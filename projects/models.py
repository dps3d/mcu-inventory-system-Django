from django.db import models


class Projects(models.Model):
    STATUS_CHOICES = [
        ('planning', 'Планування'),
        ('in_progress', 'В розробці'),
        ('completed', 'Завершено'),
        ('cancelled', 'Скасовано'),
    ]

    project_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=150, verbose_name="Назва проєкту")
    description = models.TextField(null=True, blank=True, verbose_name="Опис проєкту")
    image_path = models.CharField(max_length=255, null=True, blank=True, verbose_name="URL зображення")
    image_file = models.ImageField(upload_to='projects/', null=True, blank=True, verbose_name="Файл зображення")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planning', verbose_name="Статус проєкту")
    is_private = models.BooleanField(default=True, verbose_name="Приватний проєкт")
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True, verbose_name="Дата створення")

    class Meta:
        db_table = 'projects'
        verbose_name = 'Проєкт'
        verbose_name_plural = 'Проєкти'
        ordering = ['-created_at']

    def __str__(self):
        priv = " [Приватний]" if self.is_private else " [Публічний]"
        return f"{self.name}{priv}"

    @property
    def image_url(self):
        if self.image_file:
            return self.image_file.url
        if self.image_path:
            return self.image_path
        return None


class ProjectBoms(models.Model):
    bom_id = models.AutoField(primary_key=True)
    project = models.ForeignKey(
        Projects,
        on_delete=models.CASCADE,
        related_name='boms',
        db_column='project_id',
        verbose_name="Проєкт"
    )
    component = models.ForeignKey(
        'catalog.Components',
        on_delete=models.PROTECT,
        related_name='project_boms',
        db_column='component_id',
        verbose_name="Компонент"
    )
    quantity_required = models.IntegerField(verbose_name="Необхідна кількість на 1 виріб")
    designator = models.CharField(max_length=100, null=True, blank=True, verbose_name="Позиційне позначення (Designator)")

    class Meta:
        db_table = 'project_boms'
        verbose_name = 'Позиція BOM'
        verbose_name_plural = 'Специфікації BOM'
        ordering = ['project', 'component']

    def __str__(self):
        desig = f" ({self.designator})" if self.designator else ""
        return f"{self.project.name} | {self.component.part_number} x {self.quantity_required}{desig}"


class ProjectAllocations(models.Model):
    STATUS_CHOICES = [
        ('reserved', 'Зарезервовано'),
        ('consumed', 'Списано / Використано'),
    ]

    allocation_id = models.AutoField(primary_key=True)
    bom = models.ForeignKey(
        ProjectBoms,
        on_delete=models.CASCADE,
        related_name='allocations',
        db_column='bom_id',
        verbose_name="Позиція BOM"
    )
    stock = models.ForeignKey(
        'inventory.InventoryStocks',
        on_delete=models.PROTECT,
        related_name='allocations',
        db_column='stock_id',
        verbose_name="Складський залишок"
    )
    allocated_quantity = models.IntegerField(verbose_name="Виділена/зарезервована кількість")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='reserved', verbose_name="Статус")
    allocated_at = models.DateTimeField(auto_now_add=True, null=True, blank=True, verbose_name="Дата операції")

    class Meta:
        db_table = 'project_allocations'
        verbose_name = 'Резервування деталей'
        verbose_name_plural = 'Резервування деталей'
        ordering = ['-allocated_at']

    def __str__(self):
        return f"Резерв #{self.allocation_id}: {self.allocated_quantity} шт для {self.bom.project.name}"
