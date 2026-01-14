"""
Generator für automatische Fahrzeugbesetzung.

Algorithmus:
1. Lade alle anwesenden Mitglieder für den Dienst
2. Lade alle Fahrzeuge des Dienstes (sortiert nach Priorität)
3. Für jedes Fahrzeug (HLF zuerst):
   a. Für jede Position (sortiert nach Sitznummer):
      - Finde qualifizierte Kandidaten unter den noch nicht zugewiesenen Anwesenden
      - Sortiere nach Fairness-Score (weniger Einsätze = höhere Priorität)
      - Weise den besten Kandidaten zu
      - Falls kein qualifizierter Kandidat: Warnung setzen
"""

import random
from datetime import date
from django.db.models import Count, Q


# Qualifikationshierarchie: Höhere Qualifikationen erfüllen niedrigere
QUALIFICATION_HIERARCHY = {
    'TM1': ['TM2', 'TM', 'TF', 'GF', 'ZF', 'VF'],
    'TM2': ['TM', 'TF', 'GF', 'ZF', 'VF'],
    'TM': ['TF', 'GF', 'ZF', 'VF'],
    'TF': ['GF', 'ZF', 'VF'],
    'GF': ['ZF', 'VF'],
    'ZF': ['VF'],
    'VF': [],
    # Spezielle Qualifikationen (keine Hierarchie)
    'MA': [],
    'AGT': [],
    'MZF-FA': [],
    'ABC1': ['ABC2'],
    'ABC2': [],
    'MKS': [],
}


def has_qualification_or_higher(member, qual_code):
    """
    Prüft ob ein Mitglied eine Qualifikation oder eine höhere hat.

    Args:
        member: Member-Objekt
        qual_code: Qualifikationscode (z.B. 'TM', 'TF', 'GF')

    Returns:
        bool: True wenn qualifiziert
    """
    # Hat das Mitglied genau diese Qualifikation?
    if member.has_qualification(qual_code):
        return True

    # Hat das Mitglied eine höhere Qualifikation?
    higher_quals = QUALIFICATION_HIERARCHY.get(qual_code, [])
    for higher_code in higher_quals:
        if member.has_qualification(higher_code):
            return True

    return False


def check_member_qualification(member, vehicle_position):
    """
    Prüft ob ein Mitglied alle Anforderungen für eine Position erfüllt.

    Args:
        member: Member-Objekt
        vehicle_position: VehiclePosition-Objekt

    Returns:
        tuple: (is_qualified: bool, warning_text: str or None)
    """
    warnings = []

    # Required Qualifications prüfen
    for qual in vehicle_position.required_qualifications.all():
        if not has_qualification_or_higher(member, qual.code):
            warnings.append(f'Fehlende Qualifikation: {qual.code}')

    # AGT-Status prüfen wenn erforderlich
    if vehicle_position.requires_agt:
        if not member.has_valid_agt_status():
            warnings.append('AGT-Status nicht gültig (G26.3 oder Übungen fehlen)')

    if warnings:
        return False, '; '.join(warnings)

    return True, None


def get_fairness_score(member, position_code, year=None):
    """
    Berechnet wie oft ein Mitglied diese Position besetzt hat.

    Args:
        member: Member-Objekt
        position_code: Positionscode (z.B. 'GF', 'MA')
        year: Jahr für Statistik (default: aktuelles Jahr)

    Returns:
        int: Anzahl der Einsätze auf dieser Position
    """
    if year is None:
        year = date.today().year

    from .models import AssignmentHistory

    return AssignmentHistory.objects.filter(
        member=member,
        position__short_name=position_code,
        year=year
    ).count()


