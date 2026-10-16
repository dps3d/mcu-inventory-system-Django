from django.urls import path
from . import views

app_name = 'projects'

urlpatterns = [
    # Список та створення проєктів
    path('', views.project_list, name='list'),
    path('create/', views.project_create, name='create'),
    path('<int:pk>/', views.project_detail, name='detail'),
    path('<int:pk>/edit/', views.project_edit, name='edit'),
    path('<int:pk>/delete/', views.project_delete, name='delete'),
    path('<int:pk>/status/', views.project_status_update, name='status_update'),

    # Операції над BOM
    path('<int:pk>/bom/add/', views.bom_add_item, name='bom_add'),
    path('<int:pk>/bom/<int:bom_id>/edit/', views.bom_edit_item, name='bom_edit'),
    path('<int:pk>/bom/<int:bom_id>/delete/', views.bom_delete_item, name='bom_delete'),
    path('<int:pk>/bom/<int:bom_id>/reserve/', views.bom_reserve_item, name='bom_reserve'),
    path('<int:pk>/bom/<int:bom_id>/release/', views.bom_release_item, name='bom_release'),

    # Масові дії проєкту (резервування партії, списання у збірку, експорт)
    path('<int:pk>/reserve-all/', views.project_reserve_all, name='reserve_all'),
    path('<int:pk>/consume-all/', views.project_consume_all, name='consume_all'),
    path('<int:pk>/export/csv/', views.project_bom_export_csv, name='export_csv'),
]
