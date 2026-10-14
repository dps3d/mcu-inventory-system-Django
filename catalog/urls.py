from django.urls import path
from . import views

app_name = 'catalog'

urlpatterns = [
    path('', views.component_list, name='list'),
    path('create/', views.component_create, name='create'),
    path('<int:pk>/', views.component_detail, name='detail'),
    path('<int:pk>/edit/', views.component_edit, name='edit'),
    path('<int:pk>/delete/', views.component_delete, name='delete'),
    path('<int:pk>/pinout/', views.pinout_view, name='pinout_view'),
    path('<int:pk>/pinout/builder/', views.pinout_builder, name='pinout_builder'),
    path('<int:pk>/pinout/save-api/', views.pinout_save_api, name='pinout_save_api'),
]
