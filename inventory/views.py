from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.db import transaction, models
from django.db.models import F, Sum, Q, Count, Prefetch
from django.core.paginator import Paginator
from django.urls import reverse
from django.http import JsonResponse
from django.utils.http import url_has_allowed_host_and_scheme

from .models import StorageLocations, InventoryStocks, StockTransactions, Suppliers
from .forms import StorageLocationForm, QuickStockOperationForm, SupplierForm
from catalog.models import Components


def _safe_referer_redirect(request, fallback_url=None):
    referer = request.META.get('HTTP_REFERER')
    if referer and url_has_allowed_host_and_scheme(
        url=referer,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(referer)
    return redirect(fallback_url or reverse('inventory:dashboard'))


def dashboard(request):
    """
    Головний хаб складського обліку:
    - Візуальна сітка органайзерів та колірних комірок (get_category_pill).
    - Зведена таблиця залишків компонентів з контролем дефіциту.
    - Журнал складських рухів (StockTransactions).
    """
    active_tab = request.GET.get('tab', 'locations')
    if active_tab not in ['locations', 'stocks', 'history']:
        active_tab = 'locations'

    # Global KPI Metrics (only active storage locations)
    total_locations = StorageLocations.objects.count()
    stocks_qs = InventoryStocks.objects.filter(location__isnull=False).select_related('component', 'location')
    total_positions = stocks_qs.count()
    total_units_data = stocks_qs.aggregate(
        total_on_hand=Sum('quantity_on_hand'),
        total_reserved=Sum('quantity_reserved')
    )
    total_on_hand = total_units_data['total_on_hand'] or 0
    total_reserved = total_units_data['total_reserved'] or 0
    total_free = max(0, total_on_hand - total_reserved)

    # Deficit items count (free_stock <= min_threshold or free_stock == 0)
    deficit_count = 0
    for stock in stocks_qs:
        if stock.component and (
            stock.free_stock == 0 or
            (stock.component.min_threshold and stock.free_stock <= stock.component.min_threshold)
        ):
            deficit_count += 1

    context = {
        'active_tab': active_tab,
        'total_locations': total_locations,
        'total_positions': total_positions,
        'total_on_hand': total_on_hand,
        'total_reserved': total_reserved,
        'total_free': total_free,
        'deficit_count': deficit_count,
        'quick_form': QuickStockOperationForm(),
    }

    if active_tab == 'locations':
        # 1. Visual Organizers & Cells Grid
        organizers_list = (
            StorageLocations.objects.values_list('box_number', flat=True)
            .distinct()
            .order_by('box_number')
        )
        selected_box = request.GET.get('box')
        if not selected_box and organizers_list.exists():
            selected_box = organizers_list.first()

        selected_shelf = request.GET.get('shelf', '')

        # Filter locations for current organizer
        loc_qs = StorageLocations.objects.all()
        if selected_box:
            loc_qs = loc_qs.filter(box_number=selected_box)
        if selected_shelf:
            loc_qs = loc_qs.filter(shelf=selected_shelf)

        # Optimize N+1 by prefetching active stocks and categories
        active_stocks_prefetch = Prefetch(
            'stocks',
            queryset=InventoryStocks.objects.filter(quantity_on_hand__gt=0).select_related('component__category')
        )
        locations = loc_qs.prefetch_related(active_stocks_prefetch).order_by('shelf', 'cell_code')

        # Distinct shelves for the selected organizer
        shelves_list = []
        if selected_box:
            shelves_list = (
                StorageLocations.objects.filter(box_number=selected_box)
                .exclude(shelf__isnull=True)
                .exclude(shelf__exact='')
                .values_list('shelf', flat=True)
                .distinct()
                .order_by('shelf')
            )

        # Precompute pills, stats, and group cells by rows/shelves
        locations_data = []
        shelves_grouped = {}
        occupied_count = 0
        for loc in locations:
            pill = loc.get_category_pill()
            active_stocks = [s for s in loc.stocks.all() if s.quantity_on_hand > 0]
            if active_stocks:
                occupied_count += 1
            item = {
                'location': loc,
                'pill': pill,
                'active_stocks': active_stocks,
                'total_qty': sum(s.quantity_on_hand for s in active_stocks),
                'free_qty': sum(s.free_stock for s in active_stocks),
            }
            locations_data.append(item)

            sh_key = (loc.shelf or '').strip()
            display_name = sh_key if sh_key else "Самостійні комірки (без ряду)"
            if sh_key not in shelves_grouped:
                shelves_grouped[sh_key] = {
                    'shelf_name': display_name,
                    'raw_shelf': sh_key,
                    'is_standalone': not bool(sh_key),
                    'items': [],
                    'occupied_count': 0,
                    'total_qty': 0,
                }
            shelves_grouped[sh_key]['items'].append(item)
            if active_stocks:
                shelves_grouped[sh_key]['occupied_count'] += 1
            shelves_grouped[sh_key]['total_qty'] += item['total_qty']

        rows_data = list(shelves_grouped.values())

        context.update({
            'organizers_list': organizers_list,
            'selected_box': selected_box,
            'shelves_list': shelves_list,
            'selected_shelf': selected_shelf,
            'locations_data': locations_data,
            'rows_data': rows_data,
            'total_in_box': len(locations_data),
            'occupied_in_box': occupied_count,
            'empty_in_box': len(locations_data) - occupied_count,
        })

    elif active_tab == 'stocks':
        # 2. Complete Inventory Stocks Table with Deficit Filtering
        query = request.GET.get('q', '').strip()
        is_deficit_only = request.GET.get('deficit') == '1'
        selected_box = request.GET.get('box', '')

        stocks_list_qs = InventoryStocks.objects.filter(location__isnull=False).select_related(
            'component__category', 'location'
        ).order_by('component__part_number')

        if query:
            stocks_list_qs = stocks_list_qs.filter(
                Q(component__part_number__icontains=query) |
                Q(component__specifications__icontains=query) |
                Q(component__value_nominal__icontains=query) |
                Q(location__box_number__icontains=query) |
                Q(location__cell_code__icontains=query)
            )

        if selected_box:
            stocks_list_qs = stocks_list_qs.filter(location__box_number=selected_box)

        # Deficit filter (free_stock <= min_threshold or free_stock == 0)
        if is_deficit_only:
            deficit_stock_ids = [
                s.stock_id for s in stocks_list_qs
                if s.component and (
                    s.free_stock == 0 or
                    (s.component.min_threshold and s.free_stock <= s.component.min_threshold)
                )
            ]
            stocks_list_qs = stocks_list_qs.filter(stock_id__in=deficit_stock_ids)

        paginator = Paginator(stocks_list_qs, 25)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        organizers_list = StorageLocations.objects.values_list('box_number', flat=True).distinct().order_by('box_number')

        context.update({
            'page_obj': page_obj,
            'query': query,
            'is_deficit_only': is_deficit_only,
            'selected_box': selected_box,
            'organizers_list': organizers_list,
        })

    elif active_tab == 'history':
        # 3. Stock Movement / Transaction Audit Log
        trans_qs = StockTransactions.objects.select_related(
            'stock__component', 'stock__location'
        ).order_by('-created_at', '-transaction_id')

        op_filter = request.GET.get('op_type', '')
        if op_filter:
            trans_qs = trans_qs.filter(transaction_type=op_filter)

        paginator = Paginator(trans_qs, 30)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context.update({
            'page_obj': page_obj,
            'op_filter': op_filter,
            'transaction_types': StockTransactions.TRANSACTION_TYPES,
        })

    return render(request, 'inventory/dashboard.html', context)


@login_required
def quick_operation(request):
    """
    Обробник швидких складських операцій: «Взяти», «Покласти», «Повернення», «Коригування».
    Забезпечує транзакційність (atomic), блокування рядка (select_for_update) та сувору перевірку лімітів.
    """
    if request.method == 'POST':
        form = QuickStockOperationForm(request.POST)
        if form.is_valid():
            component = form.cleaned_data['component']
            location = form.cleaned_data['location']
            op_type = form.cleaned_data['transaction_type']
            qty = form.cleaned_data['quantity']
            unit_price = form.cleaned_data.get('unit_price')
            notes = form.cleaned_data.get('notes', '').strip()

            try:
                with transaction.atomic():
                    stock, created = InventoryStocks.objects.select_for_update().get_or_create(
                        component=component,
                        location=location,
                        defaults={'quantity_on_hand': 0, 'quantity_reserved': 0}
                    )

                    if op_type == 'consumption_out':
                        # Взяти (списання): перевіряємо чи є взагалі наявний залишок
                        if stock.quantity_on_hand <= 0:
                            messages.error(
                                request,
                                f"Помилка списання: у комірці {location} немає деталі {component.part_number} (наявний залишок: 0 шт)."
                            )
                            return _safe_referer_redirect(request)

                        # Перевіряємо чи достатньо саме вільного (незарезервованого) залишку
                        free_available = stock.free_stock
                        if qty > free_available:
                            if stock.quantity_reserved > 0:
                                messages.error(
                                    request,
                                    f"Помилка списання: недостатньо вільного залишку {component.part_number} "
                                    f"у комірці {location}. Всього на складі: {stock.quantity_on_hand} шт, "
                                    f"але {stock.quantity_reserved} шт зарезервовано під проєкти. "
                                    f"Доступно для видачі лише: {free_available} шт (запитано: {qty} шт)."
                                )
                            else:
                                messages.error(
                                    request,
                                    f"Помилка списання: недостатньо залишку {component.part_number} "
                                    f"у комірці {location}. Наявний залишок: {stock.quantity_on_hand} шт (запитано: {qty} шт)."
                                )
                            return _safe_referer_redirect(request)

                        stock.quantity_on_hand -= qty
                        delta = -qty

                    elif op_type in ['purchase_in', 'return']:
                        # Перевірка на фізичну місткість комірки (максимум 50 000 шт)
                        if stock.quantity_on_hand + qty > 50000:
                            messages.error(
                                request,
                                f"Помилка: перевищено максимальну місткість комірки (50 000 шт). "
                                f"Поточний залишок: {stock.quantity_on_hand} шт, спроба додати: {qty} шт."
                            )
                            return _safe_referer_redirect(request)

                        stock.quantity_on_hand += qty
                        delta = qty
                        if unit_price is not None:
                            stock.unit_price = unit_price

                    elif op_type == 'adjustment':
                        # Коригування фактичного залишку
                        if qty < 0:
                            messages.error(request, "Фактичний залишок не може бути від'ємним.")
                            return _safe_referer_redirect(request)

                        if qty < stock.quantity_reserved:
                            messages.error(
                                request,
                                f"Помилка коригування: неможливо встановити залишок {qty} шт, "
                                f"оскільки {stock.quantity_reserved} шт уже зарезервовано під активні проєкти. "
                                f"Спочатку звільніть резерв або вкажіть залишок не менше {stock.quantity_reserved} шт."
                            )
                            return _safe_referer_redirect(request)

                        if qty > 50000:
                            messages.error(request, "Залишок однієї комірки не може перевищувати 50 000 шт.")
                            return _safe_referer_redirect(request)

                        delta = qty - stock.quantity_on_hand
                        if delta == 0:
                            messages.info(
                                request,
                                f"Залишок {component.part_number} у комірці {location} вже становить {qty} шт. Змін не внесено."
                            )
                            return _safe_referer_redirect(request)

                        stock.quantity_on_hand = qty
                        if unit_price is not None:
                            stock.unit_price = unit_price
                    else:
                        messages.error(request, "Невідомий тип операції.")
                        return redirect(reverse('inventory:dashboard'))

                    stock.save()

                    # Створюємо запис в журналі транзакцій
                    StockTransactions.objects.create(
                        stock=stock,
                        transaction_type=op_type,
                        quantity_change=delta,
                        notes=notes or f"Операція користувача {request.user.username}"
                    )

                op_display = dict(StockTransactions.TRANSACTION_TYPES).get(op_type, op_type)
                sign = "+" if delta > 0 else ""
                messages.success(
                    request,
                    f"Успішно виконано: {op_display} для {component.part_number} ({sign}{delta} шт) у комірці {location}."
                )
            except Exception as e:
                messages.error(request, f"Помилка при виконанні операції: {str(e)}")

        else:
            # Зручне форматування помилок валідації форми
            error_msgs = []
            for field, errs in form.errors.items():
                for err in errs:
                    if field == '__all__':
                        error_msgs.append(str(err))
                    else:
                        label = form.fields[field].label if field in form.fields else field
                        error_msgs.append(f"{label}: {err}")
            messages.error(request, " ".join(error_msgs))

    return _safe_referer_redirect(request)


def location_detail(request, pk):
    """
    Детальний перегляд окремої комірки: компоненти, вільні та зарезервовані залишки, журнал операцій комірки.
    Безпечно обробляє відсутні або видалені комірки замість стандартної помилки 404.
    """
    try:
        location = StorageLocations.objects.prefetch_related(
            Prefetch(
                'stocks',
                queryset=InventoryStocks.objects.select_related('component__category')
            )
        ).get(pk=pk)
    except StorageLocations.DoesNotExist:
        messages.warning(request, f"Комірку №{pk} не знайдено (можливо, її було видалено або переміщено).")
        return redirect('inventory:dashboard')

    pill = location.get_category_pill()
    stocks = location.stocks.filter(quantity_on_hand__gt=0).select_related('component__category')

    # Cell transactions history
    transactions_list = (
        StockTransactions.objects.filter(stock__location=location)
        .select_related('stock__component')
        .order_by('-created_at')[:20]
    )

    total_qty = sum(s.quantity_on_hand for s in stocks)
    total_res = sum(s.quantity_reserved for s in stocks)
    total_free = sum(s.free_stock for s in stocks)

    context = {
        'location': location,
        'pill': pill,
        'stocks': stocks,
        'transactions_list': transactions_list,
        'total_qty': total_qty,
        'total_res': total_res,
        'total_free': total_free,
        'quick_form': QuickStockOperationForm(initial={'location': location}),
    }
    return render(request, 'inventory/location_detail.html', context)


@staff_member_required
def location_create(request):
    """Створення нової комірки зберігання"""
    if request.method == 'POST':
        form = StorageLocationForm(request.POST)
        if form.is_valid():
            loc = form.save()
            messages.success(request, f"Комірку «{loc}» успішно створено.")
            return redirect('inventory:location_detail', pk=loc.pk)
    else:
        form = StorageLocationForm()

    return render(request, 'inventory/location_form.html', {
        'form': form,
        'title': 'Додати нову комірку зберігання',
        'is_edit': False,
    })


@staff_member_required
def location_edit(request, pk):
    """Редагування існуючої комірки"""
    try:
        location = StorageLocations.objects.get(pk=pk)
    except StorageLocations.DoesNotExist:
        messages.warning(request, f"Комірку №{pk} не знайдено.")
        return redirect('inventory:dashboard')

    if request.method == 'POST':
        form = StorageLocationForm(request.POST, instance=location)
        if form.is_valid():
            loc = form.save()
            messages.success(request, f"Комірку «{loc}» успішно оновлено.")
            return redirect('inventory:location_detail', pk=loc.pk)
    else:
        form = StorageLocationForm(instance=location)

    return render(request, 'inventory/location_form.html', {
        'form': form,
        'location': location,
        'title': f'Редагувати комірку {location}',
        'is_edit': True,
    })


def suppliers_list(request):
    """Список постачальників компонентів лабораторії"""
    suppliers = Suppliers.objects.annotate(orders_count=Count('orders')).order_by('name')
    return render(request, 'inventory/suppliers_list.html', {
        'suppliers': suppliers,
        'total_suppliers': suppliers.count(),
    })


@staff_member_required
def supplier_create(request):
    """Додавання постачальника"""
    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            supplier = form.save()
            messages.success(request, f"Постачальника «{supplier.name}» додано.")
            return redirect('inventory:suppliers_list')
    else:
        form = SupplierForm()

    return render(request, 'inventory/supplier_form.html', {
        'form': form,
        'title': 'Додати постачальника',
    })


@staff_member_required
def row_create(request):
    """
    Інтуїтивне додавання нового ряду комірок до органайзера.
    Створює ряд із зазначеною кількістю комірок (від 1 до 50).
    """
    if request.method == 'POST':
        box_number = request.POST.get('box_number', '').strip()
        shelf_name = request.POST.get('shelf_name', '').strip()
        raw_count = (request.POST.get('cell_count') or request.POST.get('cells_count') or '8').strip()
        prefix = request.POST.get('prefix', '').strip()

        if not box_number:
            messages.error(request, "Вкажіть назву органайзера.")
            return redirect('inventory:dashboard')

        if len(box_number) > 50:
            messages.error(request, "Назва органайзера занадто довга (максимум 50 символів).")
            return redirect('inventory:dashboard')

        try:
            cell_count = int(raw_count)
        except ValueError:
            cell_count = 8

        if cell_count < 1 or cell_count > 50:
            messages.error(request, "Кількість комірок у ряду повинна бути від 1 до 50.")
            return redirect(f"{reverse('inventory:dashboard')}?tab=locations&box={box_number}")

        # Перевірка на загальну кількість комірок в органайзері
        existing_org_cells = StorageLocations.objects.filter(box_number=box_number).count()
        if existing_org_cells + cell_count > 300:
            messages.error(
                request,
                f"В органайзері «{box_number}» уже є {existing_org_cells} комірок. Ліміт: 300 комірок на органайзер."
            )
            return redirect(f"{reverse('inventory:dashboard')}?tab=locations&box={box_number}")

        if not shelf_name:
            existing_count = (
                StorageLocations.objects.filter(box_number=box_number)
                .values('shelf')
                .distinct()
                .count()
            )
            shelf_name = f"Ряд {existing_count + 1}"
        elif len(shelf_name) > 50:
            messages.error(request, "Назва ряду не може перевищувати 50 символів.")
            return redirect(f"{reverse('inventory:dashboard')}?tab=locations&box={box_number}")

        if not prefix:
            prefix = "C"
        elif len(prefix) > 10:
            prefix = prefix[:10]

        created = 0
        with transaction.atomic():
            for i in range(1, cell_count + 1):
                code = f"{prefix}-{i:02d}"
                counter = i
                while StorageLocations.objects.filter(box_number=box_number, shelf=shelf_name, cell_code=code).exists():
                    counter += 1
                    code = f"{prefix}-{counter:02d}"

                StorageLocations.objects.create(
                    box_number=box_number,
                    shelf=shelf_name,
                    cell_code=code
                )
                created += 1

        messages.success(request, f"Успішно створено «{shelf_name}» ({created} комірок) в органайзері «{box_number}».")
        return redirect(f"{reverse('inventory:dashboard')}?tab=locations&box={box_number}")

    return redirect('inventory:dashboard')


@staff_member_required
def row_delete(request):
    """
    Видалення порожнього ряду комірок з органайзера.
    Якщо в ряду є хоча б одна деталь або резерв, видалення блокується із попередженням.
    """
    if request.method == 'POST':
        box_number = request.POST.get('box_number', '').strip()
        shelf_name = request.POST.get('shelf_name', '').strip()

        if not box_number or not shelf_name:
            messages.error(request, "Некоректні параметри ряду.")
            return redirect('inventory:dashboard')

        row_locs = StorageLocations.objects.filter(box_number=box_number, shelf=shelf_name)
        occupied_locs = row_locs.filter(
            Q(stocks__quantity_on_hand__gt=0) | Q(stocks__quantity_reserved__gt=0)
        ).distinct()

        if occupied_locs.exists():
            messages.error(request, f"Неможливо видалити ряд «{shelf_name}»: у ньому є зайняті комірки з деталями або резервами!")
            return redirect(f"{reverse('inventory:dashboard')}?tab=locations&box={box_number}")

        count = row_locs.count()
        # Delete empty stocks in these locations before deleting locations to prevent ghost deficit entries
        InventoryStocks.objects.filter(
            location__in=row_locs,
            quantity_on_hand=0,
            quantity_reserved=0
        ).delete()
        row_locs.delete()
        messages.success(request, f"Ряд «{shelf_name}» ({count} комірок) успішно видалено.")
        return redirect(f"{reverse('inventory:dashboard')}?tab=locations&box={box_number}")

    return redirect('inventory:dashboard')


@staff_member_required
def location_quick_add(request):
    """Швидке додавання однієї комірки в існуючий ряд органайзера"""
    if request.method == 'POST':
        box_number = request.POST.get('box_number', '').strip()
        shelf_name = request.POST.get('shelf_name', '').strip()
        cell_code = request.POST.get('cell_code', '').strip()

        if not box_number:
            messages.error(request, "Вкажіть назву органайзера.")
            return redirect('inventory:dashboard')

        if len(box_number) > 50:
            messages.error(request, "Назва органайзера занадто довга (максимум 50 символів).")
            return redirect('inventory:dashboard')

        if shelf_name and len(shelf_name) > 50:
            messages.error(request, "Назва ряду занадто довга (максимум 50 символів).")
            return redirect(f"{reverse('inventory:dashboard')}?tab=locations&box={box_number}")

        if not cell_code:
            existing = StorageLocations.objects.filter(box_number=box_number, shelf=shelf_name).count()
            prefix = "CELL" if not shelf_name else "C"
            cell_code = f"{prefix}-{(existing + 1):02d}"

        if len(cell_code) > 20:
            messages.error(request, "Код комірки занадто довгий (максимум 20 символів).")
            return redirect(f"{reverse('inventory:dashboard')}?tab=locations&box={box_number}")

        if StorageLocations.objects.filter(box_number=box_number, shelf=shelf_name, cell_code=cell_code).exists():
            loc_desc = f"в ряду «{shelf_name}»" if shelf_name else "(самостійна)"
            messages.error(request, f"Комірка «{cell_code}» вже існує {loc_desc}!")
        else:
            StorageLocations.objects.create(box_number=box_number, shelf=shelf_name, cell_code=cell_code)
            if shelf_name:
                messages.success(request, f"Комірку «{cell_code}» успішно додано до ряду «{shelf_name}».")
            else:
                messages.success(request, f"Самостійну комірку «{cell_code}» (без ряду) успішно створено.")

        return redirect(f"{reverse('inventory:dashboard')}?tab=locations&box={box_number}")

    return redirect('inventory:dashboard')


@staff_member_required
def location_delete(request, pk):
    """Видалення окремої комірки (тільки якщо вона порожня)"""
    try:
        location = StorageLocations.objects.get(pk=pk)
    except StorageLocations.DoesNotExist:
        messages.warning(request, f"Комірку №{pk} не знайдено (можливо, її вже було видалено).")
        return redirect('inventory:dashboard')

    box_number = location.box_number

    if request.method == 'POST':
        active_stocks = location.stocks.filter(
            Q(quantity_on_hand__gt=0) | Q(quantity_reserved__gt=0)
        )
        if active_stocks.exists():
            messages.error(request, f"Неможливо видалити комірку «{location.cell_code}», оскільки в ній є деталі або резерви.")
            return redirect('inventory:location_detail', pk=location.pk)

        # Delete empty stocks in this location before deleting location to prevent ghost deficit entries
        location.stocks.filter(quantity_on_hand=0, quantity_reserved=0).delete()
        location.delete()
        messages.success(request, f"Порожню комірку «{location.cell_code}» успішно видалено.")
        return redirect(f"{reverse('inventory:dashboard')}?tab=locations&box={box_number}")

    return redirect('inventory:location_detail', pk=location.pk)


@staff_member_required
def organizer_create(request):
    """Створення нового органайзера з початковою сіткою рядів і комірок"""
    if request.method == 'POST':
        box_number = request.POST.get('box_number', '').strip()
        raw_rows = request.POST.get('rows_count', '2').strip()
        raw_cells = request.POST.get('cells_per_row', '8').strip()
        prefix = request.POST.get('prefix', '').strip()

        if not box_number:
            messages.error(request, "Вкажіть назву органайзера.")
            return redirect('inventory:dashboard')

        if StorageLocations.objects.filter(box_number=box_number).exists():
            messages.error(request, f"Органайзер «{box_number}» вже існує!")
            return redirect(f"{reverse('inventory:dashboard')}?tab=locations&box={box_number}")

        try:
            rows_count = int(raw_rows)
        except ValueError:
            rows_count = 2
        try:
            cells_per_row = int(raw_cells)
        except ValueError:
            cells_per_row = 8

        rows_count = max(1, min(rows_count, 10))
        cells_per_row = max(1, min(cells_per_row, 30))
        if not prefix:
            prefix = "C"

        with transaction.atomic():
            for r in range(1, rows_count + 1):
                shelf_name = f"Ряд {r}"
                for c in range(1, cells_per_row + 1):
                    code = f"{prefix}{r}-{c:02d}"
                    StorageLocations.objects.create(
                        box_number=box_number,
                        shelf=shelf_name,
                        cell_code=code
                    )

        messages.success(request, f"Органайзер «{box_number}» успішно створено ({rows_count} рядів по {cells_per_row} комірок).")
        return redirect(f"{reverse('inventory:dashboard')}?tab=locations&box={box_number}")

    return redirect('inventory:dashboard')


@staff_member_required
def organizer_delete(request):
    """Видалення всього органайзера, якщо всі його комірки вільні"""
    if request.method == 'POST':
        box_number = request.POST.get('box_number', '').strip()
        if not box_number:
            return redirect('inventory:dashboard')

        org_locs = StorageLocations.objects.filter(box_number=box_number)
        if org_locs.filter(Q(stocks__quantity_on_hand__gt=0) | Q(stocks__quantity_reserved__gt=0)).exists():
            messages.error(request, f"Неможливо видалити органайзер «{box_number}»: у ньому є деталі або резерви!")
            return redirect(f"{reverse('inventory:dashboard')}?tab=locations&box={box_number}")

        count = org_locs.count()
        # Delete empty stocks in these locations before deleting locations to prevent ghost deficit entries
        InventoryStocks.objects.filter(
            location__in=org_locs,
            quantity_on_hand=0,
            quantity_reserved=0
        ).delete()
        org_locs.delete()
        messages.success(request, f"Органайзер «{box_number}» ({count} комірок) видалено.")
        return redirect('inventory:dashboard')

    return redirect('inventory:dashboard')
