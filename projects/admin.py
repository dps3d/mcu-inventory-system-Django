from django.contrib import admin
from .models import Projects, ProjectBoms, ProjectAllocations


class ProjectBomsInline(admin.TabularInline):
    model = ProjectBoms
    extra = 1


@admin.register(Projects)
class ProjectsAdmin(admin.ModelAdmin):
    list_display = ('project_id', 'name', 'is_private', 'status', 'created_at')
    list_filter = ('is_private', 'status', 'created_at')
    search_fields = ('name', 'description')
    inlines = [ProjectBomsInline]


@admin.register(ProjectBoms)
class ProjectBomsAdmin(admin.ModelAdmin):
    list_display = ('bom_id', 'project', 'component', 'quantity_required', 'designator')
    list_filter = ('project__status', 'component__category')
    search_fields = ('project__name', 'component__part_number', 'designator')
    list_select_related = ('project', 'component', 'component__category')


@admin.register(ProjectAllocations)
class ProjectAllocationsAdmin(admin.ModelAdmin):
    list_display = ('allocation_id', 'bom', 'stock', 'allocated_quantity', 'status', 'allocated_at')
    list_filter = ('status', 'allocated_at')
    search_fields = ('bom__project__name', 'stock__component__part_number')
    list_select_related = ('bom', 'bom__project', 'bom__component', 'stock', 'stock__component', 'stock__location')
