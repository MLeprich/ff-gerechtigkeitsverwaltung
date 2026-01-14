import csv
import io
from datetime import datetime

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST

from apps.core.views import leader_required
from apps.qualifications.models import (
    Qualification, MemberQualification, MedicalExamType, MedicalExam, ExerciseRecord
)
from .models import Member, Unit


@login_required
@leader_required
def member_list(request):
    """Mitgliederliste"""
    members = Member.objects.all().select_related('unit')

    # Filter
    status_filter = request.GET.get('status', '')
    unit_filter = request.GET.get('unit', '')
    search = request.GET.get('search', '')

    if status_filter:
        members = members.filter(status=status_filter)
    if unit_filter:
        members = members.filter(unit_id=unit_filter)
    if search:
        members = members.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(member_number__icontains=search)
        )

    units = Unit.objects.filter(is_active=True)

    context = {
        'members': members,
        'units': units,
        'status_choices': Member.Status.choices,
        'current_status': status_filter,
        'current_unit': unit_filter,
        'search': search,
    }
    return render(request, 'members/member_list.html', context)


@login_required
@leader_required
def member_detail(request, member_id):
    """Mitglied-Detailansicht"""
    member = get_object_or_404(Member, id=member_id)

    # Qualifikationen laden
    qualifications = member.qualifications.select_related(
        'qualification', 'qualification__category'
    ).order_by('qualification__category__order', 'qualification__order')

    # Untersuchungen laden
    medical_exams = MedicalExam.objects.filter(member=member).select_related('exam_type').order_by('-exam_date')

    # AGT-Übungen laden
    exercise_records = ExerciseRecord.objects.filter(member=member).select_related('qualification').order_by('-exercise_date')

    # Verfügbare Qualifikationen für Modal (ohne bereits zugewiesene)
    assigned_qualification_ids = qualifications.values_list('qualification_id', flat=True)
    available_qualifications = Qualification.objects.filter(
        is_active=True
    ).exclude(
        id__in=assigned_qualification_ids
    ).select_related('category').order_by('category__order', 'order')

    # Verfügbare Untersuchungstypen
    exam_types = MedicalExamType.objects.all()

    context = {
        'member': member,
        'qualifications': qualifications,
        'medical_exams': medical_exams,
        'exercise_records': exercise_records,
        'agt_valid': member.has_valid_agt_status(),
        # Für Modals
        'available_qualifications': available_qualifications,
        'exam_types': exam_types,
    }
    return render(request, 'members/member_detail.html', context)


@login_required
@leader_required
def member_edit(request, member_id=None):
    """Mitglied erstellen oder bearbeiten"""
    if member_id:
        member = get_object_or_404(Member, id=member_id)
    else:
        member = None

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()

        if not first_name or not last_name:
            messages.error(request, 'Vor- und Nachname sind erforderlich.')
        else:
            if member:
                # Update
                member.first_name = first_name
                member.last_name = last_name
                member.birth_date = request.POST.get('birth_date') or None
                member.email = request.POST.get('email', '')
                member.phone = request.POST.get('phone', '')
                member.mobile = request.POST.get('mobile', '')
                member.member_number = request.POST.get('member_number', '')
                member.entry_date = request.POST.get('entry_date') or None
                member.status = request.POST.get('status', 'active')
                member.unit_id = request.POST.get('unit') or None
                member.notes = request.POST.get('notes', '')
                member.is_active = request.POST.get('is_active') == 'on'
                member.save()
                messages.success(request, 'Mitglied wurde aktualisiert.')
            else:
                # Create
                member = Member.objects.create(
                    first_name=first_name,
                    last_name=last_name,
                    birth_date=request.POST.get('birth_date') or None,
                    email=request.POST.get('email', ''),
                    phone=request.POST.get('phone', ''),
                    mobile=request.POST.get('mobile', ''),
                    member_number=request.POST.get('member_number', ''),
                    entry_date=request.POST.get('entry_date') or None,
                    status=request.POST.get('status', 'active'),
                    unit_id=request.POST.get('unit') or None,
                    notes=request.POST.get('notes', ''),
                    is_active=request.POST.get('is_active') == 'on'
                )
                messages.success(request, 'Mitglied wurde erstellt.')
            return redirect('member_detail', member_id=member.id)

    units = Unit.objects.filter(is_active=True)

    context = {
        'member': member,
        'units': units,
        'status_choices': Member.Status.choices,
    }
    return render(request, 'members/member_form.html', context)


