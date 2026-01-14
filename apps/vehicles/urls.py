from django.urls import path
from . import views

urlpatterns = [
    # Fahrzeuge
    path('', views.vehicle_list, name='vehicle_list'),
    path('new/', views.vehicle_edit, name='vehicle_create'),
    path('<int:vehicle_id>/', views.vehicle_detail, name='vehicle_detail'),
    path('<int:vehicle_id>/edit/', views.vehicle_edit, name='vehicle_edit'),
    path('<int:vehicle_id>/delete/', views.vehicle_delete, name='vehicle_delete'),

    # Fahrzeugtypen
    path('types/', views.vehicle_type_list, name='vehicle_type_list'),
    path('types/new/', views.vehicle_type_edit, name='vehicle_type_create'),
    path('types/<int:type_id>/edit/', views.vehicle_type_edit, name='vehicle_type_edit'),
    path('types/<int:type_id>/delete/', views.vehicle_type_delete, name='vehicle_type_delete'),

    # Positionen
    path('positions/', views.position_list, name='position_list'),
    path('positions/new/', views.position_edit, name='position_create'),
    path('positions/<int:position_id>/edit/', views.position_edit, name='position_edit'),
]
