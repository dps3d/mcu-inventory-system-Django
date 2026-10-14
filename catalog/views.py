from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Sum, Q, F
from django.db.models.functions import Coalesce
from .models import Components, Categories, ComponentPinouts
from .forms import ComponentForm
from .constants import STANDARD_PACKAGES


def is_staff_check(user):
    return user.is_authenticated and user.is_staff


def component_list(request):
    """
    Публічний каталог компонентів з пошуком, фільтрацією та перемикачем Сітка/Таблиця.
    """
    query = request.GET.get('q', '').strip()
    category_id = request.GET.get('category', '').strip()
    package_type = request.GET.get('package', '').strip()
    stock_status = request.GET.get('status', '').strip()
    sort_by = request.GET.get('sort', 'name_asc').strip()
    view_mode = request.GET.get('view', 'grid').strip()

    # Базовий запит з анотаціями залишків
    queryset = Components.objects.select_related('category').annotate(
        total_on_hand=Coalesce(Sum('stocks__quantity_on_hand'), 0),
        total_reserved=Coalesce(Sum('stocks__quantity_reserved'), 0),
    ).annotate(
        total_free=F('total_on_hand') - F('total_reserved')
    )

    # 1. Пошук (по маркуванню, опису, номіналу, корпусу, категорії)
    if query:
        queryset = queryset.filter(
            Q(part_number__icontains=query) |
            Q(specifications__icontains=query) |
            Q(value_nominal__icontains=query) |
            Q(package_type__icontains=query) |
            Q(category__name__icontains=query)
        )

    # 2. Фільтр за категорією
    if category_id:
        queryset = queryset.filter(category_id=category_id)

    # 3. Фільтр за корпусом
    if package_type:
        queryset = queryset.filter(package_type=package_type)

    # 4. Фільтр за наявністю на складі
    if stock_status == 'in_stock':
        queryset = queryset.filter(total_on_hand__gt=0)
    elif stock_status == 'low_stock':
        queryset = queryset.filter(
            total_on_hand__gt=0,
            total_on_hand__lte=F('min_threshold')
        )
    elif stock_status == 'out_of_stock':
        queryset = queryset.filter(total_on_hand__lte=0)

    # 5. Сортування
    if sort_by == 'name_desc':
        queryset = queryset.order_by('-part_number')
    elif sort_by == 'stock_desc':
        queryset = queryset.order_by('-total_free', 'part_number')
    elif sort_by == 'stock_asc':
        queryset = queryset.order_by('total_free', 'part_number')
    elif sort_by == 'newest':
        queryset = queryset.order_by('-created_at', '-component_id')
    else:  # name_asc
        queryset = queryset.order_by('part_number')

    # Пагінація: 12 елементів на сторінку
    paginator = Paginator(queryset, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Довідники для фільтрів (з оптимізацією select_related для запобігання N+1)
    categories = Categories.objects.select_related('parent').all()
    db_packages = list(
        Components.objects.exclude(package_type__isnull=True)
        .exclude(package_type__exact='')
        .values_list('package_type', flat=True)
        .distinct()
    )
    # Об'єднуємо наявні в базі корпуси та популярні стандартні для швидкої фільтрації
    packages = sorted(set(db_packages + STANDARD_PACKAGES[:16]))

    context = {
        'page_obj': page_obj,
        'components': page_obj.object_list,
        'categories': categories,
        'packages': packages,
        'search_query': query,
        'selected_category': category_id,
        'selected_package': package_type,
        'selected_status': stock_status,
        'selected_sort': sort_by,
        'view_mode': view_mode,
        'total_count': paginator.count,
    }
    return render(request, 'catalog/component_list.html', context)


def component_detail(request, pk):
    """
    Детальний перегляд компонента: характеристики, складські комірки та статус.
    """
    component = get_object_or_404(
        Components.objects.select_related('category'),
        pk=pk
    )

    stocks = component.stocks.select_related('location').all()
    total_on_hand = sum(s.quantity_on_hand for s in stocks)
    total_reserved = sum(s.quantity_reserved for s in stocks)
    total_free = max(0, total_on_hand - total_reserved)

    # Визначення статусу запасу
    if total_on_hand <= 0:
        stock_badge = {'type': 'danger', 'label': 'Немає на складі'}
    elif component.min_threshold and total_on_hand <= component.min_threshold:
        stock_badge = {'type': 'warning', 'label': 'Закінчується'}
    else:
        stock_badge = {'type': 'success', 'label': 'В наявності'}

    # Розпіновки компонента (для прев'ю та зв'язку з наступним модулем)
    pinouts = component.pinouts.all().order_by('side', 'pin_number')
    left_pins = [p for p in pinouts if p.side == 'left']
    right_pins = [p for p in pinouts if p.side == 'right']

    context = {
        'component': component,
        'stocks': stocks,
        'total_on_hand': total_on_hand,
        'total_reserved': total_reserved,
        'total_free': total_free,
        'stock_badge': stock_badge,
        'pinouts': pinouts,
        'left_pins': left_pins,
        'right_pins': right_pins,
        'has_pinouts': pinouts.exists(),
    }
    return render(request, 'catalog/component_detail.html', context)


@login_required
@user_passes_test(is_staff_check)
def component_create(request):
    """
    Створення нового компонента в каталозі (тільки для персоналу).
    """
    if request.method == 'POST':
        form = ComponentForm(request.POST, request.FILES)
        if form.is_valid():
            component = form.save()
            messages.success(request, f"Компонент «{component.part_number}» успішно додано до каталогу.")
            return redirect('catalog:detail', pk=component.pk)
    else:
        form = ComponentForm()

    return render(request, 'catalog/component_form.html', {
        'form': form,
        'action_title': 'Додавання нового компонента',
        'submit_label': 'Створити компонент',
        'standard_packages': STANDARD_PACKAGES,
    })


@login_required
@user_passes_test(is_staff_check)
def component_edit(request, pk):
    """
    Редагування існуючого компонента (тільки для персоналу).
    """
    component = get_object_or_404(Components, pk=pk)

    if request.method == 'POST':
        form = ComponentForm(request.POST, request.FILES, instance=component)
        if form.is_valid():
            form.save()
            messages.success(request, f"Дані компонента «{component.part_number}» успішно оновлено.")
            return redirect('catalog:detail', pk=component.pk)
    else:
        form = ComponentForm(instance=component)

    return render(request, 'catalog/component_form.html', {
        'form': form,
        'component': component,
        'action_title': f"Редагування «{component.part_number}»",
        'submit_label': 'Зберегти зміни',
        'standard_packages': STANDARD_PACKAGES,
    })


@login_required
@user_passes_test(is_staff_check)
def component_delete(request, pk):
    """
    Видалення компонента (тільки для персоналу).
    """
    component = get_object_or_404(Components, pk=pk)

    if request.method == 'POST':
        part_name = component.part_number
        try:
            component.delete()
            messages.success(request, f"Компонент «{part_name}» видалено з каталогу.")
            return redirect('catalog:list')
        except Exception as e:
            messages.error(
                request,
                f"Неможливо видалити компонент «{part_name}», оскільки на нього посилаються складські залишки або замовлення."
            )
            return redirect('catalog:detail', pk=component.pk)

    return render(request, 'catalog/component_confirm_delete.html', {
        'component': component,
    })


def pinout_view(request, pk):
    """
    Публічний інтерактивний візуалізатор розпіновки (Pinout Viewer).
    """
    component = get_object_or_404(
        Components.objects.select_related('category'),
        pk=pk
    )
    pinouts = component.pinouts.all().order_by('side', 'pin_number')
    left_pins = [p for p in pinouts if p.side == 'left']
    right_pins = [p for p in pinouts if p.side == 'right']

    # Сигнали та підрахунок для фільтрації
    signal_counts = {}
    for p in pinouts:
        signal_counts[p.signal_type] = signal_counts.get(p.signal_type, 0) + 1

    return render(request, 'catalog/pinout_view.html', {
        'component': component,
        'pinouts': pinouts,
        'left_pins': left_pins,
        'right_pins': right_pins,
        'signal_counts': signal_counts,
        'has_pinouts': pinouts.exists(),
    })


@login_required
@user_passes_test(is_staff_check)
def pinout_builder(request, pk):
    """
    Конструктор розпіновок (Pinout Builder) для персоналу:
    динамічне додавання, редагування, генерація пресетів та збереження пінів.
    """
    import json
    from django.db import transaction

    component = get_object_or_404(Components, pk=pk)

    if request.method == 'POST':
        pins_data_raw = request.POST.get('pins_json', '[]')
        try:
            pins_data = json.loads(pins_data_raw)
            with transaction.atomic():
                # Видаляємо старі піни та створюємо нові
                ComponentPinouts.objects.filter(component=component).delete()
                new_pins = []
                for p in pins_data:
                    side = p.get('side', 'left')
                    if side not in ['left', 'right']:
                        side = 'left'
                    pin_number = int(p.get('pin_number', 1))
                    pin_label = str(p.get('pin_label', '')).strip()
                    signal_type = str(p.get('signal_type', 'GPIO')).strip()
                    description = str(p.get('description', '')).strip()

                    if pin_label:
                        new_pins.append(ComponentPinouts(
                            component=component,
                            side=side,
                            pin_number=pin_number,
                            pin_label=pin_label,
                            signal_type=signal_type,
                            description=description,
                        ))

                ComponentPinouts.objects.bulk_create(new_pins)
                messages.success(request, f"Розпіновку для «{component.part_number}» успішно збережено ({len(new_pins)} пінів).")
                return redirect('catalog:pinout_view', pk=component.pk)

        except Exception as e:
            messages.error(request, f"Помилка при збереженні розпіновки: {str(e)}")

    pinouts = component.pinouts.all().order_by('side', 'pin_number')
    left_pins = [p for p in pinouts if p.side == 'left']
    right_pins = [p for p in pinouts if p.side == 'right']

    # Серіалізуємо поточні піни для клієнтського JS конструктора
    existing_pins = [
        {
            'side': p.side,
            'pin_number': p.pin_number,
            'pin_label': p.pin_label,
            'signal_type': p.signal_type,
            'description': p.description or '',
        }
        for p in pinouts
    ]

    return render(request, 'catalog/pinout_builder.html', {
        'component': component,
        'existing_pins': existing_pins,
        'existing_pins_json': json.dumps(existing_pins),
        'signal_choices': [c[0] for c in ComponentPinouts.SIGNAL_TYPES],
        'left_pins': left_pins,
        'right_pins': right_pins,
    })


@login_required
@user_passes_test(is_staff_check)
def pinout_save_api(request, pk):
    """
    AJAX API для швидкого збереження розпіновки без перезавантаження сторінки.
    """
    import json
    from django.http import JsonResponse
    from django.db import transaction

    if request.method != 'POST':
        return JsonResponse({'error': 'Тільки POST запити дозволені'}, status=405)

    component = get_object_or_404(Components, pk=pk)
    try:
        data = json.loads(request.body.decode('utf-8'))
        if isinstance(data, list):
            pins = data
        elif isinstance(data, dict):
            pins = data.get('pins', [])
        else:
            pins = []

        with transaction.atomic():
            ComponentPinouts.objects.filter(component=component).delete()
            new_pins = []
            for p in pins:
                side = p.get('side', 'left')
                if side not in ['left', 'right']:
                    side = 'left'
                pin_number = int(p.get('pin_number', 1))
                pin_label = str(p.get('pin_label', '')).strip()
                signal_type = str(p.get('signal_type', 'GPIO')).strip()
                description = str(p.get('description', '')).strip()

                if pin_label:
                    new_pins.append(ComponentPinouts(
                        component=component,
                        side=side,
                        pin_number=pin_number,
                        pin_label=pin_label,
                        signal_type=signal_type,
                        description=description,
                    ))

            ComponentPinouts.objects.bulk_create(new_pins)

        return JsonResponse({
            'success': True,
            'count': len(new_pins),
            'saved_count': len(new_pins),
            'message': f'Успішно збережено {len(new_pins)} виводів'
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

