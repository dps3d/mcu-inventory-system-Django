from django.shortcuts import render
from catalog.models import Components, Categories
from inventory.models import StorageLocations, Suppliers
from projects.models import Projects


def home(request):
    try:
        components_count = Components.objects.count()
        categories_count = Categories.objects.count()
        locations_count = StorageLocations.objects.count()
        suppliers_count = Suppliers.objects.count()
        projects_count = Projects.objects.count()

        popular_categories = Categories.objects.filter(parent__isnull=True).order_by('name')[:8]
        recent_components = (
            Components.objects.select_related('category')
            .order_by('-created_at', '-component_id')[:5]
        )
    except Exception:
        components_count = 0
        categories_count = 0
        locations_count = 0
        suppliers_count = 0
        projects_count = 0
        popular_categories = []
        recent_components = []

    context = {
        'components_count': components_count,
        'categories_count': categories_count,
        'locations_count': locations_count,
        'suppliers_count': suppliers_count,
        'projects_count': projects_count,
        'popular_categories': popular_categories,
        'recent_components': recent_components,
    }
    return render(request, 'home.html', context)
