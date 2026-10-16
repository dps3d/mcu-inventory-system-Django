import csv
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction, models
from django.db.models import F, Sum, Q, Prefetch
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from django.urls import reverse

from .models import Projects, ProjectBoms, ProjectAllocations
from .forms import ProjectForm, ProjectBomForm, BomQuickAddForm
from catalog.models import Components, Categories
from inventory.models import InventoryStocks, StockTransactions, StorageLocations


def _calculate_project_readiness(project, batch_size=1):
    """
    Допоміжний розрахунок готовності до збірки (Build Readiness):
    - Скільки одиниць виробу можна зібрати прямо зараз (max_buildable).
    - Рівень укомплектованості для вказаної партії batch_size (readiness_percent).
    - Деталізований статус кожного компонента в BOM.
    """
    boms = project.boms.select_related('component__category').prefetch_related(
        Prefetch(
            'allocations',
            queryset=ProjectAllocations.objects.filter(status='reserved').select_related('stock__location')
        )
    ).all()

    if not boms.exists():
        return {
            'boms_data': [],
            'max_buildable': 0,
            'readiness_percent': 0,
            'covered_count': 0,
            'total_items': 0,
            'has_shortage': False,
            'total_units_required': 0,
        }

    # Отримуємо всі активні складські залишки для компонентів цього BOM
    comp_ids = [b.component_id for b in boms]
    stocks_qs = InventoryStocks.objects.filter(
        component_id__in=comp_ids,
        location__isnull=False
    ).select_related('location')

    stocks_by_comp = {}
    for st in stocks_qs:
        stocks_by_comp.setdefault(st.component_id, []).append(st)

    boms_data = []
    buildable_per_item = []
    covered_count = 0
    total_units_required = 0

    for b in boms:
        qty_req = b.quantity_required or 1
        batch_needed = qty_req * batch_size
        total_units_required += batch_needed

        comp_stocks = stocks_by_comp.get(b.component_id, [])
        total_free = sum(s.free_stock for s in comp_stocks)

        # Активні резерви саме для цієї позиції BOM
        reserved_allocations = list(b.allocations.all())
        reserved_qty = sum(a.allocated_quantity for a in reserved_allocations)

        # Доступно під цей проєкт = Вільний залишок на складі + Вже зарезервовано під цей BOM
        effective_available = total_free + reserved_qty

        # Скільки виробів покриває цей компонент
        item_buildable = effective_available // qty_req
        buildable_per_item.append(item_buildable)

        is_covered = effective_available >= batch_needed
        if is_covered:
            covered_count += 1

        shortage = max(0, batch_needed - effective_available)

        # Відсоток покриття для даного рядка
        fulfillment_pct = min(100, int((effective_available / batch_needed) * 100)) if batch_needed > 0 else 100

        boms_data.append({
            'bom': b,
            'component': b.component,
            'qty_required': qty_req,
            'batch_needed': batch_needed,
            'total_free': total_free,
            'reserved_qty': reserved_qty,
            'effective_available': effective_available,
            'item_buildable': item_buildable,
            'is_covered': is_covered,
            'shortage': shortage,
            'fulfillment_pct': fulfillment_pct,
            'stocks': comp_stocks,
            'allocations': reserved_allocations,
        })

    max_buildable = min(buildable_per_item) if buildable_per_item else 0
    readiness_percent = int((covered_count / len(boms)) * 100) if boms else 0

    return {
        'boms_data': boms_data,
        'max_buildable': max_buildable,
        'readiness_percent': readiness_percent,
        'covered_count': covered_count,
        'total_items': len(boms),
        'has_shortage': covered_count < len(boms),
        'total_units_required': total_units_required,
    }


def _can_view_project(user, project):
    """
    Перевірка прав на перегляд проєкту:
    - Публічні проєкти (is_private=False) доступні всім.
    - Приватні проєкти (is_private=True) доступні лише їх автору (created_by) та персоналу (is_staff/is_superuser).
    """
    if not project.is_private:
        return True
    if not user.is_authenticated:
        return False
    if user.is_staff or user.is_superuser:
        return True
    return project.created_by_id == user.id


