from django import forms
from .models import Components, Categories


class ComponentForm(forms.ModelForm):
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
                'placeholder': 'DIP-28, LQFP-48, QFN-32, SOIC-8, SOT-223...',
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