class AssignmentGenerator:
    """Generator für automatische Fahrzeugbesetzung"""

    def __init__(self, duty, selected_vehicle_ids=None):
        self.duty = duty
        self.selected_vehicle_ids = selected_vehicle_ids  # Optional: nur diese Fahrzeuge besetzen
        self.assigned_members = set()  # IDs bereits zugewiesener Mitglieder
        self.results = []
        self.warnings_count = 0

    def get_present_members(self):
        """Lade alle anwesenden Mitglieder für diesen Dienst"""
        from .models import DutyAttendance

        attendance_ids = DutyAttendance.objects.filter(
            duty=self.duty,
            is_present=True
        ).values_list('member_id', flat=True)

        from apps.members.models import Member

        return Member.objects.filter(
            id__in=attendance_ids,
            status='active',
            is_active=True
        ).prefetch_related('qualifications__qualification')

    def find_candidates(self, vehicle_position, present_members):
        """
        Finde qualifizierte Kandidaten für eine Position.

        Args:
            vehicle_position: VehiclePosition-Objekt
            present_members: QuerySet der anwesenden Mitglieder

        Returns:
            list: Sortierte Liste von (member, is_qualified, warning) Tupeln
        """
        candidates = []
        position_code = vehicle_position.position.short_name

        for member in present_members:
            # Bereits zugewiesen?
            if member.id in self.assigned_members:
                continue

            is_qualified, warning = check_member_qualification(member, vehicle_position)

            # Fairness-Score berechnen
            fairness_score = get_fairness_score(member, position_code)

            # Preferred Qualifications als Bonus
            preferred_bonus = 0
            for pref_qual in vehicle_position.preferred_qualifications.all():
                if has_qualification_or_higher(member, pref_qual.code):
                    preferred_bonus += 1

            candidates.append({
                'member': member,
                'is_qualified': is_qualified,
                'warning': warning,
                'fairness_score': fairness_score,
                'preferred_bonus': preferred_bonus,
            })

        # Sortieren:
        # 1. Qualifizierte zuerst
        # 2. Dann nach Fairness (weniger Einsätze = besser)
        # 3. Dann nach Preferred-Bonus (mehr = besser)
        # 4. Bei Gleichstand: Zufall
        random.shuffle(candidates)  # Zufällige Grundreihenfolge bei Gleichstand
        candidates.sort(key=lambda c: (
            not c['is_qualified'],  # False (qualifiziert) vor True (nicht qualifiziert)
            c['fairness_score'],    # Weniger ist besser
            -c['preferred_bonus'],  # Mehr ist besser (daher negativ)
        ))

        return candidates

    def generate(self):
        """
        Generiert die Besetzung für alle Fahrzeuge des Dienstes.

        Returns:
            dict: {
                'success': bool,
                'assigned_count': int,
                'warning_count': int,
                'error': str or None
            }
        """
        from .models import Assignment
        from apps.vehicles.models import VehiclePosition

        try:
            present_members = list(self.get_present_members())

            if not present_members:
                return {
                    'success': False,
                    'assigned_count': 0,
                    'warning_count': 0,
                    'error': 'Keine anwesenden Mitglieder markiert'
                }

            # Fahrzeuge nach Priorität sortieren
            vehicles = self.duty.vehicles.all().order_by('priority')

            # Nur ausgewählte Fahrzeuge verwenden, falls angegeben
            if self.selected_vehicle_ids:
                vehicles = vehicles.filter(id__in=self.selected_vehicle_ids)

            if not vehicles:
                return {
                    'success': False,
                    'assigned_count': 0,
                    'warning_count': 0,
                    'error': 'Keine Fahrzeuge für diesen Dienst ausgewählt'
                }

            assigned_count = 0

            for vehicle in vehicles:
                # Positionen für dieses Fahrzeug
                positions = VehiclePosition.objects.filter(
                    vehicle=vehicle
                ).select_related('position').prefetch_related(
                    'required_qualifications', 'preferred_qualifications'
                ).order_by('seat_number')

                for vehicle_position in positions:
                    # Kandidaten finden
                    candidates = self.find_candidates(vehicle_position, present_members)

                    if not candidates:
                        # Keine Kandidaten verfügbar
                        continue

                    # Besten Kandidaten auswählen
                    best = candidates[0]
                    member = best['member']

                    # Assignment erstellen/aktualisieren
                    assignment, created = Assignment.objects.update_or_create(
                        duty=self.duty,
                        vehicle_position=vehicle_position,
                        defaults={
                            'vehicle': vehicle,
                            'member': member,
                            'status': Assignment.Status.SUGGESTED,
                            'has_warning': not best['is_qualified'],
                            'warning_text': best['warning'] or '',
                        }
                    )

                    self.assigned_members.add(member.id)
                    assigned_count += 1

                    if not best['is_qualified']:
                        self.warnings_count += 1

            return {
                'success': True,
                'assigned_count': assigned_count,
                'warning_count': self.warnings_count,
                'error': None
            }

        except Exception as e:
            return {
                'success': False,
                'assigned_count': 0,
                'warning_count': 0,
                'error': str(e)
            }
