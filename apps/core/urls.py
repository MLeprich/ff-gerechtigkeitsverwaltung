from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('setup/', views.setup_wizard, name='setup_wizard'),

    # Verwaltung (Admin-Bereich)
    path('verwaltung/', views.admin_settings, name='admin_settings'),
    path('verwaltung/benutzer/', views.admin_users, name='admin_users'),
    path('verwaltung/benutzer/neu/', views.admin_user_edit, name='admin_user_new'),
    path('verwaltung/benutzer/<int:user_id>/', views.admin_user_edit, name='admin_user_edit'),
]
