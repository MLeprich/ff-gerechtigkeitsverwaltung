"""
Management-Command zum Einrichten der Fahrzeuge, Positionen und Qualifikationsanforderungen.

Erstellt:
- Fahrzeugtypen (HLF, LF, MZF)
- Fahrzeuge (05-HLF20-01, 05-LF KatS-01, 05-MZF-01)
- Fahrzeugpositionen mit Qualifikationsanforderungen

Verwendung:
    python manage.py setup_vehicles
"""

from django.core.management.base import BaseCommand
from apps.vehicles.models import VehicleType, Vehicle, Position, VehiclePosition
from apps.qualifications.models import Qualification, QualificationCategory


class Command(BaseCommand):
    help = 'Richtet Fahrzeuge, Positionen und Qualifikationsanforderungen ein'

    def handle(self, *args, **options):
        self.stdout.write('Starte Fahrzeug-Setup...\n')

        # 1. MZF-FA Qualifikation anlegen
        self.setup_mzf_qualification()

        # 2. Fahrzeugtypen anlegen
        self.setup_vehicle_types()

        # 3. Fahrzeuge anlegen
        self.setup_vehicles()

        # 4. Positionen mit Qualifikationsanforderungen anlegen
        self.setup_vehicle_positions()

        self.stdout.write(self.style.SUCCESS('\nFahrzeug-Setup abgeschlossen!'))

    def setup_mzf_qualification(self):
        """MZF-Fahrabnahme Qualifikation anlegen"""
        self.stdout.write('Erstelle MZF-FA Qualifikation...')

        # Kategorie "Sonstige" finden oder erstellen
        category, _ = QualificationCategory.objects.get_or_create(
            name='Sonstige',
            defaults={'order': 100}
        )

        qual, created = Qualification.objects.get_or_create(
            code='MZF-FA',
            defaults={
                'name': 'MZF-Fahrabnahme',
                'description': 'Fahrabnahme für das Mehrzweckfahrzeug (MZF)',
                'category': category,
                'order': 50,
                'is_active': True
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'  Qualifikation MZF-FA erstellt'))
        else:
            self.stdout.write(f'  Qualifikation MZF-FA existiert bereits')

    def setup_vehicle_types(self):
        """Fahrzeugtypen anlegen"""
        self.stdout.write('Erstelle Fahrzeugtypen...')

        types = [
            {'short_name': 'HLF', 'name': 'HLF 20', 'crew_size': '1/8', 'order': 1},
            {'short_name': 'LF', 'name': 'LF KatS', 'crew_size': '1/8', 'order': 2},
            {'short_name': 'MZF', 'name': 'MZF', 'crew_size': '1/3', 'order': 3},
        ]

        for t in types:
            vt, created = VehicleType.objects.get_or_create(
                short_name=t['short_name'],
                defaults={
                    'name': t['name'],
                    'crew_size': t['crew_size'],
                    'order': t['order']
                }
            )
            status = 'erstellt' if created else 'existiert bereits'
            self.stdout.write(f'  {t["short_name"]}: {status}')

    def setup_vehicles(self):
        """Fahrzeuge anlegen"""
        self.stdout.write('Erstelle Fahrzeuge...')

        vehicles = [
            {'call_sign': '05-HLF20-01', 'type': 'HLF', 'priority': 1, 'has_optional_messenger': True},
            {'call_sign': '05-LF KatS-01', 'type': 'LF', 'priority': 2, 'has_optional_messenger': True},
            {'call_sign': '05-MZF-01', 'type': 'MZF', 'priority': 3, 'has_optional_messenger': False},
        ]

        for v in vehicles:
            vt = VehicleType.objects.get(short_name=v['type'])
            vehicle, created = Vehicle.objects.get_or_create(
                call_sign=v['call_sign'],
                defaults={
                    'vehicle_type': vt,
                    'priority': v['priority'],
                    'has_optional_messenger': v['has_optional_messenger'],
                    'is_active': True
                }
            )
            status = 'erstellt' if created else 'existiert bereits'
            self.stdout.write(f'  {v["call_sign"]}: {status}')

    def setup_vehicle_positions(self):
        """Fahrzeugpositionen mit Qualifikationsanforderungen anlegen"""
        self.stdout.write('Erstelle Fahrzeugpositionen...')

        # Positionen laden
        positions = {p.short_name: p for p in Position.objects.all()}

        # Qualifikationen laden
        quals = {q.code: q for q in Qualification.objects.all()}

        # HLF20 Positionen
        hlf = Vehicle.objects.get(call_sign='05-HLF20-01')
        self.create_hlf_positions(hlf, positions, quals, requires_agt_for_wt=True)

        # LF KatS Positionen (ähnlich wie HLF, aber WTF/WTM ohne AGT-Pflicht)
        lf = Vehicle.objects.get(call_sign='05-LF KatS-01')
        self.create_hlf_positions(lf, positions, quals, requires_agt_for_wt=False)

        # MZF Positionen
        mzf = Vehicle.objects.get(call_sign='05-MZF-01')
        self.create_mzf_positions(mzf, positions, quals)

    def create_hlf_positions(self, vehicle, positions, quals, requires_agt_for_wt=True):
        """HLF/LF Positionen erstellen"""
        self.stdout.write(f'  Positionen für {vehicle.call_sign}...')

        # Position-Konfiguration für HLF/LF
        position_configs = [
            {
                'seat': 1, 'position': 'GF', 'is_required': True, 'is_optional': False,
                'required': ['GF'], 'preferred': ['ZF', 'VF'], 'agt': False
            },
            {
                'seat': 2, 'position': 'MA', 'is_required': True, 'is_optional': False,
                'required': ['MA', 'TM'], 'preferred': ['TF'], 'agt': False
            },
            {
                'seat': 3, 'position': 'ME', 'is_required': False, 'is_optional': True,
                'required': [], 'preferred': ['GF'], 'agt': False
            },
            {
                'seat': 4, 'position': 'ATF', 'is_required': True, 'is_optional': False,
                'required': ['TF'], 'preferred': [], 'agt': True
            },
            {
                'seat': 5, 'position': 'ATM', 'is_required': True, 'is_optional': False,
                'required': ['TM'], 'preferred': ['TF'], 'agt': True
            },
            {
                'seat': 6, 'position': 'WTF', 'is_required': True, 'is_optional': False,
                'required': ['TF'], 'preferred': [], 'agt': requires_agt_for_wt
            },
            {
                'seat': 7, 'position': 'WTM', 'is_required': True, 'is_optional': False,
                'required': ['TM'], 'preferred': ['TF'], 'agt': requires_agt_for_wt
            },
            {
                'seat': 8, 'position': 'STF', 'is_required': True, 'is_optional': False,
                'required': ['TF'], 'preferred': ['AGT'], 'agt': False
            },
            {
                'seat': 9, 'position': 'STM', 'is_required': True, 'is_optional': False,
                'required': ['TM'], 'preferred': ['AGT'], 'agt': False
            },
        ]

        for config in position_configs:
            pos = positions.get(config['position'])
            if not pos:
                self.stdout.write(self.style.WARNING(f"    Position {config['position']} nicht gefunden!"))
                continue

            vp, created = VehiclePosition.objects.get_or_create(
                vehicle=vehicle,
                position=pos,
                defaults={
                    'seat_number': config['seat'],
                    'is_required': config['is_required'],
                    'is_optional': config['is_optional'],
                    'requires_agt': config['agt']
                }
            )

            if created:
                # Required Qualifications hinzufügen
                for qual_code in config['required']:
                    if qual_code in quals:
                        vp.required_qualifications.add(quals[qual_code])

                # Preferred Qualifications hinzufügen
                for qual_code in config['preferred']:
                    if qual_code in quals:
                        vp.preferred_qualifications.add(quals[qual_code])

                self.stdout.write(f'    Sitz {config["seat"]} ({config["position"]}): erstellt')
            else:
                self.stdout.write(f'    Sitz {config["seat"]} ({config["position"]}): existiert bereits')

    def create_mzf_positions(self, vehicle, positions, quals):
        """MZF Positionen erstellen"""
        self.stdout.write(f'  Positionen für {vehicle.call_sign}...')

        # Position-Konfiguration für MZF
        position_configs = [
            {
                'seat': 1, 'position': 'GF', 'is_required': True, 'is_optional': False,
                'required': ['GF'], 'preferred': ['ZF', 'VF'], 'agt': False
            },
            {
                'seat': 2, 'position': 'MA', 'is_required': True, 'is_optional': False,
                'required': ['TM', 'MZF-FA'], 'preferred': [], 'agt': False
            },
            {
                'seat': 3, 'position': 'ATF', 'is_required': True, 'is_optional': False,
                'required': ['TF'], 'preferred': [], 'agt': False
            },
            {
                'seat': 4, 'position': 'ATM', 'is_required': True, 'is_optional': False,
                'required': ['TM'], 'preferred': [], 'agt': False
            },
        ]

        for config in position_configs:
            pos = positions.get(config['position'])
            if not pos:
                self.stdout.write(self.style.WARNING(f"    Position {config['position']} nicht gefunden!"))
                continue

            vp, created = VehiclePosition.objects.get_or_create(
                vehicle=vehicle,
                position=pos,
                defaults={
                    'seat_number': config['seat'],
                    'is_required': config['is_required'],
                    'is_optional': config['is_optional'],
                    'requires_agt': config['agt']
                }
            )

            if created:
                # Required Qualifications hinzufügen
                for qual_code in config['required']:
                    if qual_code in quals:
                        vp.required_qualifications.add(quals[qual_code])

                # Preferred Qualifications hinzufügen
                for qual_code in config['preferred']:
                    if qual_code in quals:
                        vp.preferred_qualifications.add(quals[qual_code])

                self.stdout.write(f'    Sitz {config["seat"]} ({config["position"]}): erstellt')
            else:
                self.stdout.write(f'    Sitz {config["seat"]} ({config["position"]}): existiert bereits')
