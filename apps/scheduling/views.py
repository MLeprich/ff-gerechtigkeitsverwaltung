from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from datetime import timedelta, datetime
from dateutil.relativedelta import relativedelta

from apps.core.views import leader_required, admin_required
from apps.vehicles.models import Vehicle, VehiclePosition
from apps.members.models import Member
from .models import Duty, DutyType, Assignment, DutyAttendance


@login_required
def duty_list(request):
    """Dienstliste"""
    today = timezone.now().date()

    # Filter
    show = request.GET.get('show', 'upcoming')
    type_filter = request.GET.get('type', '')
    status_filter = request.GET.get('status', '')

    duties = Duty.objects.all().select_related('duty_type', 'created_by')

    if show == 'upcoming':
        duties = duties.filter(date__gte=today)
    elif show == 'past':
        duties = duties.filter(date__lt=today)
    # 'all' shows everything

    if type_filter:
        duties = duties.filter(duty_type_id=type_filter)

    if status_filter:
        duties = duties.filter(status=status_filter)

    duties = duties.order_by('date', 'start_time')

    duty_types = DutyType.objects.filter(is_active=True)

    context = {
        'duties': duties,
        'duty_types': duty_types,
        'status_choices': Duty.Status.choices,
        'current_show': show,
        'current_type': type_filter,
        'current_status': status_filter,
        'today': today,
    }
    return render(request, 'scheduling/duty_list.html', context)


@login_required
def duty_detail(request, duty_id):
    """Dienst-Detailansicht"""
    duty = get_object_or_404(Duty, id=duty_id)

    # Einteilungen laden
    assignments = duty.assignments.select_related(
        'vehicle', 'vehicle_position__position', 'member'
    ).order_by('vehicle', 'vehicle_position__seat_number')

    # Verfügbarkeiten laden
    from apps.members.models import Availability
    availabilities = Availability.objects.filter(duty=duty).select_related('member')

    # Alle aktiven Mitglieder laden für Anwesenheitserfassung
    all_members = Member.objects.filter(
        status='active',
        is_active=True
    ).select_related('unit').prefetch_related(
        'qualifications__qualification'
    ).order_by('unit__order', 'last_name', 'first_name')

    # Anwesenheiten laden
    attendances = {
        att.member_id: att
        for att in DutyAttendance.objects.filter(duty=duty)
    }

    # Mitglieder mit Anwesenheitsstatus anreichern
    members_with_attendance = []
    for member in all_members:
        attendance = attendances.get(member.id)
        members_with_attendance.append({
            'member': member,
            'is_present': attendance.is_present if attendance else False,
            'qualifications': [mq.qualification.code for mq in member.qualifications.all()],
            'has_agt': member.has_valid_agt_status(),
        })

    # Anwesende zählen
    present_count = sum(1 for m in members_with_attendance if m['is_present'])

    # Fahrzeuge mit Positionen für Besetzungs-UI
    vehicles_with_positions = []
    for vehicle in duty.vehicles.all().order_by('priority'):
        positions = VehiclePosition.objects.filter(
            vehicle=vehicle
        ).select_related('position').prefetch_related(
            'required_qualifications', 'preferred_qualifications'
        ).order_by('seat_number')

        # Bestehende Assignments für dieses Fahrzeug
        vehicle_assignments = {
            a.vehicle_position_id: a
            for a in assignments if a.vehicle_id == vehicle.id
        }

        positions_data = []
        for pos in positions:
            assignment = vehicle_assignments.get(pos.id)
            positions_data.append({
                'position': pos,
                'assignment': assignment,
                'member': assignment.member if assignment else None,
                'has_warning': assignment.has_warning if assignment else False,
                'warning_text': assignment.warning_text if assignment else '',
            })

        vehicles_with_positions.append({
            'vehicle': vehicle,
            'positions': positions_data,
        })

    context = {
        'duty': duty,
        'assignments': assignments,
        'availabilities': availabilities,
        'members_with_attendance': members_with_attendance,
        'present_count': present_count,
        'vehicles_with_positions': vehicles_with_positions,
    }
    return render(request, 'scheduling/duty_detail.html', context)