def _can_edit_project(user, project):
    """
    Перевірка прав на редагування проєкту та управління специфікацією BOM:
    - Неавторизовані користувачі не мають прав на редагування.
    - Адміністратори та персонал мають повний доступ.
    - Звичайний користувач може редагувати ТІЛЬКИ власні проєкти (де він є автором).
    """
    if not user.is_authenticated:
        return False
    if user.is_staff or user.is_superuser:
        return True
    return project.created_by_id == user.id


def project_list(request):
    """
    Головний екран модуля «Проєкти та BOM»:
    - KPI метрики (всього проєктів, в розробці, готові до збірки, завершені).
    - Фільтри за статусом, видимістю, пошуковий рядок.
    - Картки проєктів з індикатором Build Readiness (%).
    - Сувора ізоляція приватних проєктів (чужі приватні проєкти не відображаються у списку та не враховуються у лічильниках).
    """
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()
    visibility_filter = request.GET.get('vis', '').strip()
    sort_by = request.GET.get('sort', 'newest')

    # Базовий набір проєктів, які має право бачити поточний користувач:
    if not request.user.is_authenticated:
        base_visible = Projects.objects.filter(is_private=False)
    elif request.user.is_staff or request.user.is_superuser:
        base_visible = Projects.objects.all()
    else:
        base_visible = Projects.objects.filter(
            Q(is_private=False) | Q(created_by=request.user)
        )

    projects_qs = base_visible.select_related('created_by')

    # Фільтрація за видимістю (публічний / приватний)
    if visibility_filter == 'public':
        projects_qs = projects_qs.filter(is_private=False)
    elif visibility_filter == 'private':
        projects_qs = projects_qs.filter(is_private=True)

    if status_filter:
        projects_qs = projects_qs.filter(status=status_filter)

    if query:
        projects_qs = projects_qs.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )

    # Сортування
    if sort_by == 'name_asc':
        projects_qs = projects_qs.order_by('name')
    elif sort_by == 'name_desc':
        projects_qs = projects_qs.order_by('-name')
    elif sort_by == 'oldest':
        projects_qs = projects_qs.order_by('created_at')
    else:  # newest
        projects_qs = projects_qs.order_by('-created_at')

    # KPI метрики розраховуються виключно по доступних для користувача проєктах
    total_projects = base_visible.count()
    active_projects = base_visible.filter(status='in_progress').count()
    completed_projects = base_visible.filter(status='completed').count()

    # Підрахунок readiness для списку
    projects_with_stats = []
    fully_buildable_count = 0

    for proj in projects_qs:
        stats = _calculate_project_readiness(proj, batch_size=1)
        if stats['total_items'] > 0 and stats['readiness_percent'] == 100:
            fully_buildable_count += 1
        projects_with_stats.append({
            'project': proj,
            'stats': stats,
        })

    paginator = Paginator(projects_with_stats, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'query': query,
        'status_filter': status_filter,
        'visibility_filter': visibility_filter,
        'sort_by': sort_by,
        'status_choices': Projects.STATUS_CHOICES,
        'total_projects': total_projects,
        'active_projects': active_projects,
        'completed_projects': completed_projects,
        'fully_buildable_count': fully_buildable_count,
        'form': ProjectForm(),
    }
    return render(request, 'projects/project_list.html', context)