@login_required
@leader_required
def member_delete(request, member_id):
    """Mitglied löschen"""
    member = get_object_or_404(Member, id=member_id)

    if request.method == 'POST':
        name = member.full_name
        member.delete()
        messages.success(request, f'Mitglied "{name}" wurde gelöscht.')
        return redirect('member_list')

    return render(request, 'members/member_confirm_delete.html', {'member': member})


@login_required
@leader_required
def member_import_csv(request):
    """CSV-Import für Mitglieder"""
    if request.method == 'POST':
        csv_file = request.FILES.get('csv_file')

        if not csv_file:
            messages.error(request, 'Bitte wählen Sie eine CSV-Datei aus.')
            return redirect('member_list')

        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Bitte laden Sie eine CSV-Datei hoch.')
            return redirect('member_list')

        try:
            # CSV lesen
            decoded_file = csv_file.read().decode('utf-8-sig')
            io_string = io.StringIO(decoded_file)
            reader = csv.DictReader(io_string, delimiter=';')

            created_count = 0
            updated_count = 0
            error_count = 0
            errors = []

            # Status-Mapping (deutsch -> english)
            status_mapping = {
                'aktiv': 'active',
                'inaktiv': 'inactive',
                'jugendfeuerwehr': 'youth',
                'jugend': 'youth',
                'altersabteilung': 'honorary',
                'ehrenabteilung': 'honorary',
                'reserve': 'reserve',
            }

            for row_num, row in enumerate(reader, start=2):
                try:
                    # Pflichtfelder prüfen
                    vorname = row.get('vorname', '').strip()
                    nachname = row.get('nachname', '').strip()

                    if not vorname or not nachname:
                        errors.append(f'Zeile {row_num}: Vor- und Nachname sind erforderlich.')
                        error_count += 1
                        continue

                    # Einheit finden/erstellen
                    unit = None
                    einheit_name = row.get('einheit', '').strip()
                    if einheit_name:
                        unit, _ = Unit.objects.get_or_create(
                            name=einheit_name,
                            defaults={'is_active': True}
                        )

                    # Status konvertieren
                    status_raw = row.get('status', 'aktiv').strip().lower()
                    status = status_mapping.get(status_raw, 'active')

                    # Datum parsen
                    def parse_date(date_str):
                        if not date_str or not date_str.strip():
                            return None
                        date_str = date_str.strip()
                        for fmt in ['%d.%m.%Y', '%Y-%m-%d', '%d/%m/%Y']:
                            try:
                                return datetime.strptime(date_str, fmt).date()
                            except ValueError:
                                continue
                        return None

                    birth_date = parse_date(row.get('geburtsdatum', ''))
                    entry_date = parse_date(row.get('eintrittsdatum', ''))

                    # Mitglied erstellen oder aktualisieren
                    member_number = row.get('mitgliedsnummer', '').strip()

                    # Prüfen ob Mitglied existiert (nach Mitgliedsnummer oder Name)
                    existing_member = None
                    if member_number:
                        existing_member = Member.objects.filter(member_number=member_number).first()

                    if not existing_member:
                        existing_member = Member.objects.filter(
                            first_name__iexact=vorname,
                            last_name__iexact=nachname,
                            birth_date=birth_date
                        ).first()

                    if existing_member:
                        # Update
                        existing_member.first_name = vorname
                        existing_member.last_name = nachname
                        existing_member.birth_date = birth_date
                        existing_member.email = row.get('email', '').strip()
                        existing_member.phone = row.get('telefon', '').strip()
                        existing_member.mobile = row.get('mobil', '').strip()
                        existing_member.member_number = member_number
                        existing_member.entry_date = entry_date
                        existing_member.status = status
                        existing_member.unit = unit
                        existing_member.notes = row.get('bemerkungen', '').strip()
                        existing_member.save()
                        updated_count += 1
                    else:
                        # Create
                        Member.objects.create(
                            first_name=vorname,
                            last_name=nachname,
                            birth_date=birth_date,
                            email=row.get('email', '').strip(),
                            phone=row.get('telefon', '').strip(),
                            mobile=row.get('mobil', '').strip(),
                            member_number=member_number,
                            entry_date=entry_date,
                            status=status,
                            unit=unit,
                            notes=row.get('bemerkungen', '').strip(),
                            is_active=True
                        )
                        created_count += 1

                except Exception as e:
                    errors.append(f'Zeile {row_num}: {str(e)}')
                    error_count += 1

            # Ergebnis-Meldung
            if created_count > 0 or updated_count > 0:
                msg = []
                if created_count > 0:
                    msg.append(f'{created_count} Mitglied(er) erstellt')
                if updated_count > 0:
                    msg.append(f'{updated_count} Mitglied(er) aktualisiert')
                messages.success(request, ', '.join(msg) + '.')

            if error_count > 0:
                messages.warning(request, f'{error_count} Zeile(n) konnten nicht importiert werden.')
                for error in errors[:5]:  # Nur erste 5 Fehler anzeigen
                    messages.error(request, error)

        except Exception as e:
            messages.error(request, f'Fehler beim Verarbeiten der CSV-Datei: {str(e)}')

    return redirect('member_list')


