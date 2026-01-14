from django.db import models


class VehicleType(models.Model):
    """Fahrzeugtyp (z.B. HLF 20, LF KatS, MZF)"""
    name = models.CharField('Bezeichnung', max_length=100)
    short_name = models.CharField('Kurzname', max_length=20, unique=True)
    crew_size = models.CharField(
        'Besatzungsstärke',
        max_length=20,
        help_text='z.B. 1/8, 1/5, 1/2'
    )
    description = models.TextField('Beschreibung', blank=True)
    order = models.PositiveIntegerField('Reihenfolge/Priorität', default=0)

    class Meta:
        verbose_name = 'Fahrzeugtyp'
        verbose_name_plural = 'Fahrzeugtypen'
        ordering = ['order', 'name']

    def __str__(self):
        return f"{self.short_name} ({self.crew_size})"


class Vehicle(models.Model):
    """Konkretes Fahrzeug"""
    vehicle_type = models.ForeignKey(
        VehicleType,
        on_delete=models.CASCADE,
        related_name='vehicles',
        verbose_name='Fahrzeugtyp'
    )
    call_sign = models.CharField(
        'Funkrufname',
        max_length=50,
        unique=True,
        help_text='z.B. 05-HLF20-01'
    )
    name = models.CharField('Bezeichnung', max_length=100, blank=True)
    license_plate = models.CharField('Kennzeichen', max_length=20, blank=True)
    priority = models.PositiveIntegerField(
        'Besetzungspriorität',
        default=0,
        help_text='Niedrigere Werte = höhere Priorität bei der Besetzung'
    )
    has_optional_messenger = models.BooleanField(
        'Hat optionalen Melderplatz',
        default=False,
        help_text='Für historische Daten oder spätere Erweiterung'
    )
    is_active = models.BooleanField('Aktiv', default=True)
    notes = models.TextField('Bemerkungen', blank=True)

    class Meta:
        verbose_name = 'Fahrzeug'
        verbose_name_plural = 'Fahrzeuge'
        ordering = ['priority', 'call_sign']

    def __str__(self):
        return self.call_sign


class Position(models.Model):
    """Position/Sitzplatz auf einem Fahrzeug (z.B. Fahrzeugführer, Maschinist, ATF)"""
    name = models.CharField('Bezeichnung', max_length=100)
    short_name = models.CharField('Kurzname', max_length=20, unique=True)
    description = models.TextField('Beschreibung', blank=True)
    order = models.PositiveIntegerField('Reihenfolge', default=0)

    class Meta:
        verbose_name = 'Position'
        verbose_name_plural = 'Positionen'
        ordering = ['order', 'name']

    def __str__(self):
        return f"{self.short_name} - {self.name}"


class VehiclePosition(models.Model):
    """Zuordnung einer Position zu einem Fahrzeug mit Qualifikationsanforderungen"""
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name='positions',
        verbose_name='Fahrzeug'
    )
    position = models.ForeignKey(
        Position,
        on_delete=models.CASCADE,
        related_name='vehicle_positions',
        verbose_name='Position'
    )
    seat_number = models.PositiveIntegerField(
        'Sitzplatznummer',
        default=1,
        help_text='Für die Reihenfolge auf dem Fahrzeug'
    )
    is_required = models.BooleanField(
        'Pflichtposition',
        default=True,
        help_text='Muss diese Position besetzt sein?'
    )
    is_optional = models.BooleanField(
        'Optional',
        default=False,
        help_text='z.B. Melderplatz'
    )

    # Qualifikationsanforderungen
    required_qualifications = models.ManyToManyField(
        'qualifications.Qualification',
        blank=True,
        related_name='required_for_positions',
        verbose_name='Pflichtqualifikationen'
    )
    preferred_qualifications = models.ManyToManyField(
        'qualifications.Qualification',
        blank=True,
        related_name='preferred_for_positions',
        verbose_name='Bevorzugte Qualifikationen'
    )
    requires_agt = models.BooleanField(
        'Erfordert AGT-Status',
        default=False,
        help_text='Muss gültigen Atemschutz-Status haben'
    )

    class Meta:
        verbose_name = 'Fahrzeug-Position'
        verbose_name_plural = 'Fahrzeug-Positionen'
        ordering = ['vehicle', 'seat_number']
        unique_together = ['vehicle', 'position']

    def __str__(self):
        return f"{self.vehicle.call_sign} - {self.position.short_name}"


class PositionRule(models.Model):
    """Regel für eine Position (alternative Qualifikationsanforderungen)"""

    class RuleType(models.TextChoices):
        REQUIRED = 'required', 'Erforderlich'
        PREFERRED = 'preferred', 'Bevorzugt'
        ALLOWED = 'allowed', 'Erlaubt (mit Warnung)'

    vehicle_position = models.ForeignKey(
        VehiclePosition,
        on_delete=models.CASCADE,
        related_name='rules',
        verbose_name='Fahrzeug-Position'
    )
    rule_type = models.CharField(
        'Regeltyp',
        max_length=20,
        choices=RuleType.choices,
        default=RuleType.REQUIRED
    )
    description = models.CharField('Beschreibung', max_length=255)
    qualifications = models.ManyToManyField(
        'qualifications.Qualification',
        related_name='position_rules',
        verbose_name='Qualifikationen'
    )
    all_required = models.BooleanField(
        'Alle erforderlich',
        default=False,
        help_text='Alle Qualifikationen müssen vorhanden sein (UND) vs. eine davon (ODER)'
    )
    warning_text = models.CharField(
        'Warnungstext',
        max_length=255,
        blank=True,
        help_text='Wird angezeigt wenn Regel verletzt wird'
    )
    priority = models.PositiveIntegerField('Priorität', default=0)

    class Meta:
        verbose_name = 'Positionsregel'
        verbose_name_plural = 'Positionsregeln'
        ordering = ['priority']

    def __str__(self):
        return f"{self.vehicle_position}: {self.description}"