def project_detail(request, pk):
    """
    Детальний екран проєкту та двопанельний конструктор BOM:
    - Ліва панель: специфікація деталей, необхідна кількість, наявність у комірках, резервування.
    - Інтерактивний калькулятор партії збірки (batch_size: 1, 5, 10, 25...).
    - Права панель: швидкий пошук та додавання деталей із каталогу.
    - Перевірка прав доступу: приватні проєкти захищені від перегляду сторонніми користувачами.
    """
    project = get_object_or_404(Projects.objects.select_related('created_by'), pk=pk)

    # Перевірка доступу до приватного проєкту
    if not _can_view_project(request.user, project):
        if not request.user.is_authenticated:
            messages.warning(request, "Цей проєкт є приватним. Будь ласка, увійдіть до облікового запису.")
            return redirect(f"{reverse('accounts:login')}?next={request.path}")
        else:
            messages.error(request, "У вас немає прав для перегляду цього приватного проєкту.")
            return redirect('projects:list')

    user_can_edit = _can_edit_project(request.user, project)

    # Партія збірки з параметра запиту (за замовчуванням 1 шт)
    try:
        batch_size = int(request.GET.get('batch', 1))
        if batch_size < 1:
            batch_size = 1
        elif batch_size > 1000:
            batch_size = 1000
    except (ValueError, TypeError):
        batch_size = 1

    readiness = _calculate_project_readiness(project, batch_size=batch_size)

    # Список ідентифікаторів компонентів, що вже є в BOM
    existing_comp_ids = set(b.component_id for b in project.boms.all())

    # Компоненти для правої панелі швидкого вибору
    picker_query = request.GET.get('pq', '').strip()
    picker_cat = request.GET.get('pcat', '').strip()

    components_qs = Components.objects.select_related('category').all()
    if picker_cat:
        components_qs = components_qs.filter(category_id=picker_cat)
    if picker_query:
        components_qs = components_qs.filter(
            Q(part_number__icontains=picker_query) |
            Q(specifications__icontains=picker_query) |
            Q(package_type__icontains=picker_query) |
            Q(value_nominal__icontains=picker_query)
        )

    # Оптимізуємо вибірку залишків для пікера
    catalog_stocks = (
        InventoryStocks.objects.filter(location__isnull=False)
        .values('component_id')
        .annotate(
            total_on_hand=Sum('quantity_on_hand'),
            total_reserved=Sum('quantity_reserved')
        )
    )
    stock_map = {
        s['component_id']: max(0, (s['total_on_hand'] or 0) - (s['total_reserved'] or 0))
        for s in catalog_stocks
    }

    picker_components = []
    for c in components_qs[:30]:  # топ-30 для швидкого рендерингу панелі
        picker_components.append({
            'component': c,
            'free_stock': stock_map.get(c.component_id, 0),
            'is_in_bom': c.component_id in existing_comp_ids,
        })

    categories = Categories.objects.filter(parent__isnull=True).order_by('name')

    context = {
        'project': project,
        'batch_size': batch_size,
        'readiness': readiness,
        'picker_components': picker_components,
        'picker_query': picker_query,
        'picker_cat': picker_cat,
        'categories': categories,
        'project_form': ProjectForm(instance=project),
        'bom_form': ProjectBomForm(),
        'user_can_edit': user_can_edit,
    }
    return render(request, 'projects/project_detail.html', context)


@login_required
def project_create(request):
    """Створення нового проєкту"""
    if request.method == 'POST':
        form = ProjectForm(request.POST, request.FILES)
        if form.is_valid():
            project = form.save(commit=False)
            project.created_by = request.user
            project.save()
            messages.success(request, f"Проєкт «{project.name}» успішно створено! Тепер додайте компоненти до специфікації BOM.")
            return redirect('projects:detail', pk=project.pk)
        else:
            messages.error(request, "Будь ласка, перевірте правильність заповнення полів.")
    else:
        form = ProjectForm()

    return render(request, 'projects/project_form.html', {'form': form, 'title': 'Створення нового проєкту'})


@login_required
def project_edit(request, pk):
    """Редагування існуючого проєкту (доступно лише автору або персоналу)"""
    project = get_object_or_404(Projects, pk=pk)

    if not _can_edit_project(request.user, project):
        messages.error(request, "У вас немає прав для редагування цього проєкту.")
        return redirect('projects:detail', pk=project.pk)

    if request.method == 'POST':
        form = ProjectForm(request.POST, request.FILES, instance=project)
        if form.is_valid():
            form.save()
            messages.success(request, f"Дані проєкту «{project.name}» успішно оновлено.")
            return redirect('projects:detail', pk=project.pk)
        else:
            messages.error(request, "Помилка при збереженні змін проєкту.")
    else:
        form = ProjectForm(instance=project)

    return render(request, 'projects/project_form.html', {
        'form': form,
        'project': project,
        'title': f"Редагування проєкту: {project.name}"
    })


