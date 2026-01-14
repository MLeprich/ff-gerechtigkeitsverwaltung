from django.urls import path
from . import views

urlpatterns = [
    path('', views.member_list, name='member_list'),
    path('new/', views.member_edit, name='member_create'),
    path('import/', views.member_import_csv, name='member_import_csv'),
    path('export/', views.member_export_csv, name='member_export_csv'),
    path('template/', views.member_export_csv_template, name='member_csv_template'),
    path('<int:member_id>/', views.member_detail, name='member_detail'),
    path('<int:member_id>/edit/', views.member_edit, name='member_edit'),
    path('<int:member_id>/delete/', views.member_delete, name='member_delete'),

    # Qualifikationen
    path('<int:member_id>/qualification/add/', views.member_qualification_add, name='member_qualification_add'),
    path('<int:member_id>/qualification/<int:qualification_id>/remove/', views.member_qualification_remove, name='member_qualification_remove'),

    # Medizinische Untersuchungen
    path('<int:member_id>/exam/add/', views.member_exam_add, name='member_exam_add'),
    path('<int:member_id>/exam/<int:exam_id>/delete/', views.member_exam_delete, name='member_exam_delete'),

    # AGT-Übungen
    path('<int:member_id>/exercise/add/', views.member_exercise_add, name='member_exercise_add'),
    path('<int:member_id>/exercise/<int:exercise_id>/delete/', views.member_exercise_delete, name='member_exercise_delete'),
]
