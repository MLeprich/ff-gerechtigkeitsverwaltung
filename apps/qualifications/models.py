from django.db import models
from django.utils import timezone
from dateutil.relativedelta import relativedelta


class QualificationCategory(models.Model):
    """Kategorie von Qualifikationen (z.B. Grundausbildung, Führung, Sonstiges)"""
    name = models.CharField('Name', max_length=100, unique=True)
    order = models.PositiveIntegerField('Reihenfolge', default=0)

    class Meta:
        verbose_name = 'Qualifikationskategorie'
        verbose_name_plural = 'Qualifikationskategorien'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class Qualification(models.Model):
    """Qualifikation/Lehrgang (z.B. TM1, TF, GF, AGT, MA)"""
    category = models.ForeignKey(
        QualificationCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='qualifications',
        verbose_name='Kategorie'
    )
    code = models.CharField('Kürzel', max_length=20, unique=True)
    name = models.CharField('Bezeichnung', max_length=100)
    description = models.TextField('Beschreibung', blank=True)

    # Hierarchie: Höhere Qualifikationen decken niedrigere ab
    covers = models.ManyToManyField(
        'self',
        symmetrical=False,
        blank=True,
        related_name='covered_by',
        verbose_name='Deckt ab'
    )

    # Für Qualifikationen die ablaufen (z.B. G26.3)
    requires_renewal = models.BooleanField('Erfordert Erneuerung', default=False)
    renewal_months = models.PositiveIntegerField(
        'Gültigkeitsdauer (Monate)',
        null=True,
        blank=True,
        help_text='Für zeitlich begrenzte Qualifikationen wie G26.3'
    )

    # Für Qualifikationen die Übungen erfordern (z.B. AGT)
    requires_exercises = models.BooleanField('Erfordert Übungen', default=False)
    exercise_count = models.PositiveIntegerField(
        'Anzahl Übungen pro Jahr',
        null=True,
        blank=True
    )

    order = models.PositiveIntegerField('Reihenfolge', default=0)
    is_active = models.BooleanField('Aktiv', default=True)

    class Meta:
        verbose_name = 'Qualifikation'
        verbose_name_plural = 'Qualifikationen'
        ordering = ['order', 'code']

    def __str__(self):
        return f"{self.code} - {self.name}"


class MedicalExamType(models.Model):
    """Typ einer ärztlichen Untersuchung (z.B. G26.3, G25)"""
    code = models.CharField('Kürzel', max_length=20, unique=True)
    name = models.CharField('Bezeichnung', max_length=100)
    validity_months = models.PositiveIntegerField(
        'Gültigkeitsdauer (Monate)',
        default=36,
        help_text='z.B. 36 Monate für G26.3'
    )
    related_qualification = models.ForeignKey(
        Qualification,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='required_exams',
        verbose_name='Benötigt für Qualifikation'
    )

    class Meta:
        verbose_name = 'Untersuchungstyp'
        verbose_name_plural = 'Untersuchungstypen'

    def __str__(self):
        return f"{self.code} - {self.name}"


class MemberQualification(models.Model):
    """Zuordnung einer Qualifikation zu einem Mitglied"""
    member = models.ForeignKey(
        'members.Member',
        on_delete=models.CASCADE,
        related_name='qualifications',
        verbose_name='Mitglied'
    )
    qualification = models.ForeignKey(
        Qualification,
        on_delete=models.CASCADE,
        related_name='member_qualifications',
        verbose_name='Qualifikation'
    )
    acquired_date = models.DateField('Erworben am', null=True, blank=True)
    notes = models.TextField('Bemerkungen', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Mitglieder-Qualifikation'
        verbose_name_plural = 'Mitglieder-Qualifikationen'
        unique_together = ['member', 'qualification']

    def __str__(self):
        return f"{self.member} - {self.qualification.code}"


class MedicalExam(models.Model):
    """Ärztliche Untersuchung eines Mitglieds"""
    member = models.ForeignKey(
        'members.Member',
        on_delete=models.CASCADE,
        related_name='medical_exams',
        verbose_name='Mitglied'
    )
    exam_type = models.ForeignKey(
        MedicalExamType,
        on_delete=models.CASCADE,
        related_name='exams',
        verbose_name='Untersuchungstyp'
    )
    exam_date = models.DateField('Untersuchungsdatum')
    valid_until = models.DateField('Gültig bis', blank=True, null=True)
    result_positive = models.BooleanField('Bestanden', default=True)
    notes = models.TextField('Bemerkungen', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Ärztliche Untersuchung'
        verbose_name_plural = 'Ärztliche Untersuchungen'
        ordering = ['-exam_date']

    def save(self, *args, **kwargs):
        if not self.valid_until and self.exam_type:
            self.valid_until = self.exam_date + relativedelta(
                months=self.exam_type.validity_months
            )
        super().save(*args, **kwargs)

    @property
    def is_valid(self):
        return self.result_positive and self.valid_until >= timezone.now().date()

    def __str__(self):
        return f"{self.member} - {self.exam_type.code} ({self.exam_date})"


class ExerciseRecord(models.Model):
    """Nachweis einer Übung (z.B. Atemschutzübung)"""
    member = models.ForeignKey(
        'members.Member',
        on_delete=models.CASCADE,
        related_name='exercise_records',
        verbose_name='Mitglied'
    )
    qualification = models.ForeignKey(
        Qualification,
        on_delete=models.CASCADE,
        related_name='exercise_records',
        verbose_name='Für Qualifikation'
    )
    exercise_date = models.DateField('Übungsdatum')
    exercise_type = models.CharField('Übungsart', max_length=100)
    notes = models.TextField('Bemerkungen', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Übungsnachweis'
        verbose_name_plural = 'Übungsnachweise'
        ordering = ['-exercise_date']

    def __str__(self):
        return f"{self.member} - {self.exercise_type} ({self.exercise_date})"
