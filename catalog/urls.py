from django.urls import path
from . import views

app_name = 'catalog'

urlpatterns = [
    path('', views.ComponentListView.as_view(), name='list'),
    path('create/', views.ComponentCreateView.as_view(), name='create'),
    path('<int:pk>/', views.ComponentDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.ComponentUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.ComponentDeleteView.as_view(), name='delete'),
    path('<int:pk>/pinout/', views.pinout_view, name='pinout_view'),
    path('<int:pk>/pinout/builder/', views.pinout_builder, name='pinout_builder'),
    path('<int:pk>/pinout/save-api/', views.pinout_save_api, name='pinout_save_api'),
]
