from django.contrib import admin
from .models import StorageLocations, InventoryStocks, StockTransactions, Suppliers, Orders, OrderItems


class OrderItemsInline(admin.TabularInline):
    model = OrderItems
    extra = 1


@admin.register(StorageLocations)
class StorageLocationsAdmin(admin.ModelAdmin):
    list_display = ('location_id', 'box_number', 'shelf', 'cell_code', 'category_pill_badge')
    search_fields = ('box_number', 'cell_code', 'shelf')
    list_filter = ('box_number', 'shelf')

    def category_pill_badge(self, obj):
        pill = obj.get_category_pill()
        return f"{pill['label']} ({pill['type']})"
    category_pill_badge.short_description = "Категорії комірки"


@admin.register(InventoryStocks)
class InventoryStocksAdmin(admin.ModelAdmin):
    list_display = ('stock_id', 'component', 'location', 'quantity_on_hand', 'quantity_reserved', 'available_stock', 'unit_price')
    list_filter = ('location__box_number', 'component__category')
    search_fields = ('component__part_number', 'location__cell_code')

    def available_stock(self, obj):
        return obj.free_stock
    available_stock.short_description = "Вільний залишок"


@admin.register(StockTransactions)
class StockTransactionsAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'stock', 'transaction_type', 'quantity_change', 'reference_id', 'created_at')
    list_filter = ('transaction_type', 'created_at')
    search_fields = ('stock__component__part_number', 'notes')


@admin.register(Suppliers)
class SuppliersAdmin(admin.ModelAdmin):
    list_display = ('supplier_id', 'name', 'url')
    search_fields = ('name',)


@admin.register(Orders)
class OrdersAdmin(admin.ModelAdmin):
    list_display = ('order_id', 'supplier', 'tracking_number', 'status', 'order_date', 'expected_delivery')
    list_filter = ('status', 'order_date')
    search_fields = ('tracking_number', 'supplier__name')
    inlines = [OrderItemsInline]


@admin.register(OrderItems)
class OrderItemsAdmin(admin.ModelAdmin):
    list_display = ('order_item_id', 'order', 'component', 'quantity_ordered', 'unit_price')
    list_filter = ('order__status',)
    search_fields = ('component__part_number', 'order__tracking_number')
