from django import forms
from .models import StorageLocations, InventoryStocks, StockTransactions, Suppliers
from catalog.models import Components


class StorageLocationForm(forms.ModelForm):
    class Meta:
        model = StorageLocations
        fields = ['box_number', 'shelf', 'cell_code']
        widgets = {
            'box_number': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Наприклад: Органайзер A, Шафа 1...'
            }),
            'shelf': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Наприклад: Ряд 1, Полиця 2 (опціонально)...'
            }),
            'cell_code': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Наприклад: A1, B3, 12...'
            }),
        }

    def clean_box_number(self):
        val = self.cleaned_data.get('box_number', '').strip()
        if not val:
            raise forms.ValidationError("Вкажіть назву органайзера.")
        if len(val) > 50:
            raise forms.ValidationError("Назва органайзера не може перевищувати 50 символів.")
        return val

    def clean_shelf(self):
        val = (self.cleaned_data.get('shelf') or '').strip()
        if len(val) > 50:
            raise forms.ValidationError("Назва ряду/полиці не може перевищувати 50 символів.")
        return val

    def clean_cell_code(self):
        val = self.cleaned_data.get('cell_code', '').strip()
        if not val:
            raise forms.ValidationError("Вкажіть код комірки.")
        if len(val) > 20:
            raise forms.ValidationError("Код комірки не може перевищувати 20 символів.")
        return val

    def clean(self):
        cleaned_data = super().clean()
        box = cleaned_data.get('box_number')
        shelf = cleaned_data.get('shelf') or ''
        cell = cleaned_data.get('cell_code')
        if box and cell:
            qs = StorageLocations.objects.filter(box_number=box, shelf=shelf, cell_code=cell)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                loc_name = f"в ряду «{shelf}»" if shelf else "(без ряду)"
                raise forms.ValidationError(f"Комірка «{cell}» вже існує в органайзері «{box}» {loc_name}!")
        return cleaned_data