@login_required
@leader_required
def duty_edit(request, duty_id=None):
    """Dienst erstellen oder bearbeiten"""
    if duty_id:
        duty = get_object_or_404(Duty, id=duty_id)
    else:
        duty = None

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        date = request.POST.get('date')
        duty_type_id = request.POST.get('duty_type')

        if not title or not date:
            messages.error(request, 'Titel und Datum sind erforderlich.')
        else:
            start_time = request.POST.get('start_time') or None
            end_time = request.POST.get('end_time') or None

            if duty:
                duty.title = title
                duty.date = date
                duty.duty_type_id = duty_type_id or None
                duty.start_time = start_time
                duty.end_time = end_time
                duty.location = request.POST.get('location', '')
                duty.description = request.POST.get('description', '')
                duty.status = request.POST.get('status', 'draft')
                duty.min_agt_count = int(request.POST.get('min_agt_count', 0))
                duty.notes = request.POST.get('notes', '')
                duty.save()

                # Fahrzeuge aktualisieren
                vehicle_ids = request.POST.getlist('vehicles')
                duty.vehicles.set(vehicle_ids)

                messages.success(request, 'Dienst wurde aktualisiert.')
            else:
                # Prüfen ob wiederkehrender Dienst
                is_recurring = request.POST.get('is_recurring') == 'on'
                recurrence_pattern = request.POST.get('recurrence_pattern', 'weekly')
                recurrence_end = request.POST.get('recurrence_end')

                if is_recurring:
                    # Wiederkehrende Dienste erstellen
                    start_date = datetime.strptime(date, '%Y-%m-%d').date()
                    # Standard: 1 Jahr wenn kein Enddatum angegeben
                    if recurrence_end:
                        end_date = datetime.strptime(recurrence_end, '%Y-%m-%d').date()
                    else:
                        end_date = start_date + relativedelta(years=1)

                    # Alle Termine berechnen
                    dates = []
                    current_date = start_date
                    while current_date <= end_date:
                        dates.append(current_date)
                        if recurrence_pattern == 'weekly':
                            current_date += timedelta(weeks=1)
                        elif recurrence_pattern == 'biweekly':
                            current_date += timedelta(weeks=2)
                        elif recurrence_pattern == 'monthly':
                            # Gleicher Wochentag im nächsten Monat
                            current_date += relativedelta(months=1)

                    # Dienste erstellen
                    vehicle_ids = request.POST.getlist('vehicles')
                    first_duty = None
                    for duty_date in dates:
                        # Titel mit Datum formatieren
                        formatted_title = f"{title} ({duty_date.strftime('%d.%m.%Y')})"

                        duty = Duty.objects.create(
                            title=formatted_title,
                            date=duty_date,
                            duty_type_id=duty_type_id or None,
                            start_time=start_time,
                            end_time=end_time,
                            location=request.POST.get('location', ''),
                            description=request.POST.get('description', ''),
                            status=request.POST.get('status', 'draft'),
                            min_agt_count=int(request.POST.get('min_agt_count', 0)),
                            notes=request.POST.get('notes', ''),
                            created_by=request.user
                        )
                        duty.vehicles.set(vehicle_ids)

                        if first_duty is None:
                            first_duty = duty

                    messages.success(request, f'{len(dates)} Dienste wurden erstellt.')
                    return redirect('duty_detail', duty_id=first_duty.id)
                else:
                    # Einzelner Dienst
                    duty = Duty.objects.create(
                        title=title,
                        date=date,
                        duty_type_id=duty_type_id or None,
                        start_time=start_time,
                        end_time=end_time,
                        location=request.POST.get('location', ''),
                        description=request.POST.get('description', ''),
                        status=request.POST.get('status', 'draft'),
                        min_agt_count=int(request.POST.get('min_agt_count', 0)),
                        notes=request.POST.get('notes', ''),
                        created_by=request.user
                    )

                    # Fahrzeuge zuordnen
                    vehicle_ids = request.POST.getlist('vehicles')
                    duty.vehicles.set(vehicle_ids)

                    messages.success(request, 'Dienst wurde erstellt.')
            return redirect('duty_detail', duty_id=duty.id)

    duty_types = DutyType.objects.filter(is_active=True)
    vehicles = Vehicle.objects.filter(is_active=True)

    context = {
        'duty': duty,
        'duty_types': duty_types,
        'vehicles': vehicles,
        'status_choices': Duty.Status.choices,
    }
    return render(request, 'scheduling/duty_form.html', context)