@login_required
def project_delete(request, pk):
    """Безпечне видалення проєкту з попереднім зняттям резервів (доступно автору або персоналу)"""
    project = get_object_or_404(Projects, pk=pk)

    if not _can_edit_project(request.user, project):
        messages.error(request, "У вас немає прав для видалення цього проєкту.")
        return redirect('projects:detail', pk=project.pk)

    if request.method == 'POST':
        with transaction.atomic():
            # Знімаємо всі активні резерви на складі перед видаленням
            allocations = ProjectAllocations.objects.filter(
                bom__project=project,
                status='reserved'
            ).select_related('stock')

            for alloc in allocations:
                stock = alloc.stock
                stock.quantity_reserved = max(0, stock.quantity_reserved - alloc.allocated_quantity)
                stock.save(update_fields=['quantity_reserved'])

                StockTransactions.objects.create(
                    stock=stock,
                    transaction_type='reservation',
                    quantity_change=-alloc.allocated_quantity,
                    reference_id=project.project_id,
                    notes=f"Знято резерв через видалення проєкту: {project.name}"
                )

            name = project.name
            project.delete()

        messages.success(request, f"Проєкт «{name}» успішно видалено, всі зарезервовані деталі повернено у вільний залишок складу.")
        return redirect('projects:list')

    return redirect('projects:detail', pk=project.pk)


@login_required
def project_status_update(request, pk):
    """Швидка зміна статусу проєкту (доступно лише автору або персоналу)"""
    project = get_object_or_404(Projects, pk=pk)

    if not _can_edit_project(request.user, project):
        messages.error(request, "У вас немає прав для зміни статусу цього проєкту.")
        return redirect('projects:detail', pk=project.pk)

    if request.method == 'POST':
        new_status = request.POST.get('status', '').strip()
        valid_statuses = dict(Projects.STATUS_CHOICES)
        if new_status in valid_statuses:
            project.status = new_status
            project.save(update_fields=['status'])
            messages.success(request, f"Статус проєкту змінено на «{valid_statuses[new_status]}».")
        else:
            messages.error(request, "Некоректний статус проєкту.")

    return redirect('projects:detail', pk=project.pk)


@login_required
def bom_add_item(request, pk):
    """
    Додавання деталі до специфікації BOM проєкту.
    Підтримує додавання через форму або через швидкий клік із правої панелі каталогу.
    """
    project = get_object_or_404(Projects, pk=pk)

    if not _can_edit_project(request.user, project):
        messages.error(request, "У вас немає прав для модифікації специфікації цього проєкту.")
        return redirect('projects:detail', pk=project.pk)

    if request.method == 'POST':
        component_id = request.POST.get('component') or request.POST.get('component_id')
        raw_qty = request.POST.get('quantity_required', '1')
        designator = request.POST.get('designator', '').strip()

        if not component_id:
            messages.error(request, "Не обрано компонент для додавання.")
            return redirect('projects:detail', pk=project.pk)

        component = get_object_or_404(Components, pk=component_id)

        try:
            qty = int(raw_qty)
            if qty < 1:
                qty = 1
            elif qty > 10000:
                qty = 10000
        except (ValueError, TypeError):
            qty = 1

        # Якщо деталь вже є в BOM — оновлюємо кількість та об'єднуємо десигнатори
        existing_bom = ProjectBoms.objects.filter(project=project, component=component).first()
        if existing_bom:
            existing_bom.quantity_required += qty
            if designator:
                if existing_bom.designator:
                    existing_bom.designator = f"{existing_bom.designator}, {designator}"
                else:
                    existing_bom.designator = designator
            existing_bom.save()
            messages.success(
                request,
                f"Кількість для {component.part_number} збільшено на {qty} шт (разом: {existing_bom.quantity_required} шт)."
            )
        else:
            ProjectBoms.objects.create(
                project=project,
                component=component,
                quantity_required=qty,
                designator=designator
            )
            desig_hint = f" [{designator}]" if designator else ""
            messages.success(request, f"Компонент {component.part_number}{desig_hint} (x{qty} шт) додано до BOM.")

    batch = request.GET.get('batch', '1')
    return redirect(f"{reverse('projects:detail', args=[project.pk])}?batch={batch}")


@login_required
def bom_edit_item(request, pk, bom_id):
    """Редагування позиції BOM (кількість або позиційне позначення)"""
    project = get_object_or_404(Projects, pk=pk)

    if not _can_edit_project(request.user, project):
        messages.error(request, "У вас немає прав для редагування специфікації цього проєкту.")
        return redirect('projects:detail', pk=project.pk)

    bom_item = get_object_or_404(ProjectBoms, pk=bom_id, project=project)

    if request.method == 'POST':
        raw_qty = request.POST.get('quantity_required', '').strip()
        designator = request.POST.get('designator', '').strip()

        try:
            qty = int(raw_qty)
            if qty < 1:
                qty = 1
            elif qty > 10000:
                qty = 10000
            bom_item.quantity_required = qty
            bom_item.designator = designator
            bom_item.save()
            messages.success(request, f"Позицію BOM для {bom_item.component.part_number} успішно оновлено.")
        except (ValueError, TypeError):
            messages.error(request, "Вкажіть коректну кількість (від 1 до 10000 шт).")

    batch = request.GET.get('batch', '1')
    return redirect(f"{reverse('projects:detail', args=[project.pk])}?batch={batch}")