@login_required
@leader_required
def member_export_csv_template(request):
    """Beispiel-CSV-Datei für Import"""
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="mitglieder_vorlage.csv"'

    # BOM für Excel-Kompatibilität
    response.write('\ufeff')

    writer = csv.writer(response, delimiter=';')

    # Header
    writer.writerow([
        'vorname',
        'nachname',
        'geburtsdatum',
        'email',
        'telefon',
        'mobil',
        'mitgliedsnummer',
        'eintrittsdatum',
        'status',
        'einheit',
        'bemerkungen'
    ])

    # Beispieldaten
    writer.writerow([
        'Max',
        'Mustermann',
        '15.03.1990',
        'max.mustermann@email.de',
        '01234 56789',
        '0170 1234567',
        'M-001',
        '01.01.2015',
        'Aktiv',
        'Löschzug 1',
        'Beispielmitglied'
    ])

    writer.writerow([
        'Anna',
        'Beispiel',
        '22.07.1995',
        'anna.beispiel@email.de',
        '',
        '0171 9876543',
        'M-002',
        '15.06.2018',
        'Aktiv',
        'Löschzug 1',
        ''
    ])

    writer.writerow([
        'Tim',
        'Nachwuchs',
        '10.11.2010',
        '',
        '',
        '',
        'J-001',
        '01.09.2020',
        'Jugendfeuerwehr',
        'Jugendfeuerwehr',
        ''
    ])

    return response


@login_required
@leader_required
def member_export_csv(request):
    """Export aller Mitglieder als CSV"""
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="mitglieder_export.csv"'

    # BOM für Excel-Kompatibilität
    response.write('\ufeff')

    writer = csv.writer(response, delimiter=';')

    # Header
    writer.writerow([
        'vorname',
        'nachname',
        'geburtsdatum',
        'email',
        'telefon',
        'mobil',
        'mitgliedsnummer',
        'eintrittsdatum',
        'status',
        'einheit',
        'bemerkungen'
    ])

    # Status-Mapping (english -> deutsch)
    status_display = {
        'active': 'Aktiv',
        'inactive': 'Inaktiv',
        'youth': 'Jugendfeuerwehr',
        'honorary': 'Altersabteilung',
        'reserve': 'Reserve',
    }

    members = Member.objects.all().select_related('unit').order_by('last_name', 'first_name')

    for member in members:
        writer.writerow([
            member.first_name,
            member.last_name,
            member.birth_date.strftime('%d.%m.%Y') if member.birth_date else '',
            member.email,
            member.phone,
            member.mobile,
            member.member_number,
            member.entry_date.strftime('%d.%m.%Y') if member.entry_date else '',
            status_display.get(member.status, member.status),
            member.unit.name if member.unit else '',
            member.notes
        ])

    return response


# ============================================================================
# Qualifikationen verwalten
# ============================================================================

