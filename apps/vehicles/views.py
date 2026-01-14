from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q

from apps.core.views import leader_required, admin_required
from .models import Vehicle, VehicleType, Position, VehiclePosition


@login_required
@leader_required
def vehicle_list(request):
    """Fahrzeugliste"""
    vehicles = Vehicle.objects.all().select_related('vehicle_type')

    # Filter
    active_filter = request.GET.get('active', '')
    type_filter = request.GET.get('type', '')

    if active_filter == 'active':
        vehicles = vehicles.filter(is_active=True)
    elif active_filter == 'inactive':
        vehicles = vehicles.filter(is_active=False)

    if type_filter:
        vehicles = vehicles.filter(vehicle_type_id=type_filter)

    vehicle_types = VehicleType.objects.all()

    context = {
        'vehicles': vehicles,
        'vehicle_types': vehicle_types,
        'current_active': active_filter,
        'current_type': type_filter,
    }
    return render(request, 'vehicles/vehicle_list.html', context)


@login_required
@leader_required
def vehicle_detail(request, vehicle_id):
    """Fahrzeug-Detailansicht"""
    vehicle = get_object_or_404(Vehicle, id=vehicle_id)

    # Positionen laden
    positions = vehicle.positions.select_related('position').prefetch_related(
        'required_qualifications', 'preferred_qualifications'
    ).order_by('seat_number')

    context = {
        'vehicle': vehicle,
        'positions': positions,
    }
    return render(request, 'vehicles/vehicle_detail.html', context)


@login_required
@admin_required
def vehicle_edit(request, vehicle_id=None):
    """Fahrzeug erstellen oder bearbeiten"""
    if vehicle_id:
        vehicle = get_object_or_404(Vehicle, id=vehicle_id)
    else:
        vehicle = None

    if request.method == 'POST':
        call_sign = request.POST.get('call_sign', '').strip()
        vehicle_type_id = request.POST.get('vehicle_type')

        if not call_sign or not vehicle_type_id:
            messages.error(request, 'Funkrufname und Fahrzeugtyp sind erforderlich.')
        else:
            if vehicle:
                vehicle.call_sign = call_sign
                vehicle.vehicle_type_id = vehicle_type_id
                vehicle.name = request.POST.get('name', '')
                vehicle.license_plate = request.POST.get('license_plate', '')
                vehicle.priority = int(request.POST.get('priority', 0))
                vehicle.notes = request.POST.get('notes', '')
                vehicle.is_active = request.POST.get('is_active') == 'on'
                vehicle.save()
                messages.success(request, 'Fahrzeug wurde aktualisiert.')
            else:
                vehicle = Vehicle.objects.create(
                    call_sign=call_sign,
                    vehicle_type_id=vehicle_type_id,
                    name=request.POST.get('name', ''),
                    license_plate=request.POST.get('license_plate', ''),
                    priority=int(request.POST.get('priority', 0)),
                    notes=request.POST.get('notes', ''),
                    is_active=request.POST.get('is_active') == 'on'
                )
                messages.success(request, 'Fahrzeug wurde erstellt.')
            return redirect('vehicle_detail', vehicle_id=vehicle.id)

    vehicle_types = VehicleType.objects.all()

    context = {
        'vehicle': vehicle,
        'vehicle_types': vehicle_types,
    }
    return render(request, 'vehicles/vehicle_form.html', context)


@login_required
@admin_required
def vehicle_delete(request, vehicle_id):
    """Fahrzeug löschen"""
    vehicle = get_object_or_404(Vehicle, id=vehicle_id)

    if request.method == 'POST':
        call_sign = vehicle.call_sign
        vehicle.delete()
        messages.success(request, f'Fahrzeug "{call_sign}" wurde gelöscht.')
        return redirect('vehicle_list')

    return render(request, 'vehicles/vehicle_confirm_delete.html', {'vehicle': vehicle})


# ============ Fahrzeugtypen ============

@login_required
@admin_required
def vehicle_type_list(request):
    """Fahrzeugtypen-Liste"""
    vehicle_types = VehicleType.objects.all()

    context = {
        'vehicle_types': vehicle_types,
    }
    return render(request, 'vehicles/vehicle_type_list.html', context)


@login_required
@admin_required
def vehicle_type_edit(request, type_id=None):
    """Fahrzeugtyp erstellen oder bearbeiten"""
    if type_id:
        vehicle_type = get_object_or_404(VehicleType, id=type_id)
    else:
        vehicle_type = None

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        short_name = request.POST.get('short_name', '').strip()
        crew_size = request.POST.get('crew_size', '').strip()

        if not name or not short_name or not crew_size:
            messages.error(request, 'Name, Kurzname und Besatzungsstärke sind erforderlich.')
        else:
            if vehicle_type:
                vehicle_type.name = name
                vehicle_type.short_name = short_name
                vehicle_type.crew_size = crew_size
                vehicle_type.description = request.POST.get('description', '')
                vehicle_type.order = int(request.POST.get('order', 0))
                vehicle_type.save()
                messages.success(request, 'Fahrzeugtyp wurde aktualisiert.')
            else:
                vehicle_type = VehicleType.objects.create(
                    name=name,
                    short_name=short_name,
                    crew_size=crew_size,
                    description=request.POST.get('description', ''),
                    order=int(request.POST.get('order', 0))
                )
                messages.success(request, 'Fahrzeugtyp wurde erstellt.')
            return redirect('vehicle_type_list')

    context = {
        'vehicle_type': vehicle_type,
    }
    return render(request, 'vehicles/vehicle_type_form.html', context)


@login_required
@admin_required
def vehicle_type_delete(request, type_id):
    """Fahrzeugtyp löschen"""
    vehicle_type = get_object_or_404(VehicleType, id=type_id)

    if request.method == 'POST':
        name = vehicle_type.name
        vehicle_type.delete()
        messages.success(request, f'Fahrzeugtyp "{name}" wurde gelöscht.')
        return redirect('vehicle_type_list')

    return render(request, 'vehicles/vehicle_type_confirm_delete.html', {'vehicle_type': vehicle_type})


# ============ Positionen ============

@login_required
@admin_required
def position_list(request):
    """Positionen-Liste"""
    positions = Position.objects.all()

    context = {
        'positions': positions,
    }
    return render(request, 'vehicles/position_list.html', context)


@login_required
@admin_required
def position_edit(request, position_id=None):
    """Position erstellen oder bearbeiten"""
    if position_id:
        position = get_object_or_404(Position, id=position_id)
    else:
        position = None

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        short_name = request.POST.get('short_name', '').strip()

        if not name or not short_name:
            messages.error(request, 'Name und Kurzname sind erforderlich.')
        else:
            if position:
                position.name = name
                position.short_name = short_name
                position.description = request.POST.get('description', '')
                position.order = int(request.POST.get('order', 0))
                position.save()
                messages.success(request, 'Position wurde aktualisiert.')
            else:
                position = Position.objects.create(
                    name=name,
                    short_name=short_name,
                    description=request.POST.get('description', ''),
                    order=int(request.POST.get('order', 0))
                )
                messages.success(request, 'Position wurde erstellt.')
            return redirect('position_list')

    context = {
        'position': position,
    }
    return render(request, 'vehicles/position_form.html', context)
