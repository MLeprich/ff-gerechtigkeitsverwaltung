from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Settings, AuditLog


@admin.register(Settings)
class SettingsAdmin(admin.ModelAdmin):
    list_display = ['name', 'short_name', 'city', 'created_at']
    search_fields = ['name', 'short_name', 'city']

    def has_add_permission(self, request):
        # Nur eine Settings-Instanz erlaubt (Singleton)
        return not Settings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'role', 'is_active']
    list_filter = ['role', 'is_active', 'is_staff']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering = ['username']

    fieldsets = BaseUserAdmin.fieldsets + (
        ('Feuerwehr', {'fields': ('role', 'phone')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Feuerwehr', {'fields': ('role', 'phone')}),
    )


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'user', 'action', 'model_name', 'object_repr']
    list_filter = ['action', 'model_name']
    search_fields = ['object_repr', 'user__username']
    readonly_fields = ['user', 'action', 'model_name', 'object_id',
                       'object_repr', 'changes', 'timestamp', 'ip_address']
    ordering = ['-timestamp']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
