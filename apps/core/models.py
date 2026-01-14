from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError


class Settings(models.Model):
    """Anwendungseinstellungen (Singleton) - Feuerwehr-Stammdaten"""
    name = models.CharField('Name', max_length=200)
    short_name = models.CharField('Kurzname', max_length=50)
    city = models.CharField('Ort', max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Einstellungen'
        verbose_name_plural = 'Einstellungen'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Singleton-Pattern: Nur eine Instanz erlaubt
        if not self.pk and Settings.objects.exists():
            raise ValidationError('Es kann nur eine Einstellungs-Instanz geben.')
        super().save(*args, **kwargs)

    @classmethod
    def get_instance(cls):
        """Singleton-Instanz abrufen oder erstellen"""
        instance = cls.objects.first()
        if not instance:
            instance = cls.objects.create(
                name='Freiwillige Feuerwehr',
                short_name='FF'
            )
        return instance


class User(AbstractUser):
    """Erweitertes Benutzermodell mit Rollen"""

    class Role(models.TextChoices):
        ADMIN = 'admin', 'Administrator'
        COMMANDER = 'commander', 'Zugführer'
        LEADER = 'leader', 'Gruppenführer'
        MEMBER = 'member', 'Mitglied'

    role = models.CharField(
        'Rolle',
        max_length=20,
        choices=Role.choices,
        default=Role.MEMBER
    )
    phone = models.CharField('Telefon', max_length=50, blank=True)

    class Meta:
        verbose_name = 'Benutzer'
        verbose_name_plural = 'Benutzer'

    def __str__(self):
        return f"{self.get_full_name() or self.username}"

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN or self.is_superuser

    @property
    def is_commander(self):
        return self.role in [self.Role.ADMIN, self.Role.COMMANDER] or self.is_superuser

    @property
    def is_leader(self):
        return self.role in [self.Role.ADMIN, self.Role.COMMANDER, self.Role.LEADER] or self.is_superuser


class AuditLog(models.Model):
    """Protokollierung aller wichtigen Änderungen"""

    class Action(models.TextChoices):
        CREATE = 'create', 'Erstellt'
        UPDATE = 'update', 'Geändert'
        DELETE = 'delete', 'Gelöscht'
        OVERRIDE = 'override', 'Übersteuert'

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='audit_logs',
        verbose_name='Benutzer'
    )
    action = models.CharField('Aktion', max_length=20, choices=Action.choices)
    model_name = models.CharField('Modell', max_length=100)
    object_id = models.PositiveIntegerField('Objekt-ID', null=True, blank=True)
    object_repr = models.CharField('Objektbeschreibung', max_length=255)
    changes = models.JSONField('Änderungen', default=dict, blank=True)
    timestamp = models.DateTimeField('Zeitpunkt', auto_now_add=True)
    ip_address = models.GenericIPAddressField('IP-Adresse', null=True, blank=True)

    class Meta:
        verbose_name = 'Protokolleintrag'
        verbose_name_plural = 'Protokoll'
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.get_action_display()}: {self.object_repr} von {self.user}"
