from django import forms
from .models import Projects, ProjectBoms, ProjectAllocations
from catalog.models import Components
from inventory.models import InventoryStocks


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Projects
        fields = ['name', 'description', 'status', 'is_private', 'image_file', 'image_path']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Наприклад: IoT Метеостанція, Плата керування двигуном...'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 4,
                'placeholder': 'Короткий опис проєкту, призначення, технічні особливості...'
            }),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'is_private': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'image_file': forms.FileInput(attrs={'class': 'form-file-input', 'accept': 'image/*'}),
            'image_path': forms.URLInput(attrs={
                'class': 'form-input',
                'placeholder': 'https://example.com/schematic.png (опціонально)'
            }),
        }

    def clean_name(self):
        val = self.cleaned_data.get('name', '').strip()
        if not val:
            raise forms.ValidationError("Вкажіть назву проєкту.")
        if len(val) > 150:
            raise forms.ValidationError("Назва проєкту не може перевищувати 150 символів.")
        return val


class ProjectBomForm(forms.ModelForm):
    class Meta:
        model = ProjectBoms
        fields = ['component', 'quantity_required', 'designator']
        widgets = {
            'component': forms.Select(attrs={'class': 'form-select', 'id': 'bomComponentSelect'}),
            'quantity_required': forms.NumberInput(attrs={
                'class': 'form-input qty-number-input',
                'min': '1',
                'max': '10000',
                'value': '1',
                'id': 'bomQtyInput'
            }),
            'designator': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Наприклад: U1, R1, C3-C5',
                'id': 'bomDesignatorInput'
            }),
        }

    def clean_quantity_required(self):
        qty = self.cleaned_data.get('quantity_required')
        if not qty or qty < 1:
            raise forms.ValidationError("Кількість має бути не менше 1 шт.")
        if qty > 10000:
            raise forms.ValidationError("Кількість не може перевищувати 10 000 шт.")
        return qty


class BomQuickAddForm(forms.Form):
    component_id = forms.IntegerField(widget=forms.HiddenInput())
    quantity_required = forms.IntegerField(
        min_value=1,
        max_value=10000,
        initial=1,
        widget=forms.NumberInput(attrs={'class': 'form-input', 'min': '1', 'max': '10000', 'value': '1'})
    )
    designator = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Наприклад: U1, C1'})
    )


class ReserveStockForm(forms.Form):
    stock_id = forms.IntegerField(widget=forms.HiddenInput())
    quantity = forms.IntegerField(
        min_value=1,
        max_value=10000,
        widget=forms.NumberInput(attrs={'class': 'form-input', 'min': '1'})
    )