@login_required
def bom_delete_item(request, pk, bom_id):
    """Видалення позиції з BOM із попереднім поверненням резервів"""
    project = get_object_or_404(Projects, pk=pk)

    if not _can_edit_project(request.user, project):
        messages.error(request, "У вас немає прав для видалення позицій з цього проєкту.")
        return redirect('projects:detail', pk=project.pk)

    bom_item = get_object_or_404(ProjectBoms, pk=bom_id, project=project)

    if request.method == 'POST':
        with transaction.atomic():
            # Повертаємо резерви для цього рядка
            for alloc in bom_item.allocations.filter(status='reserved').select_related('stock'):
                stock = alloc.stock
                stock.quantity_reserved = max(0, stock.quantity_reserved - alloc.allocated_quantity)
                stock.save(update_fields=['quantity_reserved'])

                StockTransactions.objects.create(
                    stock=stock,
                    transaction_type='reservation',
                    quantity_change=-alloc.allocated_quantity,
                    reference_id=project.project_id,
                    notes=f"Знято резерв через видалення з BOM: {bom_item.component.part_number}"
                )

            part = bom_item.component.part_number
            bom_item.delete()

        messages.success(request, f"Позицію {part} видалено зі специфікації проєкту.")

    batch = request.GET.get('batch', '1')
    return redirect(f"{reverse('projects:detail', args=[project.pk])}?batch={batch}")


@login_required
def bom_reserve_item(request, pk, bom_id):
    """
    Резервування деталей під окрему позицію BOM:
    - Визначає потрібну кількість для поточної партії.
    - Автоматично резервує деталі з доступних комірок складу.
    - Створює записи ProjectAllocations та оновлює quantity_reserved.
    """
    project = get_object_or_404(Projects, pk=pk)

    if not _can_edit_project(request.user, project):
        messages.error(request, "У вас немає прав для резервування компонентів під цей проєкт.")
        return redirect('projects:detail', pk=project.pk)

    bom_item = get_object_or_404(ProjectBoms, pk=bom_id, project=project)

    try:
        batch_size = max(1, int(request.POST.get('batch', 1)))
    except (ValueError, TypeError):
        batch_size = 1

    needed_total = bom_item.quantity_required * batch_size

    with transaction.atomic():
        # Скільки вже зарезервовано під цей BOM
        current_reserved = bom_item.allocations.filter(status='reserved').aggregate(
            total=Sum('allocated_quantity')
        )['total'] or 0

        needed_to_reserve = max(0, needed_total - current_reserved)
        if needed_to_reserve == 0:
            messages.info(request, f"Для {bom_item.component.part_number} вже зарезервовано повну партію ({current_reserved} шт).")
            return redirect(f"{reverse('projects:detail', args=[project.pk])}?batch={batch_size}")

        # Шукаємо активні складські запаси з вільним залишком
        stocks = (
            InventoryStocks.objects.select_for_update()
            .filter(
                component=bom_item.component,
                location__isnull=False,
                quantity_on_hand__gt=F('quantity_reserved')
            )
            .order_by('location__box_number', 'location__cell_code')
        )

        reserved_now = 0
        for stock in stocks:
            free = stock.free_stock
            if free <= 0:
                continue

            take_from_cell = min(free, needed_to_reserve - reserved_now)
            if take_from_cell <= 0:
                break

            stock.quantity_reserved += take_from_cell
            stock.save(update_fields=['quantity_reserved'])

            # Знаходимо або створюємо алокацію
            alloc, created = ProjectAllocations.objects.get_or_create(
                bom=bom_item,
                stock=stock,
                status='reserved',
                defaults={'allocated_quantity': take_from_cell}
            )
            if not created:
                alloc.allocated_quantity += take_from_cell
                alloc.save(update_fields=['allocated_quantity'])

            # Запис руху в журнал транзакцій
            StockTransactions.objects.create(
                stock=stock,
                transaction_type='reservation',
                quantity_change=take_from_cell,
                reference_id=project.project_id,
                notes=f"Резервування для проєкту: {project.name} ({take_from_cell} шт)"
            )

            reserved_now += take_from_cell
            if reserved_now >= needed_to_reserve:
                break

        if reserved_now > 0:
            messages.success(
                request,
                f"Успішно зарезервовано {reserved_now} шт {bom_item.component.part_number} для проєкту «{project.name}»."
            )
        else:
            messages.warning(
                request,
                f"На складі немає вільного залишку {bom_item.component.part_number} для нового резервування."
            )

    return redirect(f"{reverse('projects:detail', args=[project.pk])}?batch={batch_size}")


