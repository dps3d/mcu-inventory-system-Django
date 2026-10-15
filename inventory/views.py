from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.db import transaction, models
from django.db.models import F, Sum, Q, Count, Prefetch
from django.core.paginator import Paginator
from django.urls import reverse
from django.http import JsonResponse

from .models import StorageLocations, InventoryStocks, StockTransactions, Suppliers
from .forms import StorageLocationForm, QuickStockOperationForm, SupplierForm
from catalog.models import Components


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

    # Global KPI Metrics
    total_locations = StorageLocations.objects.count()
    stocks_qs = InventoryStocks.objects.select_related('component', 'location')
    total_positions = stocks_qs.count()
    total_units_data = stocks_qs.aggregate(
        total_on_hand=Sum('quantity_on_hand'),
        total_reserved=Sum('quantity_reserved')
    )
    total_on_hand = total_units_data['total_on_hand'] or 0
    total_reserved = total_units_data['total_reserved'] or 0
    total_free = max(0, total_on_hand - total_reserved)

    # Deficit items count (free_stock <= min_threshold)
    deficit_count = 0
    for stock in stocks_qs:
        if stock.component and stock.free_stock <= stock.component.min_threshold:
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

        # Precompute pills and stats for locations to guarantee instant rendering
        locations_data = []
        occupied_count = 0
        for loc in locations:
            pill = loc.get_category_pill()
            active_stocks = [s for s in loc.stocks.all() if s.quantity_on_hand > 0]
            if active_stocks:
                occupied_count += 1
            locations_data.append({
                'location': loc,
                'pill': pill,
                'active_stocks': active_stocks,
                'total_qty': sum(s.quantity_on_hand for s in active_stocks),
                'free_qty': sum(s.free_stock for s in active_stocks),
            })

        context.update({
            'organizers_list': organizers_list,
            'selected_box': selected_box,
            'shelves_list': shelves_list,
            'selected_shelf': selected_shelf,
            'locations_data': locations_data,
            'total_in_box': len(locations_data),
            'occupied_in_box': occupied_count,
            'empty_in_box': len(locations_data) - occupied_count,
        })

    elif active_tab == 'stocks':
        # 2. Complete Inventory Stocks Table with Deficit Filtering
        query = request.GET.get('q', '').strip()
        is_deficit_only = request.GET.get('deficit') == '1'
        selected_box = request.GET.get('box', '')

        stocks_list_qs = InventoryStocks.objects.select_related(
            'component__category', 'location'
        ).order_by('component__part_number')

        if query:
            stocks_list_qs = stocks_list_qs.filter(
                Q(component__part_number__icontains=query) |
                Q(component__description__icontains=query) |
                Q(location__box_number__icontains=query) |
                Q(location__cell_code__icontains=query)
            )

        if selected_box:
            stocks_list_qs = stocks_list_qs.filter(location__box_number=selected_box)

        # Deficit filter
        if is_deficit_only:
            # Filter in Python or DB expression
            deficit_stock_ids = [
                s.stock_id for s in stocks_list_qs
                if s.component and s.free_stock <= s.component.min_threshold
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
    Забезпечує транзакційність (atomic) та перевірку вільного залишку.
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
                        # Взяти: перевіряємо чи є достатній вільний залишок
                        free_available = stock.free_stock
                        if qty > free_available:
                            messages.error(
                                request,
                                f"Помилка списання: недостатньо вільного залишку {component.part_number} "
                                f"у комірці {location}. Доступно: {free_available} шт (запитано: {qty} шт)."
                            )
                            return redirect(request.META.get('HTTP_REFERER') or reverse('inventory:dashboard'))

                        stock.quantity_on_hand -= qty
                        delta = -qty

                    elif op_type in ['purchase_in', 'return']:
                        # Покласти або Повернення
                        stock.quantity_on_hand += qty
                        delta = qty
                        if unit_price is not None:
                            stock.unit_price = unit_price

                    elif op_type == 'adjustment':
                        # Коригування фактичного залишку
                        delta = qty - stock.quantity_on_hand
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
            errors = " ".join([f"{f}: {e.as_text()}" for f, e in form.errors.items()])
            messages.error(request, f"Некоректні дані у формі операції: {errors}")

    return redirect(request.META.get('HTTP_REFERER') or reverse('inventory:dashboard'))


def location_detail(request, pk):
    """
    Детальний перегляд окремої комірки: компоненти, вільні та зарезервовані залишки, журнал операцій комірки.
    """
    location = get_object_or_404(
        StorageLocations.objects.prefetch_related('stocks__component__category'),
        pk=pk
    )
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
    location = get_object_or_404(StorageLocations, pk=pk)
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