@login_required
@leader_required
def member_qualification_add(request, member_id):
    """Qualifikation zu Mitglied hinzufügen"""
    member = get_object_or_404(Member, id=member_id)

    if request.method == 'POST':
        qualification_id = request.POST.get('qualification')
        acquired_date = request.POST.get('acquired_date') or None
        notes = request.POST.get('notes', '')

        if qualification_id:
            qualification = get_object_or_404(Qualification, id=qualification_id)

            # Prüfen ob bereits vorhanden
            if not MemberQualification.objects.filter(member=member, qualification=qualification).exists():
                MemberQualification.objects.create(
                    member=member,
                    qualification=qualification,
                    acquired_date=acquired_date,
                    notes=notes
                )
                messages.success(request, f'Qualifikation "{qualification.code}" wurde hinzugefügt.')
            else:
                messages.warning(request, f'Qualifikation "{qualification.code}" ist bereits vorhanden.')
        else:
            messages.error(request, 'Bitte wählen Sie eine Qualifikation aus.')

    return redirect('member_detail', member_id=member_id)


@login_required
@leader_required
def member_qualification_remove(request, member_id, qualification_id):
    """Qualifikation von Mitglied entfernen"""
    member = get_object_or_404(Member, id=member_id)
    member_qual = get_object_or_404(MemberQualification, member=member, qualification_id=qualification_id)

    if request.method == 'POST':
        qual_code = member_qual.qualification.code
        member_qual.delete()
        messages.success(request, f'Qualifikation "{qual_code}" wurde entfernt.')

    return redirect('member_detail', member_id=member_id)


# ============================================================================
# Medizinische Untersuchungen verwalten
# ============================================================================

@login_required
@leader_required
def member_exam_add(request, member_id):
    """Ärztliche Untersuchung hinzufügen"""
    member = get_object_or_404(Member, id=member_id)

    if request.method == 'POST':
        exam_type_id = request.POST.get('exam_type')
        exam_date = request.POST.get('exam_date')
        result_positive = request.POST.get('result_positive') == 'on'
        notes = request.POST.get('notes', '')

        if exam_type_id and exam_date:
            exam_type = get_object_or_404(MedicalExamType, id=exam_type_id)

            MedicalExam.objects.create(
                member=member,
                exam_type=exam_type,
                exam_date=exam_date,
                result_positive=result_positive,
                notes=notes
            )
            messages.success(request, f'Untersuchung "{exam_type.name}" wurde hinzugefügt.')
        else:
            messages.error(request, 'Bitte füllen Sie alle Pflichtfelder aus.')

    return redirect('member_detail', member_id=member_id)


@login_required
@leader_required
def member_exam_delete(request, member_id, exam_id):
    """Ärztliche Untersuchung löschen"""
    member = get_object_or_404(Member, id=member_id)
    exam = get_object_or_404(MedicalExam, id=exam_id, member=member)

    if request.method == 'POST':
        exam_name = exam.exam_type.name
        exam.delete()
        messages.success(request, f'Untersuchung "{exam_name}" wurde gelöscht.')

    return redirect('member_detail', member_id=member_id)


# ============================================================================
# AGT-Übungen verwalten
# ============================================================================

@login_required
@leader_required
def member_exercise_add(request, member_id):
    """AGT-Übung hinzufügen"""
    member = get_object_or_404(Member, id=member_id)

    if request.method == 'POST':
        exercise_date = request.POST.get('exercise_date')
        exercise_type = request.POST.get('exercise_type', '').strip()
        notes = request.POST.get('notes', '')

        if exercise_date and exercise_type:
            # AGT-Qualifikation finden
            agt_qual = Qualification.objects.filter(code='AGT').first()

            if agt_qual:
                ExerciseRecord.objects.create(
                    member=member,
                    qualification=agt_qual,
                    exercise_date=exercise_date,
                    exercise_type=exercise_type,
                    notes=notes
                )
                messages.success(request, 'AGT-Übung wurde hinzugefügt.')
            else:
                messages.error(request, 'AGT-Qualifikation nicht gefunden. Bitte zuerst in der Qualifikationsverwaltung anlegen.')
        else:
            messages.error(request, 'Bitte füllen Sie Datum und Übungsart aus.')

    return redirect('member_detail', member_id=member_id)


@login_required
@leader_required
def member_exercise_delete(request, member_id, exercise_id):
    """AGT-Übung löschen"""
    member = get_object_or_404(Member, id=member_id)
    exercise = get_object_or_404(ExerciseRecord, id=exercise_id, member=member)

    if request.method == 'POST':
        exercise.delete()
        messages.success(request, 'Übung wurde gelöscht.')

    return redirect('member_detail', member_id=member_id)
