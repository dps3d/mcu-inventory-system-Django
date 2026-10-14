from django.contrib import admin
from .models import Categories, Components, ComponentPinouts


class ComponentPinoutsInline(admin.TabularInline):
    model = ComponentPinouts
    extra = 2
    ordering = ('side', 'pin_number')


@admin.register(Categories)
class CategoriesAdmin(admin.ModelAdmin):
    list_display = ('category_id', 'name', 'parent', 'description')
    search_fields = ('name',)
    list_filter = ('parent',)
    list_select_related = ('parent',)


@admin.register(Components)
class ComponentsAdmin(admin.ModelAdmin):
    list_display = ('component_id', 'part_number', 'category', 'package_type', 'value_nominal', 'min_threshold', 'created_at')
    list_filter = ('category', 'package_type')
    search_fields = ('part_number', 'value_nominal', 'specifications')
    list_select_related = ('category',)
    inlines = [ComponentPinoutsInline]


@admin.register(ComponentPinouts)
class ComponentPinoutsAdmin(admin.ModelAdmin):
    list_display = ('pinout_id', 'component', 'side', 'pin_number', 'pin_label', 'signal_type', 'description')
    list_filter = ('signal_type', 'side', 'component__category')
    search_fields = ('component__part_number', 'pin_label')
    list_select_related = ('component', 'component__category')
