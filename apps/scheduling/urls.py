from django.urls import path
from . import views

urlpatterns = [
    # Dienste
    path('', views.duty_list, name='duty_list'),
    path('new/', views.duty_edit, name='duty_create'),
    path('<int:duty_id>/', views.duty_detail, name='duty_detail'),
    path('<int:duty_id>/edit/', views.duty_edit, name='duty_edit'),
    path('<int:duty_id>/delete/', views.duty_delete, name='duty_delete'),

    # Anwesenheit & Besetzung
    path('<int:duty_id>/attendance/<int:member_id>/toggle/', views.attendance_toggle, name='attendance_toggle'),
    path('<int:duty_id>/assignment/<int:position_id>/update/', views.update_assignment, name='update_assignment'),
    path('<int:duty_id>/generate/', views.generate_assignments, name='generate_assignments'),

    # Statistiken
    path('statistics/', views.statistics, name='scheduling_statistics'),

    # Diensttypen
    path('types/', views.duty_type_list, name='duty_type_list'),
    path('types/new/', views.duty_type_edit, name='duty_type_create'),
    path('types/<int:type_id>/edit/', views.duty_type_edit, name='duty_type_edit'),
    path('types/<int:type_id>/delete/', views.duty_type_delete, name='duty_type_delete'),
]