class QuickStockOperationForm(forms.Form):
    OPERATION_CHOICES = [
        ('purchase_in', 'Покласти (Надходження на склад)'),
        ('consumption_out', 'Взяти (Списання для роботи/лабораторії)'),
        ('return', 'Повернення (Повернення залишків у комірку)'),
        ('adjustment', 'Коригування (Інвентаризація)'),
    ]

    component = forms.ModelChoiceField(
        queryset=Components.objects.select_related('category').order_by('part_number'),
        label="Компонент",
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'opComponentSelect'})
    )
    location = forms.ModelChoiceField(
        queryset=StorageLocations.objects.all().order_by('box_number', 'shelf', 'cell_code'),
        label="Комірка зберігання",
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'opLocationSelect'})
    )
    transaction_type = forms.ChoiceField(
        choices=OPERATION_CHOICES,
        label="Тип операції",
        initial='purchase_in',
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'opTypeSelect'})
    )
    quantity = forms.IntegerField(
        min_value=0,
        max_value=10000,
        label="Кількість (шт)",
        widget=forms.NumberInput(attrs={
            'class': 'form-input qty-number-input',
            'min': '0',
            'max': '10000',
            'value': '1',
            'id': 'opQuantityInput'
        })
    )
    unit_price = forms.DecimalField(
        min_value=0,
        max_value=1000000,
        max_digits=10,
        decimal_places=2,
        required=False,
        label="Ціна за од. (грн, опціонально)",
        widget=forms.NumberInput(attrs={'class': 'form-input', 'placeholder': '0.00', 'step': '0.01', 'min': '0', 'max': '1000000'})
    )
    notes = forms.CharField(
        max_length=255,
        required=False,
        label="Примітка / Ціль",
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Наприклад: Збірка стенду, закупка, повернення...'})
    )

    def clean_quantity(self):
        qty = self.cleaned_data.get('quantity')
        if qty is None:
            raise forms.ValidationError("Будь ласка, вкажіть кількість.")
        if qty < 0:
            raise forms.ValidationError("Кількість не може бути від'ємною.")
        if qty > 10000:
            raise forms.ValidationError("Кількість для однієї операції не може перевищувати 10 000 шт.")
        return qty

    def clean_unit_price(self):
        price = self.cleaned_data.get('unit_price')
        if price is not None:
            if price < 0:
                raise forms.ValidationError("Ціна не може бути від'ємною.")
            if price > 1000000:
                raise forms.ValidationError("Ціна не може перевищувати 1 000 000 грн.")
        return price

    def clean_notes(self):
        notes = self.cleaned_data.get('notes', '')
        if notes:
            notes = notes.strip()
            if '<script' in notes.lower() or 'javascript:' in notes.lower():
                raise forms.ValidationError("Неприпустимий вміст у полі примітки.")
        return notes

    def clean(self):
        cleaned_data = super().clean()
        op_type = cleaned_data.get('transaction_type')
        qty = cleaned_data.get('quantity')
        component = cleaned_data.get('component')
        location = cleaned_data.get('location')

        if not (op_type and qty is not None and component and location):
            return cleaned_data

        # Для звичайних операцій кількість повинна бути щонайменше 1 шт
        if op_type in ['purchase_in', 'consumption_out', 'return'] and qty <= 0:
            self.add_error('quantity', "Кількість для цієї операції повинна бути не менше 1 шт.")
            return cleaned_data

        stock = InventoryStocks.objects.filter(component=component, location=location).first()

        if op_type == 'consumption_out':
            if not stock or stock.quantity_on_hand <= 0:
                raise forms.ValidationError(
                    f"У комірці «{location}» немає деталі «{component.part_number}» (наявний залишок: 0 шт). Списання неможливе."
                )
            if qty > stock.free_stock:
                if stock.quantity_reserved > 0:
                    raise forms.ValidationError(
                        f"Недостатньо вільного залишку для списання! "
                        f"У комірці є {stock.quantity_on_hand} шт, але {stock.quantity_reserved} шт зарезервовано під проєкти. "
                        f"Вільно для взяття лише {stock.free_stock} шт (запитано {qty} шт)."
                    )
                else:
                    raise forms.ValidationError(
                        f"Недостатньо деталей у комірці! Наявний залишок: {stock.quantity_on_hand} шт (запитано {qty} шт)."
                    )

        elif op_type in ['purchase_in', 'return']:
            current_on_hand = stock.quantity_on_hand if stock else 0
            if current_on_hand + qty > 50000:
                raise forms.ValidationError(
                    f"Перевищено максимальну місткість комірки (50 000 шт)! "
                    f"Поточний залишок: {current_on_hand} шт, спроба додати: {qty} шт."
                )

        elif op_type == 'adjustment':
            reserved = stock.quantity_reserved if stock else 0
            if qty < reserved:
                raise forms.ValidationError(
                    f"Неможливо встановити залишок {qty} шт: зарезервовано {reserved} шт під активні проєкти. "
                    f"Фактичний залишок не може бути меншим за зарезервовану кількість."
                )
            if qty > 50000:
                raise forms.ValidationError("Фактичний залишок для однієї комірки не може перевищувати 50 000 шт.")

        return cleaned_data


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Suppliers
        fields = ['name', 'url', 'contact_notes']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Назва компанії/постачальника'}),
            'url': forms.URLInput(attrs={'class': 'form-input', 'placeholder': 'https://...'}),
            'contact_notes': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3, 'placeholder': 'Контакти, менеджери, умови доставки...'}),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise forms.ValidationError("Вкажіть назву постачальника.")
        if len(name) > 100:
            raise forms.ValidationError("Назва не повинна перевищувати 100 символів.")
        return name

    def clean_url(self):
        url = self.cleaned_data.get('url')
        if url:
            url_clean = url.strip()
            url_lower = url_clean.lower()
            if not (url_lower.startswith('http://') or url_lower.startswith('https://')):
                raise forms.ValidationError("URL веб-сайту повинен починатися з http:// або https://")
            if 'javascript:' in url_lower or 'data:' in url_lower:
                raise forms.ValidationError("Недопустимий протокол URL (заборонено javascript: та data:)")
            return url_clean
        return url
