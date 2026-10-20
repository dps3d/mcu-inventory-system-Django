from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.core.paginator import Paginator
from django.db.models import Sum, Q, F
from django.db.models.functions import Coalesce
from .models import Components, Categories, ComponentPinouts
from .forms import ComponentForm
from .constants import STANDARD_PACKAGES


def is_staff_check(user):
    return user.is_authenticated and user.is_staff


class ComponentListView(ListView):
    """
    Generic ListView для виводу списку компонентів каталогу.
    Перевизначено get_queryset() (фільтрація, пошук, залишки, сортування)
    та get_context_data() (довідники, параметри запиту, лічильники).
    """
    model = Components
    template_name = 'catalog/component_list.html'
    context_object_name = 'components'
    paginate_by = 12

    def get_queryset(self):
        query = self.request.GET.get('q', '').strip()
        category_id = self.request.GET.get('category', '').strip()
        package_type = self.request.GET.get('package', '').strip()
        stock_status = self.request.GET.get('status', '').strip()
        sort_by = self.request.GET.get('sort', 'name_asc').strip()

        qs = Components.objects.select_related('category').annotate(
            total_on_hand=Coalesce(Sum('stocks__quantity_on_hand'), 0),
            total_reserved=Coalesce(Sum('stocks__quantity_reserved'), 0),
        ).annotate(
            total_free=F('total_on_hand') - F('total_reserved')
        )

        if query:
            qs = qs.filter(
                Q(part_number__icontains=query) |
                Q(specifications__icontains=query) |
                Q(value_nominal__icontains=query) |
                Q(package_type__icontains=query) |
                Q(category__name__icontains=query)
            )

        if category_id:
            qs = qs.filter(category_id=category_id)

        if package_type:
            qs = qs.filter(package_type=package_type)

        if stock_status == 'in_stock':
            qs = qs.filter(total_free__gt=0)
        elif stock_status == 'low_stock':
            qs = qs.filter(
                total_free__gt=0,
                total_free__lte=F('min_threshold')
            )
        elif stock_status == 'out_of_stock':
            qs = qs.filter(total_free__lte=0)

        if sort_by == 'name_desc':
            qs = qs.order_by('-part_number')
        elif sort_by == 'stock_desc':
            qs = qs.order_by('-total_free', 'part_number')
        elif sort_by == 'stock_asc':
            qs = qs.order_by('total_free', 'part_number')
        elif sort_by == 'newest':
            qs = qs.order_by('-created_at', '-component_id')
        else:
            qs = qs.order_by('part_number')

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        categories = Categories.objects.select_related('parent').all()
        db_packages = list(
            Components.objects.exclude(package_type__isnull=True)
            .exclude(package_type__exact='')
            .values_list('package_type', flat=True)
            .distinct()
        )
        packages = sorted(set(db_packages + STANDARD_PACKAGES[:16]))

        context.update({
            'categories': categories,
            'packages': packages,
            'search_query': self.request.GET.get('q', '').strip(),
            'selected_category': self.request.GET.get('category', '').strip(),
            'selected_package': self.request.GET.get('package', '').strip(),
            'selected_status': self.request.GET.get('status', '').strip(),
            'selected_sort': self.request.GET.get('sort', 'name_asc').strip(),
            'view_mode': self.request.GET.get('view', 'grid').strip(),
            'total_count': context['paginator'].count if 'paginator' in context else self.get_queryset().count(),
        })
        return context


