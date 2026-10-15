from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('locations/', views.dashboard, name='locations_list'),
    path('locations/<int:pk>/', views.location_detail, name='location_detail'),
    path('locations/create/', views.location_create, name='location_create'),
    path('locations/<int:pk>/edit/', views.location_edit, name='location_edit'),
    path('locations/<int:pk>/delete/', views.location_delete, name='location_delete'),
    path('locations/quick-add/', views.location_quick_add, name='location_quick_add'),
    path('rows/create/', views.row_create, name='row_create'),
    path('rows/delete/', views.row_delete, name='row_delete'),
    path('organizers/create/', views.organizer_create, name='organizer_create'),
    path('organizers/delete/', views.organizer_delete, name='organizer_delete'),
    path('operation/', views.quick_operation, name='quick_operation'),
    path('suppliers/', views.suppliers_list, name='suppliers_list'),
    path('suppliers/create/', views.supplier_create, name='supplier_create'),
]
