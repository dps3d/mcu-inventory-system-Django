"""
URL configuration for MCU Inventory System.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from .views import home

urlpatterns = [
    path('', home, name='home'),
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('catalog/', include('catalog.urls')),
    path('inventory/', include('inventory.urls')),
    path('projects/', include('projects.urls')),
]

if settings.DEBUG:
    from django.views.defaults import page_not_found
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += [
        path('404/', lambda request: page_not_found(request, Exception("Попередній перегляд 404 сторінки"))),
    ]
