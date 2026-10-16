from django.db import models


class StorageLocations(models.Model):
    location_id = models.AutoField(primary_key=True)
    box_number = models.CharField(max_length=50, verbose_name="Органайзер / Коробка")
    shelf = models.CharField(max_length=50, null=True, blank=True, verbose_name="Полиця / Секція")
    cell_code = models.CharField(max_length=20, verbose_name="Код комірки")

    class Meta:
        db_table = 'storage_locations'
        verbose_name = 'Комірка зберігання'
        verbose_name_plural = 'Комірки зберігання'
        unique_together = (('box_number', 'shelf', 'cell_code'),)
        ordering = ['box_number', 'shelf', 'cell_code']

    def __str__(self):
        shelf_str = f" / {self.shelf}" if self.shelf else ""
        return f"{self.box_number}{shelf_str} [{self.cell_code}]"

    def get_category_pill(self):
        """
        4.4. Складський облік та колірні комірки:
        - 1 категорія: пігулка кольору категорії.
        - 2 категорії: спокійний змішаний відтінок.
        - 3+ категорій: автоматична сіра пігулка 'Різне'.
        Оптимізовано для запобігання N+1 через підтримку prefetch_related('stocks__component__category').
        """
        if hasattr(self, '_prefetched_objects_cache') and 'stocks' in self._prefetched_objects_cache:
            cats = set()
            for s in self.stocks.all():
                if s.quantity_on_hand > 0 and s.component_id and s.component and s.component.category_id:
                    cats.add((s.component.category_id, s.component.category.name))
            cat_ids = list(cats)
        else:
            cat_ids = list(
                self.stocks.filter(quantity_on_hand__gt=0)
                .order_by()
                .values_list('component__category_id', 'component__category__name')
                .distinct()
            )
        count = len(cat_ids)
        if count == 0:
            return {'type': 'empty', 'label': 'Порожня', 'css_class': 'pill-empty'}
        elif count == 1:
            name = cat_ids[0][1]
            return {'type': 'single', 'label': name, 'css_class': 'pill-single'}
        elif count == 2:
            names = " + ".join([c[1] for c in cat_ids])
            return {'type': 'dual', 'label': names, 'css_class': 'pill-dual'}
        else:
            return {'type': 'mixed', 'label': 'Різне', 'css_class': 'pill-mixed'}


class InventoryStocks(models.Model):
    stock_id = models.AutoField(primary_key=True)
    component = models.ForeignKey(
        'catalog.Components',
        on_delete=models.PROTECT,
        related_name='stocks',
        db_column='component_id',
        verbose_name="Компонент"
    )
    location = models.ForeignKey(
        StorageLocations,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stocks',
        db_column='location_id',
        verbose_name="Комірка зберігання"
    )
    quantity_on_hand = models.IntegerField(default=0, verbose_name="Фактичний залишок")
    quantity_reserved = models.IntegerField(default=0, verbose_name="Зарезервовано")
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Ціна за од.")

    class Meta:
        db_table = 'inventory_stocks'
        verbose_name = 'Залишок на складі'
        verbose_name_plural = 'Залишки на складі'
        ordering = ['component']

    def __str__(self):
        loc = f" @ {self.location}" if self.location else " (без комірки)"
        return f"{self.component.part_number}: {self.quantity_on_hand} шт{loc}"

    @property
    def free_stock(self):
        """Вільний залишок для видачі та нових резервувань"""
        return max(0, self.quantity_on_hand - self.quantity_reserved)


class StockTransactions(models.Model):
    TRANSACTION_TYPES = [
        ('purchase_in', 'Покласти (Надходження)'),
        ('consumption_out', 'Взяти (Списання)'),
        ('reservation', 'Резервування'),
        ('adjustment', 'Коригування'),
        ('return', 'Повернення'),
    ]

    transaction_id = models.AutoField(primary_key=True)
    stock = models.ForeignKey(
        InventoryStocks,
        on_delete=models.CASCADE,
        related_name='transactions',
        db_column='stock_id',
        verbose_name="Позиція складу"
    )
    transaction_type = models.CharField(max_length=30, choices=TRANSACTION_TYPES, verbose_name="Тип операції")
    quantity_change = models.IntegerField(verbose_name="Зміна кількості")
    reference_id = models.IntegerField(null=True, blank=True, verbose_name="ID зв'язаного об'єкта")
    notes = models.CharField(max_length=255, null=True, blank=True, verbose_name="Примітка")
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True, verbose_name="Дата та час")

    class Meta:
        db_table = 'stock_transactions'
        verbose_name = 'Складська операція'
        verbose_name_plural = 'Складські операції'
        ordering = ['-created_at']

    def __str__(self):
        sign = "+" if self.quantity_change > 0 else ""
        return f"{self.created_at:%Y-%m-%d %H:%M} | {self.stock.component.part_number} | {sign}{self.quantity_change} ({self.get_transaction_type_display()})"


class Suppliers(models.Model):
    supplier_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=150, verbose_name="Постачальник")
    url = models.CharField(max_length=255, null=True, blank=True, verbose_name="Вебсайт")
    contact_notes = models.TextField(null=True, blank=True, verbose_name="Контакти / Нотатки")

    class Meta:
        db_table = 'suppliers'
        verbose_name = 'Постачальник'
        verbose_name_plural = 'Постачальники'
        ordering = ['name']

    def __str__(self):
        return self.name


class Orders(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Очікує'),
        ('ordered', 'Замовлено'),
        ('shipped', 'Відправлено'),
        ('delivered', 'Доставлено'),
        ('cancelled', 'Скасовано'),
    ]

    order_id = models.AutoField(primary_key=True)
    supplier = models.ForeignKey(
        Suppliers,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
        db_column='supplier_id',
        verbose_name="Постачальник"
    )
    tracking_number = models.CharField(max_length=100, null=True, blank=True, verbose_name="Номер ТТН / трекінгу")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Статус")
    order_date = models.DateTimeField(null=True, blank=True, verbose_name="Дата замовлення")
    expected_delivery = models.DateField(null=True, blank=True, verbose_name="Очікувана доставка")

    class Meta:
        db_table = 'orders'
        verbose_name = 'Замовлення'
        verbose_name_plural = 'Замовлення'
        ordering = ['-order_date']

    def __str__(self):
        sup = self.supplier.name if self.supplier else "Невідомий постачальник"
        return f"Замовлення #{self.order_id} ({sup}) - {self.get_status_display()}"


class OrderItems(models.Model):
    order_item_id = models.AutoField(primary_key=True)
    order = models.ForeignKey(
        Orders,
        on_delete=models.CASCADE,
        related_name='items',
        db_column='order_id',
        verbose_name="Замовлення"
    )
    component = models.ForeignKey(
        'catalog.Components',
        on_delete=models.PROTECT,
        related_name='order_items',
        db_column='component_id',
        verbose_name="Компонент"
    )
    quantity_ordered = models.IntegerField(verbose_name="Замовлена кількість")
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Ціна за од.")

    class Meta:
        db_table = 'order_items'
        verbose_name = 'Позиція замовлення'
        verbose_name_plural = 'Позиції замовлень'

    def __str__(self):
        return f"{self.component.part_number} x {self.quantity_ordered} (Замовлення #{self.order.order_id})"
