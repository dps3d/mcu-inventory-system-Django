from django import forms
from .models import Components, Categories
from .constants import STANDARD_PACKAGES


class ComponentForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Оптимізація вибірки категорій з select_related('parent') для запобігання N+1
        self.fields['category'].queryset = Categories.objects.select_related('parent').all()

    class Meta:
        model = Components
        fields = [
            'part_number',
            'category',
            'package_type',
            'value_nominal',
            'specifications',
            'min_threshold',
            'datasheet_url',
            'image_file',
            'image_path',
        ]
        widgets = {
            'part_number': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'наприклад: STM32F103C8T6 або ATmega328P',
                'required': True,
            }),
            'category': forms.Select(attrs={
                'class': 'form-select',
                'required': True,
            }),
            'package_type': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Виберіть зі списку або введіть: DIP-28, LQFP-48...',
                'list': 'standardPackagesList',
            }),
            'value_nominal': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'наприклад: 72MHz / 64KB Flash, 10k 1%, 100nF...',
            }),
            'specifications': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 4,
                'placeholder': 'Короткий технічний опис, напруга живлення (3.3V/5V), особливості інтерфейсів...',
            }),
            'min_threshold': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': '0',
                'placeholder': '0',
            }),
            'datasheet_url': forms.URLInput(attrs={
                'class': 'form-input',
                'placeholder': 'https://alldatasheet.com/... або пряме посилання на PDF',
            }),
            'image_file': forms.ClearableFileInput(attrs={
                'class': 'form-file-input',
            }),
            'image_path': forms.URLInput(attrs={
                'class': 'form-input',
                'placeholder': 'Або пряме зовнішнє посилання на зображення (URL)',
            }),
        }
        labels = {
            'part_number': 'Парт-номер / Маркування',
            'category': 'Категорія',
            'package_type': 'Тип корпусу',
            'value_nominal': 'Номінал / Конфігурація',
            'specifications': 'Технічні характеристики',
            'min_threshold': 'Мінімальний поріг запасу (шт)',
            'datasheet_url': 'Посилання на документацію (Datasheet URL)',
            'image_file': 'Файл зображення (завантажити з ПК)',
            'image_path': 'Зовнішнє посилання на фото (URL)',
        }

    def clean_part_number(self):
        val = self.cleaned_data.get('part_number', '').strip()
        if not val:
            raise forms.ValidationError("Вкажіть маркування (парт-номер).")
        if len(val) > 100:
            raise forms.ValidationError("Парт-номер не може перевищувати 100 символів.")
        qs = Components.objects.filter(part_number__iexact=val)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(f"Компонент з парт-номером «{val}» вже існує в каталозі!")
        return val

    def clean_min_threshold(self):
        val = self.cleaned_data.get('min_threshold')
        if val is not None:
            if val < 0:
                raise forms.ValidationError("Мінімальний поріг не може бути від'ємним.")
            if val > 100000:
                raise forms.ValidationError("Мінімальний поріг не може перевищувати 100 000 шт.")
        return val

    def clean_datasheet_url(self):
        url = self.cleaned_data.get('datasheet_url')
        if url:
            url_clean = url.strip()
            url_lower = url_clean.lower()
            if not (url_lower.startswith('http://') or url_lower.startswith('https://')):
                raise forms.ValidationError("URL документації повинен починатися з http:// або https://")
            if 'javascript:' in url_lower or 'data:' in url_lower:
                raise forms.ValidationError("Недопустимий протокол URL (заборонено javascript: та data:)")
            return url_clean
        return url

    def clean_image_path(self):
        url = self.cleaned_data.get('image_path')
        if url:
            url_clean = url.strip()
            url_lower = url_clean.lower()
            if not (url_lower.startswith('http://') or url_lower.startswith('https://')):
                raise forms.ValidationError("URL фото повинен починатися з http:// або https://")
            if 'javascript:' in url_lower or 'data:' in url_lower:
                raise forms.ValidationError("Недопустимий протокол URL (заборонено javascript: та data:)")
            return url_clean
        return url
