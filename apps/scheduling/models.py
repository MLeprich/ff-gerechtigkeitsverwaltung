from django.db import models
from django.utils import timezone


class DutyType(models.Model):
    """Diensttyp (z.B. Dienstabend, Übung, Sonderdienst)"""
    name = models.CharField('Bezeichnung', max_length=100, unique=True)
    color = models.CharField(
        'Farbe',
        max_length=7,
        default='#3B82F6',
        help_text='Hex-Farbcode für Kalenderansicht'
    )
    is_active = models.BooleanField('Aktiv', default=True)

    class Meta:
        verbose_name = 'Diensttyp'
        verbose_name_plural = 'Diensttypen'

    def __str__(self):
        return self.name


class Duty(models.Model):
    """Dienst/Übung/Termin"""

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Entwurf'
        PLANNED = 'planned', 'Geplant'
        CONFIRMED = 'confirmed', 'Bestätigt'
        COMPLETED = 'completed', 'Abgeschlossen'
        CANCELLED = 'cancelled', 'Abgesagt'

    duty_type = models.ForeignKey(
        DutyType,
        on_delete=models.SET_NULL,
        null=True,
        related_name='duties',
        verbose_name='Diensttyp'
    )
    title = models.CharField('Titel', max_length=200)
    description = models.TextField('Beschreibung', blank=True)
    date = models.DateField('Datum')
    start_time = models.TimeField('Beginn', null=True, blank=True)
    end_time = models.TimeField('Ende', null=True, blank=True)
    location = models.CharField('Ort', max_length=200, blank=True)

    # Fahrzeuge die für diesen Dienst benötigt werden
    vehicles = models.ManyToManyField(
        'vehicles.Vehicle',
        blank=True,
        related_name='duties',
        verbose_name='Fahrzeuge'
    )

    status = models.CharField(
        'Status',
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )

    # Mindestanforderungen
    min_agt_count = models.PositiveIntegerField(
        'Mindestanzahl AGT',
        default=0,
        help_text='Mindestens so viele Personen mit gültigem AGT-Status'
    )

    notes = models.TextField('Bemerkungen', blank=True)
    created_by = models.ForeignKey(
        'core.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_duties',
        verbose_name='Erstellt von'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Dienst'
        verbose_name_plural = 'Dienste'
        ordering = ['-date', '-start_time']

    def __str__(self):
        return f"{self.title} ({self.date})"

    @property
    def is_past(self):
        return self.date < timezone.now().date()

    @property
    def is_today(self):
        return self.date == timezone.now().date()


class Assignment(models.Model):
    """Einteilung einer Person auf eine Position für einen Dienst"""

    class Status(models.TextChoices):
        SUGGESTED = 'suggested', 'Vorgeschlagen'
        CONFIRMED = 'confirmed', 'Bestätigt'
        LOCKED = 'locked', 'Gesperrt'
        CANCELLED = 'cancelled', 'Ausgefallen'

    duty = models.ForeignKey(
        Duty,
        on_delete=models.CASCADE,
        related_name='assignments',
        verbose_name='Dienst'
    )
    vehicle = models.ForeignKey(
        'vehicles.Vehicle',
        on_delete=models.CASCADE,
        related_name='assignments',
        verbose_name='Fahrzeug'
    )
    vehicle_position = models.ForeignKey(
        'vehicles.VehiclePosition',
        on_delete=models.CASCADE,
        related_name='assignments',
        verbose_name='Position'
    )
    member = models.ForeignKey(
        'members.Member',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='assignments',
        verbose_name='Mitglied'
    )
    status = models.CharField(
        'Status',
        max_length=20,
        choices=Status.choices,
        default=Status.SUGGESTED
    )

    # Qualifikations-Override
    qualification_override = models.BooleanField(
        'Qualifikation übersteuert',
        default=False
    )
    override_reason = models.TextField(
        'Begründung für Übersteuerung',
        blank=True
    )
    overridden_by = models.ForeignKey(
        'core.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='qualification_overrides',
        verbose_name='Übersteuert von'
    )
    overridden_at = models.DateTimeField(
        'Übersteuert am',
        null=True,
        blank=True
    )

    # Warnungen
    has_warning = models.BooleanField('Hat Warnung', default=False)
    warning_text = models.TextField('Warnungstext', blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Einteilung'
        verbose_name_plural = 'Einteilungen'
        ordering = ['duty', 'vehicle', 'vehicle_position__seat_number']
        unique_together = ['duty', 'vehicle_position']

    def __str__(self):
        member_name = self.member.full_name if self.member else 'Unbesetzt'
        return f"{self.duty} - {self.vehicle_position}: {member_name}"


class AssignmentHistory(models.Model):
    """Historie aller Einteilungen für Fairness-Auswertungen"""
    member = models.ForeignKey(
        'members.Member',
        on_delete=models.CASCADE,
        related_name='assignment_history',
        verbose_name='Mitglied'
    )
    duty = models.ForeignKey(
        Duty,
        on_delete=models.SET_NULL,
        null=True,
        related_name='history_entries',
        verbose_name='Dienst'
    )
    vehicle = models.ForeignKey(
        'vehicles.Vehicle',
        on_delete=models.SET_NULL,
        null=True,
        related_name='assignment_history',
        verbose_name='Fahrzeug'
    )
    position = models.ForeignKey(
        'vehicles.Position',
        on_delete=models.SET_NULL,
        null=True,
        related_name='assignment_history',
        verbose_name='Position'
    )
    duty_type = models.ForeignKey(
        DutyType,
        on_delete=models.SET_NULL,
        null=True,
        related_name='assignment_history',
        verbose_name='Diensttyp'
    )
    date = models.DateField('Datum')
    year = models.PositiveIntegerField('Jahr')
    month = models.PositiveIntegerField('Monat')
    qualification_valid = models.BooleanField(
        'Qualifikation erfüllt',
        default=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Einteilungs-Historie'
        verbose_name_plural = 'Einteilungs-Historien'
        ordering = ['-date']
        indexes = [
            models.Index(fields=['member', 'year']),
            models.Index(fields=['vehicle', 'year']),
            models.Index(fields=['position', 'year']),
        ]

    def save(self, *args, **kwargs):
        if self.date:
            self.year = self.date.year
            self.month = self.date.month
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.member} - {self.position} ({self.date})"


class FairnessScore(models.Model):
    """Fairness-Score für ein Mitglied (aggregierte Statistik)"""
    member = models.ForeignKey(
        'members.Member',
        on_delete=models.CASCADE,
        related_name='fairness_scores',
        verbose_name='Mitglied'
    )
    year = models.PositiveIntegerField('Jahr')

    # Aggregierte Werte
    total_duties = models.PositiveIntegerField('Gesamtdienste', default=0)
    total_by_vehicle = models.JSONField(
        'Dienste pro Fahrzeug',
        default=dict,
        help_text='{"HLF": 5, "LF": 3, "MZF": 2}'
    )
    total_by_position = models.JSONField(
        'Dienste pro Position',
        default=dict,
        help_text='{"GF": 2, "MA": 3, "ATF": 5}'
    )
    last_duty_date = models.DateField(
        'Letzter Dienst',
        null=True,
        blank=True
    )
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Fairness-Score'
        verbose_name_plural = 'Fairness-Scores'
        unique_together = ['member', 'year']
        ordering = ['-year', 'member']

    def __str__(self):
        return f"{self.member} - {self.year}: {self.total_duties} Dienste"


class DutyAttendance(models.Model):
    """Tatsächliche Anwesenheit am Dienstabend"""
    duty = models.ForeignKey(
        Duty,
        on_delete=models.CASCADE,
        related_name='attendances',
        verbose_name='Dienst'
    )
    member = models.ForeignKey(
        'members.Member',
        on_delete=models.CASCADE,
        related_name='duty_attendances',
        verbose_name='Mitglied'
    )
    is_present = models.BooleanField('Anwesend', default=False)
    checked_in_at = models.DateTimeField(
        'Eingecheckt um',
        null=True,
        blank=True
    )
    checked_in_by = models.ForeignKey(
        'core.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='attendance_check_ins',
        verbose_name='Eingecheckt von'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Anwesenheit'
        verbose_name_plural = 'Anwesenheiten'
        unique_together = ['duty', 'member']
        ordering = ['member__last_name', 'member__first_name']

    def __str__(self):
        status = 'anwesend' if self.is_present else 'abwesend'
        return f"{self.member} - {self.duty}: {status}"
