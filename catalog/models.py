from django.db import models
from .validators import validate_part_number


class Categories(models.Model):
    category_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, verbose_name="Назва категорії")
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subcategories',
        db_column='parent_id',
        verbose_name="Батьківська категорія"
    )
    description = models.TextField(null=True, blank=True, verbose_name="Опис")

    class Meta:
        db_table = 'categories'
        verbose_name = 'Категорія'
        verbose_name_plural = 'Категорії'
        ordering = ['name']

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} → {self.name}"
        return self.name


class Components(models.Model):
    component_id = models.AutoField(primary_key=True)
    category = models.ForeignKey(
        Categories,
        on_delete=models.PROTECT,
        related_name='components',
        db_column='category_id',
        verbose_name="Категорія"
    )
    part_number = models.CharField(
        max_length=100,
        verbose_name="Парт-номер / Маркування",
        validators=[validate_part_number]
    )
    package_type = models.CharField(max_length=50, null=True, blank=True, verbose_name="Тип корпусу")
    value_nominal = models.CharField(max_length=50, null=True, blank=True, verbose_name="Номінал")
    specifications = models.TextField(null=True, blank=True, verbose_name="Технічні характеристики")
    min_threshold = models.IntegerField(null=True, blank=True, default=0, verbose_name="Мінімальний поріг")
    datasheet_url = models.CharField(max_length=255, null=True, blank=True, verbose_name="URL даташиту")
    image_path = models.CharField(max_length=255, null=True, blank=True, verbose_name="URL зображення")
    image_file = models.ImageField(upload_to='components/', null=True, blank=True, verbose_name="Файл фото")
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True, verbose_name="Дата додавання")

    class Meta:
        db_table = 'components'
        verbose_name = 'Компонент'
        verbose_name_plural = 'Компоненти'
        ordering = ['part_number']

    def __str__(self):
        val = f" ({self.value_nominal})" if self.value_nominal else ""
        return f"{self.part_number}{val}"

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('catalog:detail', kwargs={'pk': self.pk})

    @property
    def image_url(self):
        if self.image_file:
            return self.image_file.url
        if self.image_path:
            return self.image_path
        return None


class ComponentPinouts(models.Model):
    SIDE_CHOICES = [
        ('left', 'Ліва сторона'),
        ('right', 'Права сторона'),
    ]

    SIGNAL_TYPES = [
        ('GPIO', 'GPIO'),
        ('Power', 'Power'),
        ('Ground', 'Ground'),
        ('I2C', 'I2C'),
        ('UART', 'UART'),
        ('SPI', 'SPI'),
        ('ADC', 'ADC'),
        ('Reset', 'Reset'),
    ]

    pinout_id = models.AutoField(primary_key=True)
    component = models.ForeignKey(
        Components,
        on_delete=models.CASCADE,
        related_name='pinouts',
        db_column='component_id',
        verbose_name="Компонент"
    )
    side = models.CharField(max_length=10, choices=SIDE_CHOICES, verbose_name="Сторона")
    pin_number = models.IntegerField(verbose_name="Номер виводу")
    pin_label = models.CharField(max_length=50, verbose_name="Маркування виводу")
    signal_type = models.CharField(max_length=20, choices=SIGNAL_TYPES, default='GPIO', verbose_name="Тип сигналу")
    description = models.CharField(max_length=255, null=True, blank=True, verbose_name="Опис")

    class Meta:
        db_table = 'component_pinouts'
        verbose_name = 'Вивід розпіновки'
        verbose_name_plural = 'Розпіновки'
        unique_together = (('component', 'side', 'pin_number'),)
        ordering = ['component', 'side', 'pin_number']

    def __str__(self):
        return f"{self.component.part_number} | {self.side}#{self.pin_number} - {self.pin_label} ({self.signal_type})"
