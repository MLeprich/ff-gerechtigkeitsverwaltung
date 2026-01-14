from django.db import models
from django.utils import timezone
from datetime import date


class Unit(models.Model):
    """Einheit/Gruppe innerhalb einer Feuerwehr (z.B. Löschzug 1, Gruppe A)"""
    name = models.CharField('Name', max_length=100, unique=True)
    short_name = models.CharField('Kurzname', max_length=20, blank=True)
    order = models.PositiveIntegerField('Reihenfolge', default=0)
    is_active = models.BooleanField('Aktiv', default=True)

    class Meta:
        verbose_name = 'Einheit'
        verbose_name_plural = 'Einheiten'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class Member(models.Model):
    """Mitglied der Feuerwehr (Kamerad:in)"""

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Aktiv'
        INACTIVE = 'inactive', 'Inaktiv'
        YOUTH = 'youth', 'Jugendfeuerwehr'
        HONORARY = 'honorary', 'Alters- und Ehrenabteilung'
        RESERVE = 'reserve', 'Reserve'

    user = models.OneToOneField(
        'core.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='member_profile',
        verbose_name='Benutzerkonto'
    )
    unit = models.ForeignKey(
        Unit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='members',
        verbose_name='Einheit'
    )

    # Persönliche Daten
    first_name = models.CharField('Vorname', max_length=100)
    last_name = models.CharField('Nachname', max_length=100)
    birth_date = models.DateField('Geburtsdatum', null=True, blank=True)
    email = models.EmailField('E-Mail', blank=True)
    phone = models.CharField('Telefon', max_length=50, blank=True)
    mobile = models.CharField('Mobil', max_length=50, blank=True)

    # Feuerwehr-spezifisch
    member_number = models.CharField('Mitgliedsnummer', max_length=50, blank=True)
    entry_date = models.DateField('Eintrittsdatum', null=True, blank=True)
    status = models.CharField(
        'Status',
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )

    # Präferenzen
    preferred_positions = models.TextField(
        'Wunschpositionen',
        blank=True,
        help_text='Kommaseparierte Liste bevorzugter Positionen'
    )
    notes = models.TextField('Bemerkungen', blank=True)

    # Metadaten
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField('Aktiv', default=True)

    class Meta:
        verbose_name = 'Mitglied'
        verbose_name_plural = 'Mitglieder'
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.last_name}, {self.first_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def is_available(self):
        """Prüft ob Mitglied grundsätzlich einsetzbar ist"""
        return self.is_active and self.status == self.Status.ACTIVE

    def has_qualification(self, qualification_code):
        """Prüft ob Mitglied eine Qualifikation besitzt"""
        return self.qualifications.filter(
            qualification__code=qualification_code
        ).exists()

    def has_valid_agt_status(self):
        """Prüft ob AGT-Status gültig ist (G26.3 + Übungen)"""
        from apps.qualifications.models import MedicalExam, ExerciseRecord

        # Prüfe G26.3
        g26_valid = MedicalExam.objects.filter(
            member=self,
            exam_type__code='G26.3',
            valid_until__gte=timezone.now().date(),
            result_positive=True
        ).exists()

        if not g26_valid:
            return False

        # Prüfe Übungen im letzten Jahr
        one_year_ago = date.today().replace(year=date.today().year - 1)
        exercise_count = ExerciseRecord.objects.filter(
            member=self,
            qualification__code='AGT',
            exercise_date__gte=one_year_ago
        ).count()

        return exercise_count >= 1  # Mindestens eine Belastungsübung


class Availability(models.Model):
    """Verfügbarkeitsmeldung eines Mitglieds für einen Termin"""

    class Status(models.TextChoices):
        AVAILABLE = 'available', 'Verfügbar'
        UNAVAILABLE = 'unavailable', 'Nicht verfügbar'
        MAYBE = 'maybe', 'Vielleicht'
        PENDING = 'pending', 'Offen'

    member = models.ForeignKey(
        Member,
        on_delete=models.CASCADE,
        related_name='availabilities',
        verbose_name='Mitglied'
    )
    duty = models.ForeignKey(
        'scheduling.Duty',
        on_delete=models.CASCADE,
        related_name='availabilities',
        verbose_name='Dienst'
    )
    status = models.CharField(
        'Status',
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    notes = models.TextField('Bemerkungen', blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Verfügbarkeit'
        verbose_name_plural = 'Verfügbarkeiten'
        unique_together = ['member', 'duty']

    def __str__(self):
        return f"{self.member} - {self.duty}: {self.get_status_display()}"
