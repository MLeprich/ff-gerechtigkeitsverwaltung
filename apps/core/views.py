from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count
from django.utils import timezone
from django.http import HttpResponse
from datetime import timedelta
from functools import wraps

from .models import Settings, User, AuditLog
from apps.members.models import Member, Unit
from apps.vehicles.models import Vehicle, VehicleType, Position
from apps.qualifications.models import Qualification, QualificationCategory
from apps.scheduling.models import Duty, Assignment, DutyType


def admin_required(view_func):
    """Decorator für Admin-only Views"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not (request.user.is_superuser or request.user.role == 'admin'):
            messages.error(request, 'Sie haben keine Berechtigung für diesen Bereich.')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


def leader_required(view_func):
    """Decorator für Gruppenführer+ Views"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not request.user.is_leader:
            messages.error(request, 'Sie haben keine Berechtigung für diesen Bereich.')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            next_url = request.GET.get('next', 'dashboard')
            return redirect(next_url)
        else:
            messages.error(request, 'Ungültige Anmeldedaten.')

    return render(request, 'core/login.html')


def logout_view(request):
    logout(request)
    messages.success(request, 'Sie wurden erfolgreich abgemeldet.')
    return redirect('login')


@login_required
def dashboard(request):
    # Prüfen ob Settings existieren, sonst Setup-Wizard
    if not Settings.objects.exists():
        if request.user.is_superuser:
            return redirect('setup_wizard')
        else:
            messages.warning(request, 'Die Anwendung muss erst eingerichtet werden.')
            return render(request, 'core/dashboard.html', {'needs_setup': True})

    today = timezone.now().date()
    week_ahead = today + timedelta(days=7)

    # Statistiken
    active_members = Member.objects.filter(
        is_active=True,
        status='active'
    ).count()

    active_vehicles = Vehicle.objects.filter(
        is_active=True
    ).count()

    # Kommende Dienste
    upcoming_duties = Duty.objects.filter(
        date__gte=today,
        date__lte=week_ahead
    ).exclude(status='cancelled').order_by('date', 'start_time')[:5]

    # Dienste diesen Monat
    month_start = today.replace(day=1)
    duties_this_month = Duty.objects.filter(
        date__gte=month_start,
        date__lte=today
    ).exclude(status='cancelled').count()

    # Offene Positionen
    open_positions = Assignment.objects.filter(
        duty__date__gte=today,
        member__isnull=True
    ).count()

    # Qualifikationen die bald ablaufen
    from apps.qualifications.models import MedicalExam
    expiring_soon = MedicalExam.objects.filter(
        valid_until__gte=today,
        valid_until__lte=today + timedelta(days=60)
    ).select_related('member', 'exam_type').order_by('valid_until')[:5]

    context = {
        'active_members': active_members,
        'active_vehicles': active_vehicles,
        'upcoming_duties': upcoming_duties,
        'duties_this_month': duties_this_month,
        'open_positions': open_positions,
        'expiring_soon': expiring_soon,
        'today': today,
        'settings': Settings.get_instance() if Settings.objects.exists() else None,
    }

    return render(request, 'core/dashboard.html', context)


@login_required
def setup_wizard(request):
    """Ersteinrichtung der Feuerwehr"""
    if not request.user.is_superuser:
        return redirect('dashboard')

    # Bereits eingerichtet?
    if Settings.objects.exists():
        return redirect('dashboard')

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        short_name = request.POST.get('short_name', '').strip()
        city = request.POST.get('city', '').strip()

        if not name or not short_name:
            messages.error(request, 'Name und Kurzname sind erforderlich.')
            return render(request, 'core/setup_wizard.html')

        # Settings erstellen
        Settings.objects.create(
            name=name,
            short_name=short_name,
            city=city
        )

        # Admin-Rolle setzen
        request.user.role = 'admin'
        request.user.save()

        # Standard-Qualifikationen erstellen
        create_default_qualifications()

        # Standard-Positionen erstellen
        create_default_positions()

        # Standard-Diensttypen erstellen
        create_default_duty_types()

        messages.success(request, f'"{name}" wurde erfolgreich eingerichtet!')
        return redirect('dashboard')

    return render(request, 'core/setup_wizard.html')


def create_default_qualifications():
    """Erstellt Standard-Qualifikationen nach FwDV"""
    categories = {
        'grund': QualificationCategory.objects.create(name='Grundausbildung', order=1),
        'fuehrung': QualificationCategory.objects.create(name='Führung', order=2),
        'sonder': QualificationCategory.objects.create(name='Sonderausbildung', order=3),
    }

    qualifications_data = [
        ('TM1', 'Truppmann Teil 1', 'grund', 1),
        ('TM2', 'Truppmann Teil 2', 'grund', 2),
        ('TM', 'Truppmann (vollständig)', 'grund', 3),
        ('AGT', 'Atemschutzgeräteträger', 'sonder', 10),
        ('MA', 'Maschinist', 'sonder', 11),
        ('TF', 'Truppführer', 'fuehrung', 20),
        ('GF', 'Gruppenführer', 'fuehrung', 21),
        ('ZF', 'Zugführer', 'fuehrung', 22),
        ('ABC1', 'ABC-Einsatz Grundlagen', 'sonder', 30),
        ('ABC2', 'ABC-Einsatz Erweitert', 'sonder', 31),
        ('MKS', 'Motorkettensägenführer', 'sonder', 40),
    ]

    quals = {}
    for code, name, cat_key, order in qualifications_data:
        q = Qualification.objects.create(
            category=categories[cat_key],
            code=code,
            name=name,
            order=order,
            requires_exercises=(code == 'AGT'),
            exercise_count=1 if code == 'AGT' else None,
        )
        quals[code] = q

    # Hierarchien setzen (höhere deckt niedrigere ab)
    if 'TM' in quals and 'TM1' in quals:
        quals['TM'].covers.add(quals['TM1'])
    if 'TM' in quals and 'TM2' in quals:
        quals['TM'].covers.add(quals['TM2'])
    if 'TF' in quals and 'TM' in quals:
        quals['TF'].covers.add(quals['TM'])
    if 'GF' in quals and 'TF' in quals:
        quals['GF'].covers.add(quals['TF'])
    if 'ZF' in quals and 'GF' in quals:
        quals['ZF'].covers.add(quals['GF'])

    # G26.3 Untersuchungstyp
    from apps.qualifications.models import MedicalExamType
    MedicalExamType.objects.create(
        code='G26.3',
        name='Atemschutz-Tauglichkeit',
        validity_months=36,
        related_qualification=quals.get('AGT')
    )