@login_required
def bom_release_item(request, pk, bom_id):
    """Зняття всіх активних резервів для конкретної позиції BOM"""
    project = get_object_or_404(Projects, pk=pk)

    if not _can_edit_project(request.user, project):
        messages.error(request, "У вас немає прав для зміни резервів цього проєкту.")
        return redirect('projects:detail', pk=project.pk)

    bom_item = get_object_or_404(ProjectBoms, pk=bom_id, project=project)

    try:
        batch_size = max(1, int(request.POST.get('batch', 1)))
    except (ValueError, TypeError):
        batch_size = 1

    with transaction.atomic():
        allocations = bom_item.allocations.filter(status='reserved').select_related('stock')
        total_released = 0

        for alloc in allocations:
            stock = alloc.stock
            released = alloc.allocated_quantity
            stock.quantity_reserved = max(0, stock.quantity_reserved - released)
            stock.save(update_fields=['quantity_reserved'])

            StockTransactions.objects.create(
                stock=stock,
                transaction_type='reservation',
                quantity_change=-released,
                reference_id=project.project_id,
                notes=f"Скасування резерву для проєкту: {project.name}"
            )
            total_released += released
            alloc.delete()

        if total_released > 0:
            messages.success(
                request,
                f"Знято резерв {total_released} шт {bom_item.component.part_number}. Деталі повернено у вільний залишок."
            )
        else:
            messages.info(request, f"Для {bom_item.component.part_number} не було активних резервів.")

    return redirect(f"{reverse('projects:detail', args=[project.pk])}?batch={batch_size}")


@login_required
def project_reserve_all(request, pk):
    """Масове резервування всіх доступних на складі деталей для партії проєкту"""
    project = get_object_or_404(Projects, pk=pk)

    if not _can_edit_project(request.user, project):
        messages.error(request, "У вас немає прав для резервування компонентів під цей проєкт.")
        return redirect('projects:detail', pk=project.pk)

    try:
        batch_size = max(1, int(request.POST.get('batch', 1)))
    except (ValueError, TypeError):
        batch_size = 1

    total_reserved_items = 0
    with transaction.atomic():
        for bom in project.boms.select_related('component').all():
            needed_total = bom.quantity_required * batch_size
            current_reserved = bom.allocations.filter(status='reserved').aggregate(
                total=Sum('allocated_quantity')
            )['total'] or 0

            needed = max(0, needed_total - current_reserved)
            if needed <= 0:
                continue

            stocks = (
                InventoryStocks.objects.select_for_update()
                .filter(
                    component=bom.component,
                    location__isnull=False,
                    quantity_on_hand__gt=F('quantity_reserved')
                )
                .order_by('location__box_number', 'location__cell_code')
            )

            for stock in stocks:
                free = stock.free_stock
                if free <= 0:
                    continue

                take = min(free, needed)
                if take <= 0:
                    break

                stock.quantity_reserved += take
                stock.save(update_fields=['quantity_reserved'])

                alloc, created = ProjectAllocations.objects.get_or_create(
                    bom=bom,
                    stock=stock,
                    status='reserved',
                    defaults={'allocated_quantity': take}
                )
                if not created:
                    alloc.allocated_quantity += take
                    alloc.save(update_fields=['allocated_quantity'])

                StockTransactions.objects.create(
                    stock=stock,
                    transaction_type='reservation',
                    quantity_change=take,
                    reference_id=project.project_id,
                    notes=f"Масовий резерв: {project.name}"
                )

                needed -= take
                total_reserved_items += take
                if needed <= 0:
                    break

    if total_reserved_items > 0:
        messages.success(request, f"Успішно зарезервовано {total_reserved_items} деталей під партію з {batch_size} виробів!")
    else:
        messages.info(request, "Всі деталі вже зарезервовані або немає додаткових вільних залишків на складі.")

    return redirect(f"{reverse('projects:detail', args=[project.pk])}?batch={batch_size}")


