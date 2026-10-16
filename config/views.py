from django.shortcuts import render
from django.db.utils import OperationalError, DatabaseError
from django.contrib.auth.models import AnonymousUser
from catalog.models import Components, Categories
from inventory.models import StorageLocations, Suppliers
from projects.models import Projects


def home(request):
    db_healthy = getattr(request, 'db_healthy', True)

    if not db_healthy:
        context = {
            'components_count': 0,
            'categories_count': 0,
            'locations_count': 0,
            'suppliers_count': 0,
            'projects_count': 0,
            'popular_categories': [],
            'recent_components': [],
            'db_healthy': False,
        }
        return render(request, 'home.html', context)

    try:
        components_count = Components.objects.count()
        categories_count = Categories.objects.count()
        locations_count = StorageLocations.objects.count()
        suppliers_count = Suppliers.objects.count()
        projects_count = Projects.objects.count()

        popular_categories = list(Categories.objects.filter(parent__isnull=True).order_by('name')[:8])
        recent_components = list(
            Components.objects.select_related('category')
            .order_by('-created_at', '-component_id')[:5]
        )
    except (OperationalError, DatabaseError, Exception):
        components_count = 0
        categories_count = 0
        locations_count = 0
        suppliers_count = 0
        projects_count = 0
        popular_categories = []
        recent_components = []
        request.db_healthy = False
        request.user = AnonymousUser()

    context = {
        'components_count': components_count,
        'categories_count': categories_count,
        'locations_count': locations_count,
        'suppliers_count': suppliers_count,
        'projects_count': projects_count,
        'popular_categories': popular_categories,
        'recent_components': recent_components,
        'db_healthy': getattr(request, 'db_healthy', True),
    }

    try:
        return render(request, 'home.html', context)
    except (OperationalError, DatabaseError):
        request.user = AnonymousUser()
        context['db_healthy'] = False
        return render(request, 'home.html', context)