def create_default_positions():
    """Erstellt Standard-Positionen für Fahrzeuge"""
    positions_data = [
        ('GF', 'Gruppenführer/Fahrzeugführer', 1),
        ('MA', 'Maschinist', 2),
        ('ME', 'Melder', 3),
        ('ATF', 'Angriffstruppführer', 4),
        ('ATM', 'Angriffstruppmann', 5),
        ('WTF', 'Wassertruppführer', 6),
        ('WTM', 'Wassertruppmann', 7),
        ('STF', 'Schlauchtruppführer', 8),
        ('STM', 'Schlauchtruppmann', 9),
    ]

    for short_name, name, order in positions_data:
        Position.objects.create(
            short_name=short_name,
            name=name,
            order=order
        )


def create_default_duty_types():
    """Erstellt Standard-Diensttypen"""
    duty_types = [
        ('Dienstabend', '#3B82F6'),
        ('Übung', '#10B981'),
        ('Sonderdienst', '#F59E0B'),
        ('Einsatz', '#EF4444'),
        ('Lehrgang', '#8B5CF6'),
    ]

    for name, color in duty_types:
        DutyType.objects.create(name=name, color=color)


@login_required
def profile(request):
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.email = request.POST.get('email', '')
        user.phone = request.POST.get('phone', '')

        # Passwort ändern
        new_password = request.POST.get('new_password', '')
        new_password_confirm = request.POST.get('new_password_confirm', '')
        password_changed = False

        if new_password:
            if len(new_password) < 8:
                messages.error(request, 'Das Passwort muss mindestens 8 Zeichen lang sein.')
            elif new_password != new_password_confirm:
                messages.error(request, 'Die Passwörter stimmen nicht überein.')
            else:
                user.set_password(new_password)
                password_changed = True

        user.save()

        if password_changed:
            messages.success(request, 'Passwort wurde geändert. Bitte melden Sie sich erneut an.')
            return redirect('login')
        else:
            messages.success(request, 'Profil wurde aktualisiert.')
        return redirect('profile')

    return render(request, 'core/profile.html')


# ============ Admin Views ============

@login_required
@admin_required
def admin_users(request):
    """Benutzerverwaltung"""
    users = User.objects.all().order_by('username')
    return render(request, 'core/admin/users.html', {'users': users})


@login_required
@admin_required
def admin_user_edit(request, user_id=None):
    """Benutzer bearbeiten oder erstellen"""
    if user_id:
        user_obj = get_object_or_404(User, id=user_id)
    else:
        user_obj = None

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        role = request.POST.get('role', 'member')
        is_active = request.POST.get('is_active') == 'on'
        password = request.POST.get('password', '')

        if not username:
            messages.error(request, 'Benutzername ist erforderlich.')
        elif not user_obj and User.objects.filter(username=username).exists():
            messages.error(request, 'Dieser Benutzername ist bereits vergeben.')
        else:
            if user_obj:
                user_obj.username = username
                user_obj.email = email
                user_obj.first_name = first_name
                user_obj.last_name = last_name
                user_obj.role = role
                user_obj.is_active = is_active
                if password:
                    user_obj.set_password(password)
                user_obj.save()
                messages.success(request, 'Benutzer wurde aktualisiert.')
            else:
                if not password:
                    messages.error(request, 'Passwort ist für neue Benutzer erforderlich.')
                else:
                    user_obj = User.objects.create_user(
                        username=username,
                        email=email,
                        password=password,
                        first_name=first_name,
                        last_name=last_name,
                        role=role,
                        is_active=is_active
                    )
                    messages.success(request, 'Benutzer wurde erstellt.')
            return redirect('admin_users')

    context = {
        'user_obj': user_obj,
        'roles': User.Role.choices,
    }
    return render(request, 'core/admin/user_form.html', context)


@login_required
@admin_required
def admin_settings(request):
    """Feuerwehr-Einstellungen"""
    settings = Settings.get_instance()

    if request.method == 'POST':
        settings.name = request.POST.get('name', settings.name)
        settings.short_name = request.POST.get('short_name', settings.short_name)
        settings.city = request.POST.get('city', '')
        settings.save()
        messages.success(request, 'Einstellungen wurden gespeichert.')
        return redirect('admin_settings')

    return render(request, 'core/admin/settings.html', {'settings': settings})
