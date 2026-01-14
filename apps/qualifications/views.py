from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from apps.core.views import leader_required, admin_required
from .models import Qualification, QualificationCategory, MedicalExamType


@login_required
@leader_required
def qualification_list(request):
    """Qualifikationenliste"""
    categories = QualificationCategory.objects.all().prefetch_related('qualifications')

    context = {
        'categories': categories,
    }
    return render(request, 'qualifications/qualification_list.html', context)


@login_required
@admin_required
def qualification_edit(request, qualification_id=None):
    """Qualifikation erstellen oder bearbeiten"""
    if qualification_id:
        qualification = get_object_or_404(Qualification, id=qualification_id)
    else:
        qualification = None

    if request.method == 'POST':
        code = request.POST.get('code', '').strip()
        name = request.POST.get('name', '').strip()

        if not code or not name:
            messages.error(request, 'Kürzel und Bezeichnung sind erforderlich.')
        else:
            category_id = request.POST.get('category') or None

            if qualification:
                qualification.code = code
                qualification.name = name
                qualification.category_id = category_id
                qualification.description = request.POST.get('description', '')
                qualification.requires_exercises = request.POST.get('requires_exercises') == 'on'
                qualification.exercise_count = int(request.POST.get('exercise_count', 0)) or None
                qualification.order = int(request.POST.get('order', 0))
                qualification.is_active = request.POST.get('is_active') == 'on'
                qualification.save()
                messages.success(request, 'Qualifikation wurde aktualisiert.')
            else:
                qualification = Qualification.objects.create(
                    code=code,
                    name=name,
                    category_id=category_id,
                    description=request.POST.get('description', ''),
                    requires_exercises=request.POST.get('requires_exercises') == 'on',
                    exercise_count=int(request.POST.get('exercise_count', 0)) or None,
                    order=int(request.POST.get('order', 0)),
                    is_active=request.POST.get('is_active') == 'on'
                )
                messages.success(request, 'Qualifikation wurde erstellt.')
            return redirect('qualification_list')

    categories = QualificationCategory.objects.all()

    context = {
        'qualification': qualification,
        'categories': categories,
    }
    return render(request, 'qualifications/qualification_form.html', context)


@login_required
@admin_required
def qualification_delete(request, qualification_id):
    """Qualifikation löschen"""
    qualification = get_object_or_404(Qualification, id=qualification_id)

    if request.method == 'POST':
        name = qualification.name
        qualification.delete()
        messages.success(request, f'Qualifikation "{name}" wurde gelöscht.')
        return redirect('qualification_list')

    return render(request, 'qualifications/qualification_confirm_delete.html', {'qualification': qualification})


# ============ Kategorien ============

@login_required
@admin_required
def category_list(request):
    """Kategorien-Liste"""
    categories = QualificationCategory.objects.all()

    context = {
        'categories': categories,
    }
    return render(request, 'qualifications/category_list.html', context)


@login_required
@admin_required
def category_edit(request, category_id=None):
    """Kategorie erstellen oder bearbeiten"""
    if category_id:
        category = get_object_or_404(QualificationCategory, id=category_id)
    else:
        category = None

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()

        if not name:
            messages.error(request, 'Name ist erforderlich.')
        else:
            if category:
                category.name = name
                category.order = int(request.POST.get('order', 0))
                category.save()
                messages.success(request, 'Kategorie wurde aktualisiert.')
            else:
                category = QualificationCategory.objects.create(
                    name=name,
                    order=int(request.POST.get('order', 0))
                )
                messages.success(request, 'Kategorie wurde erstellt.')
            return redirect('category_list')

    context = {
        'category': category,
    }
    return render(request, 'qualifications/category_form.html', context)


# ============ Untersuchungstypen ============

@login_required
@admin_required
def exam_type_list(request):
    """Untersuchungstypen-Liste"""
    exam_types = MedicalExamType.objects.all().select_related('related_qualification')

    context = {
        'exam_types': exam_types,
    }
    return render(request, 'qualifications/exam_type_list.html', context)


@login_required
@admin_required
def exam_type_edit(request, exam_type_id=None):
    """Untersuchungstyp erstellen oder bearbeiten"""
    if exam_type_id:
        exam_type = get_object_or_404(MedicalExamType, id=exam_type_id)
    else:
        exam_type = None

    if request.method == 'POST':
        code = request.POST.get('code', '').strip()
        name = request.POST.get('name', '').strip()
        validity_months = request.POST.get('validity_months', '36')

        if not code or not name:
            messages.error(request, 'Kürzel und Bezeichnung sind erforderlich.')
        else:
            qualification_id = request.POST.get('related_qualification') or None

            if exam_type:
                exam_type.code = code
                exam_type.name = name
                exam_type.validity_months = int(validity_months)
                exam_type.related_qualification_id = qualification_id
                exam_type.save()
                messages.success(request, 'Untersuchungstyp wurde aktualisiert.')
            else:
                exam_type = MedicalExamType.objects.create(
                    code=code,
                    name=name,
                    validity_months=int(validity_months),
                    related_qualification_id=qualification_id
                )
                messages.success(request, 'Untersuchungstyp wurde erstellt.')
            return redirect('exam_type_list')

    qualifications = Qualification.objects.filter(is_active=True)

    context = {
        'exam_type': exam_type,
        'qualifications': qualifications,
    }
    return render(request, 'qualifications/exam_type_form.html', context)