@login_required
def project_consume_all(request, pk):
    """
    Списання зарезервованих деталей у збірку:
    - Зменшує фактичний залишок (quantity_on_hand) і резерв (quantity_reserved).
    - Переводить статус алокацій у 'consumed'.
    - Фіксує операцію consumption_out у журналі рухів StockTransactions.
    """
    project = get_object_or_404(Projects, pk=pk)

    if not _can_edit_project(request.user, project):
        messages.error(request, "У вас немає прав для списання деталей цього проєкту.")
        return redirect('projects:detail', pk=project.pk)

    try:
        batch_size = max(1, int(request.POST.get('batch', 1)))
    except (ValueError, TypeError):
        batch_size = 1

    total_consumed = 0
    with transaction.atomic():
        allocations = (
            ProjectAllocations.objects.select_for_update()
            .filter(bom__project=project, status='reserved')
            .select_related('stock__component', 'stock__location')
        )

        if not allocations.exists():
            messages.warning(request, "Немає зарезервованих деталей для списання у збірку. Спочатку виконайте резервування.")
            return redirect(f"{reverse('projects:detail', args=[project.pk])}?batch={batch_size}")

        for alloc in allocations:
            stock = alloc.stock
            qty = alloc.allocated_quantity

            # Списуємо зі складу
            stock.quantity_on_hand = max(0, stock.quantity_on_hand - qty)
            stock.quantity_reserved = max(0, stock.quantity_reserved - qty)
            stock.save(update_fields=['quantity_on_hand', 'quantity_reserved'])

            alloc.status = 'consumed'
            alloc.save(update_fields=['status'])

            StockTransactions.objects.create(
                stock=stock,
                transaction_type='consumption_out',
                quantity_change=-qty,
                reference_id=project.project_id,
                notes=f"Списано у збірку проєкту: {project.name}"
            )
            total_consumed += qty

        # Якщо проєкт був у плануванні — переводимо в розробку або зберігаємо статус
        if project.status == 'planning':
            project.status = 'in_progress'
            project.save(update_fields=['status'])

    messages.success(
        request,
        f"Успішно списано {total_consumed} деталей у виробництво/збірку для проєкту «{project.name}»!"
    )
    return redirect(f"{reverse('projects:detail', args=[project.pk])}?batch={batch_size}")


def project_bom_export_csv(request, pk):
    """Експорт специфікації BOM проєкту у формат CSV для лабораторії"""
    project = get_object_or_404(Projects, pk=pk)

    if not _can_view_project(request.user, project):
        messages.error(request, "У вас немає прав для експорту специфікації цього проєкту.")
        return redirect('projects:list')

    try:
        batch_size = max(1, int(request.GET.get('batch', 1)))
    except (ValueError, TypeError):
        batch_size = 1

    readiness = _calculate_project_readiness(project, batch_size=batch_size)

    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    filename = f"BOM_{project.name.replace(' ', '_')}_x{batch_size}.csv"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow([
        "Позиційне позначення",
        "Парт-номер",
        "Опис",
        "Категорія",
        "Корпус",
        "Кількість на 1 шт",
        f"Потрібно на партію ({batch_size} шт)",
        "Вільно на складі",
        "Зарезервовано",
        "Статус забезпечення",
        "Дефіцит"
    ])

    for item in readiness['boms_data']:
        status_text = "В наявності" if item['is_covered'] else f"Дефіцит ({item['shortage']} шт)"
        writer.writerow([
            item['bom'].designator or "—",
            item['component'].part_number,
            item['component'].specifications or "—",
            item['component'].category.name if item['component'].category else "—",
            item['component'].package_type or "—",
            item['qty_required'],
            item['batch_needed'],
            item['total_free'],
            item['reserved_qty'],
            status_text,
            item['shortage']
        ])

    return response
