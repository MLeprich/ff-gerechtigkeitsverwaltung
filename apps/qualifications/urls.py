from django.urls import path
from . import views

urlpatterns = [
    # Qualifikationen
    path('', views.qualification_list, name='qualification_list'),
    path('new/', views.qualification_edit, name='qualification_create'),
    path('<int:qualification_id>/edit/', views.qualification_edit, name='qualification_edit'),
    path('<int:qualification_id>/delete/', views.qualification_delete, name='qualification_delete'),

    # Kategorien
    path('categories/', views.category_list, name='category_list'),
    path('categories/new/', views.category_edit, name='category_create'),
    path('categories/<int:category_id>/edit/', views.category_edit, name='category_edit'),

    # Untersuchungstypen
    path('exam-types/', views.exam_type_list, name='exam_type_list'),
    path('exam-types/new/', views.exam_type_edit, name='exam_type_create'),
    path('exam-types/<int:exam_type_id>/edit/', views.exam_type_edit, name='exam_type_edit'),
]
