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
                'placeholder': 'Наприклад: Полиця 2, Секція B...'
            }),
            'cell_code': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Наприклад: A1, B3, 12...'
            }),
        }


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
        min_value=1,
        label="Кількість (шт)",
        widget=forms.NumberInput(attrs={'class': 'form-input', 'min': '1', 'value': '1', 'id': 'opQuantityInput'})
    )
    unit_price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        label="Ціна за од. (грн, опціонально)",
        widget=forms.NumberInput(attrs={'class': 'form-input', 'placeholder': '0.00', 'step': '0.01'})
    )
    notes = forms.CharField(
        max_length=255,
        required=False,
        label="Примітка / Ціль",
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Наприклад: Збірка стенду, закупка, повернення...'})
    )


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Suppliers
        fields = ['name', 'url', 'contact_notes']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Назва компанії/постачальника'}),
            'url': forms.URLInput(attrs={'class': 'form-input', 'placeholder': 'https://...'}),
            'contact_notes': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3, 'placeholder': 'Контакти, менеджери, умови доставки...'}),
        }