class ComponentDetailView(DetailView):
    """
    Generic DetailView для відображення детальної сторінки електронного компонента.
    Перевизначено get_context_data() для розрахунку складських статусів та виводів розпіновки.
    """
    model = Components
    template_name = 'catalog/component_detail.html'
    context_object_name = 'component'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        component = self.object
        stocks = component.stocks.select_related('location').all()
        total_on_hand = sum(s.quantity_on_hand for s in stocks)
        total_reserved = sum(s.quantity_reserved for s in stocks)
        total_free = max(0, total_on_hand - total_reserved)

        if total_free <= 0:
            stock_badge = {'type': 'danger', 'label': 'Немає на складі'}
        elif component.min_threshold and total_free <= component.min_threshold:
            stock_badge = {'type': 'warning', 'label': 'Закінчується'}
        else:
            stock_badge = {'type': 'success', 'label': 'В наявності'}

        pinouts = component.pinouts.all().order_by('side', 'pin_number')
        left_pins = [p for p in pinouts if p.side == 'left']
        right_pins = [p for p in pinouts if p.side == 'right']

        context.update({
            'stocks': stocks,
            'total_on_hand': total_on_hand,
            'total_reserved': total_reserved,
            'total_free': total_free,
            'stock_badge': stock_badge,
            'pinouts': pinouts,
            'left_pins': left_pins,
            'right_pins': right_pins,
            'has_pinouts': pinouts.exists(),
        })
        return context


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Міксин перевірки прав персоналу (is_staff) для CBV з редиректом на логін."""
    def test_func(self):
        return is_staff_check(self.request.user)

    def handle_no_permission(self):
        from django.contrib.auth.views import redirect_to_login
        return redirect_to_login(
            self.request.get_full_path(),
            self.get_login_url(),
            self.get_redirect_field_name(),
        )


class ComponentCreateView(StaffRequiredMixin, CreateView):
    """
    Generic CreateView для реєстрації нового компонента в каталозі (персонал).
    Перевизначено form_valid() (flash-повідомлення) та get_context_data().
    """
    model = Components
    form_class = ComponentForm
    template_name = 'catalog/component_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'action_title': 'Додавання нового компонента',
            'submit_label': 'Створити компонент',
            'standard_packages': STANDARD_PACKAGES,
        })
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Компонент «{self.object.part_number}» успішно додано до каталогу.")
        return response

    def get_success_url(self):
        return self.object.get_absolute_url()


class ComponentUpdateView(StaffRequiredMixin, UpdateView):
    """
    Generic UpdateView для редагування параметрів деталі.
    Перевизначено form_valid() (flash-повідомлення) та get_context_data().
    """
    model = Components
    form_class = ComponentForm
    template_name = 'catalog/component_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'component': self.object,
            'action_title': f"Редагування «{self.object.part_number}»",
            'submit_label': 'Зберегти зміни',
            'standard_packages': STANDARD_PACKAGES,
        })
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Дані компонента «{self.object.part_number}» успішно оновлено.")
        return response

    def get_success_url(self):
        return self.object.get_absolute_url()


class ComponentDeleteView(StaffRequiredMixin, DeleteView):
    """
    Generic DeleteView для видалення компонента з контролем зовнішніх ключів.
    """
    model = Components
    template_name = 'catalog/component_confirm_delete.html'
    context_object_name = 'component'
    success_url = reverse_lazy('catalog:list')

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        part_name = self.object.part_number
        try:
            response = super().delete(request, *args, **kwargs)
            messages.success(request, f"Компонент «{part_name}» видалено з каталогу.")
            return response
        except Exception:
            messages.error(
                request,
                f"Неможливо видалити компонент «{part_name}», оскільки на нього посилаються складські залишки або замовлення."
            )
            return redirect('catalog:detail', pk=self.object.pk)


# Зворотна сумісність для функціональних викликів та тестів
component_list = ComponentListView.as_view()
component_detail = ComponentDetailView.as_view()
component_create = ComponentCreateView.as_view()
component_edit = ComponentUpdateView.as_view()
component_delete = ComponentDeleteView.as_view()


def pinout_view(request, pk):
    """
    Публічний інтерактивний візуалізатор розпіновки (Pinout Viewer).
    """
    try:
        component = Components.objects.select_related('category').get(pk=pk)
    except Components.DoesNotExist:
        messages.warning(request, f"Компонент №{pk} не знайдено.")
        return redirect('catalog:list')

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
                seen_keys = set()
                for p in pins_data:
                    side = p.get('side', 'left')
                    if side not in ['left', 'right']:
                        side = 'left'
                    pin_number = int(p.get('pin_number', 1))
                    pin_label = str(p.get('pin_label', '')).strip()
                    signal_type = str(p.get('signal_type', 'GPIO')).strip()
                    description = str(p.get('description', '')).strip()

                    if pin_label:
                        key = (side, pin_number)
                        if key in seen_keys:
                            side_label = "лівій" if side == "left" else "правій"
                            raise ValueError(f"Дублювання номера виводу №{pin_number} на {side_label} стороні.")
                        seen_keys.add(key)
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
            seen_keys = set()
            for p in pins:
                side = p.get('side', 'left')
                if side not in ['left', 'right']:
                    side = 'left'
                pin_number = int(p.get('pin_number', 1))
                pin_label = str(p.get('pin_label', '')).strip()
                signal_type = str(p.get('signal_type', 'GPIO')).strip()
                description = str(p.get('description', '')).strip()

                if pin_label:
                    key = (side, pin_number)
                    if key in seen_keys:
                        side_label = "лівій" if side == "left" else "правій"
                        raise ValueError(f"Дублювання номера виводу №{pin_number} на {side_label} стороні.")
                    seen_keys.add(key)
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