@login_required
@leader_required
def duty_delete(request, duty_id):
    """Dienst löschen"""
    duty = get_object_or_404(Duty, id=duty_id)

    if request.method == 'POST':
        title = duty.title
        duty.delete()
        messages.success(request, f'Dienst "{title}" wurde gelöscht.')
        return redirect('duty_list')

    return render(request, 'scheduling/duty_confirm_delete.html', {'duty': duty})


# ============ Diensttypen ============

@login_required
@admin_required
def duty_type_list(request):
    """Diensttypen-Liste"""
    duty_types = DutyType.objects.all()

    context = {
        'duty_types': duty_types,
    }
    return render(request, 'scheduling/duty_type_list.html', context)


@login_required
@admin_required
def duty_type_edit(request, type_id=None):
    """Diensttyp erstellen oder bearbeiten"""
    if type_id:
        duty_type = get_object_or_404(DutyType, id=type_id)
    else:
        duty_type = None

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()

        if not name:
            messages.error(request, 'Name ist erforderlich.')
        else:
            color = request.POST.get('color', '#3B82F6')
            is_active = request.POST.get('is_active') == 'on'

            if duty_type:
                duty_type.name = name
                duty_type.color = color
                duty_type.is_active = is_active
                duty_type.save()
                messages.success(request, 'Diensttyp wurde aktualisiert.')
            else:
                duty_type = DutyType.objects.create(
                    name=name,
                    color=color,
                    is_active=is_active
                )
                messages.success(request, 'Diensttyp wurde erstellt.')
            return redirect('duty_type_list')

    context = {
        'duty_type': duty_type,
    }
    return render(request, 'scheduling/duty_type_form.html', context)


@login_required
@admin_required
def duty_type_delete(request, type_id):
    """Diensttyp löschen"""
    duty_type = get_object_or_404(DutyType, id=type_id)

    if request.method == 'POST':
        name = duty_type.name
        duty_type.delete()
        messages.success(request, f'Diensttyp "{name}" wurde gelöscht.')
        return redirect('duty_type_list')

    return render(request, 'scheduling/duty_type_confirm_delete.html', {'duty_type': duty_type})


# ============ Anwesenheit & Besetzung ============

@login_required
@leader_required
@require_POST
def attendance_toggle(request, duty_id, member_id):
    """Anwesenheit eines Mitglieds für einen Dienst umschalten (AJAX)"""
    duty = get_object_or_404(Duty, id=duty_id)
    member = get_object_or_404(Member, id=member_id)

    attendance, created = DutyAttendance.objects.get_or_create(
        duty=duty,
        member=member,
        defaults={'is_present': False}
    )

    # Umschalten
    attendance.is_present = not attendance.is_present
    if attendance.is_present:
        attendance.checked_in_at = timezone.now()
        attendance.checked_in_by = request.user
    else:
        attendance.checked_in_at = None
        attendance.checked_in_by = None
    attendance.save()

    return JsonResponse({
        'success': True,
        'is_present': attendance.is_present,
        'member_id': member_id,
    })


@login_required
@leader_required
@require_POST
def update_assignment(request, duty_id, position_id):
    """Assignment für eine Position aktualisieren (AJAX)"""
    duty = get_object_or_404(Duty, id=duty_id)
    vehicle_position = get_object_or_404(VehiclePosition, id=position_id)

    member_id = request.POST.get('member_id')

    if member_id:
        member = get_object_or_404(Member, id=member_id)
    else:
        member = None

    # Assignment erstellen oder aktualisieren
    assignment, created = Assignment.objects.update_or_create(
        duty=duty,
        vehicle_position=vehicle_position,
        defaults={
            'vehicle': vehicle_position.vehicle,
            'member': member,
            'status': Assignment.Status.SUGGESTED,
        }
    )

    # Qualifikation prüfen und Warnung setzen
    if member:
        from .generator import check_member_qualification
        is_qualified, warning = check_member_qualification(member, vehicle_position)
        assignment.has_warning = not is_qualified
        assignment.warning_text = warning if warning else ''
        assignment.save()

    return JsonResponse({
        'success': True,
        'assignment_id': assignment.id,
        'member_name': member.full_name if member else None,
        'has_warning': assignment.has_warning,
        'warning_text': assignment.warning_text,
    })


@login_required
@leader_required
def generate_assignments(request, duty_id):
    """Automatische Besetzung generieren"""
    duty = get_object_or_404(Duty, id=duty_id)

    if request.method == 'POST':
        from .generator import AssignmentGenerator

        # Ausgewaehlte Fahrzeuge aus dem Formular
        selected_vehicle_ids = request.POST.getlist('vehicles')

        if not selected_vehicle_ids:
            messages.error(request, 'Bitte waehlen Sie mindestens ein Fahrzeug aus.')
            return redirect('duty_detail', duty_id=duty_id)

        # IDs in Integer konvertieren
        selected_vehicle_ids = [int(vid) for vid in selected_vehicle_ids]

        generator = AssignmentGenerator(duty, selected_vehicle_ids=selected_vehicle_ids)
        result = generator.generate()

        if result['success']:
            messages.success(
                request,
                f'Besetzung generiert: {result["assigned_count"]} Positionen besetzt, '
                f'{result["warning_count"]} mit Warnungen.'
            )
        else:
            messages.error(request, f'Fehler bei der Generierung: {result["error"]}')

    return redirect('duty_detail', duty_id=duty_id)


# ============ Statistiken ============

@login_required
@leader_required
def statistics(request):
    """Fairness-Statistiken anzeigen"""
    from datetime import date
    from django.db.models import Count
    from apps.vehicles.models import Vehicle, Position

    current_year = date.today().year
    selected_year = int(request.GET.get('year', current_year))

    # Jahre für Dropdown (letzte 5 Jahre)
    years = list(range(current_year, current_year - 5, -1))

    # Mitglieder mit Statistiken laden
    members = Member.objects.filter(
        status='active',
        is_active=True
    ).prefetch_related('assignment_history').order_by('last_name', 'first_name')

    # Fahrzeuge und Positionen für Spalten
    vehicles = Vehicle.objects.filter(is_active=True).order_by('priority')
    positions = Position.objects.all().order_by('order')

    # Statistiken pro Mitglied berechnen
    from .models import AssignmentHistory

    member_stats = []
    for member in members:
        history = AssignmentHistory.objects.filter(
            member=member,
            year=selected_year
        )

        # Gesamt
        total = history.count()

        # Pro Fahrzeug
        by_vehicle = {}
        for v in vehicles:
            count = history.filter(vehicle=v).count()
            by_vehicle[v.call_sign] = count

        # Pro Position
        by_position = {}
        for p in positions:
            count = history.filter(position=p).count()
            by_position[p.short_name] = count

        member_stats.append({
            'member': member,
            'total': total,
            'by_vehicle': by_vehicle,
            'by_position': by_position,
        })

    # Sortieren nach Gesamt (absteigend)
    member_stats.sort(key=lambda x: x['total'], reverse=True)

    # Fahrzeug-Zusammenfassung
    vehicle_totals = {}
    for v in vehicles:
        vehicle_totals[v.call_sign] = AssignmentHistory.objects.filter(
            vehicle=v,
            year=selected_year
        ).count()

    # Position-Zusammenfassung
    position_totals = {}
    for p in positions:
        position_totals[p.short_name] = AssignmentHistory.objects.filter(
            position=p,
            year=selected_year
        ).count()

    context = {
        'member_stats': member_stats,
        'vehicles': vehicles,
        'positions': positions,
        'vehicle_totals': vehicle_totals,
        'position_totals': position_totals,
        'selected_year': selected_year,
        'years': years,
        'total_duties': sum(vehicle_totals.values()),
    }
    return render(request, 'scheduling/statistics.html', context)
