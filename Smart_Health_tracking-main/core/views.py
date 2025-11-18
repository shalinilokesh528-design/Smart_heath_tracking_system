from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Avg, Count, Max
from datetime import timedelta
from .forms import (
    UnifiedRegisterForm,
    PatientLookupForm,
    HealthLogForm,
    PatientVisitForm,
    PatientTaskForm,
    TherapistFeedbackForm,
    TherapistNotesForm,
    ExerciseVideoForm
)
from .forms import DoctorVisitForm
from .forms import AppointmentForm
from .models import Appointment

from django.utils import timezone
from django.db.models import Avg, Count, Max
from datetime import timedelta
from .models import User, HealthLog, PatientVisit, PatientTask, SOSAlert, ExerciseVideo
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate, login as auth_login
import logging

logger = logging.getLogger(__name__)

# 🔹 Register View (hide navbar)
def unified_register(request):
    if request.method == 'POST':
        form = UnifiedRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            if user.role == 'patient':
                return redirect('patient_home')
            elif user.role == 'doctor':
                return redirect('doctor_profile')
            elif user.role == 'therapist':
                return redirect('therapist_profile')
    else:
        form = UnifiedRegisterForm()
    return render(request, 'core/register.html', {'form': form, 'hide_nav': True})

# 🔹 Login View (hide navbar)
def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            if user.role == 'patient':
                return redirect('patient_home')
            elif user.role == 'doctor':
                return redirect('doctor_profile')
            elif user.role == 'therapist':
                return redirect('therapist_profile')
    else:
        form = AuthenticationForm()
    return render(request, 'core/login.html', {'form': form, 'hide_nav': True})

# 🔹 Patient Home — Add Daily Task
from .models import Appointment

@login_required
def patient_home(request):
    if request.user.role != 'patient':
        messages.error(request, "Access denied.")
        return redirect('login')

    active_task = PatientTask.objects.filter(patient=request.user, status='in_progress').first()
    task_form = PatientTaskForm(request.POST or None)
    appointment_form = AppointmentForm()
    latest_appointment = Appointment.objects.filter(patient=request.user).order_by('-created_at').first()

    if request.method == 'POST':
        if 'task_type' in request.POST:
            task_form = PatientTaskForm(request.POST)
            if task_form.is_valid():
                task = task_form.save(commit=False)
                task.patient = request.user
                task.status = 'in_progress'
                task.started_at = timezone.now()
                task.save()
                messages.success(request, "Task started successfully.")
                return redirect('patient_home')
        else:
            appointment_form = AppointmentForm(request.POST)
            if appointment_form.is_valid():
                appointment = appointment_form.save(commit=False)
                appointment.patient = request.user
                appointment.status = 'pending'
                appointment.save()
                messages.success(request, "Appointment request submitted.")
                return redirect('patient_home')

    return render(request, 'core/patient_home.html', {
        'user': request.user,
        'form': task_form,
        'appointment_form': appointment_form,
        'active_task': active_task,
        'latest_appointment': latest_appointment,
        'now': timezone.now()
    })

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from core.models import PatientTask,  MoodLog, ImprovementScore
from core.forms import PatientProfileForm
from datetime import date
def calculate_age(dob):
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


@login_required
def patient_profile(request):
    # 🔐 Ensure only patients can access this view
    if request.user.role != 'patient':
        messages.error(request, "Access denied.")
        return redirect('login')

    # ✅ Fetch completed tasks and active task
    completed_tasks = PatientTask.objects.filter(
        patient=request.user,
        status='completed'
    ).order_by('-completed_at')

    active_task = PatientTask.objects.filter(
        patient=request.user,
        status='in_progress'
    ).first()

    # 🧠 Calculate age if DOB is present
    age = calculate_age(request.user.date_of_birth) if request.user.date_of_birth else None

    # 📊 Weekly progress data
    progress_data = get_weekly_progress(request.user)

    # 🎨 Determine mood color based on latest mood
    latest_mood = MoodLog.objects.filter(patient=request.user).order_by('-logged_at').first()
    MOOD_COLOR_MAP = {
        'happy': '#4caf50',     # Green
        'neutral': '#9e9e9e',   # Gray
        'sad': '#f44336',       # Red
        'anxious': '#3f51b5',   # Indigo
        'excited': '#ff9800',   # Orange
        'tired': '#795548'      # Brown
    }
    mood_color = MOOD_COLOR_MAP.get(latest_mood.mood, '#2196f3') if latest_mood else '#2196f3'

    # 📋 Handle profile form
    if request.method == 'POST':
        form = PatientProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect(request.path)
        else:
            messages.error(request, "Please correct the errors below.")
            print(form.errors)
    else:
        form = PatientProfileForm(instance=request.user)

    # 🎯 Render profile page
    context = {
        'form': form,
        'unique_id': request.user.unique_id,
        'age': age,
        'tasks': completed_tasks,
        'active_task': active_task,
        'progress_data': progress_data,
        'mood_color': mood_color,
    }
    return render(request, 'core/patient_profile.html', context)
from core.forms import DoctorProfileForm
@login_required
def doctor_profile(request):
    # 🔐 Ensure only doctors can access this view
    if request.user.role != 'doctor':
        messages.error(request, "Access denied.")
        return redirect('login')

    # 📝 Handle form submission
    if request.method == 'POST':
        form = DoctorProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('doctor_profile')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = DoctorProfileForm(instance=request.user)

    # 🧠 Render the profile page
    context = {
        'form': form,
        'user': request.user,
    }
    return render(request, 'core/doctor_profile.html', context)

# 🔹 Therapist Profile
@login_required
def therapist_profile(request):
    if request.user.role != 'therapist':
        messages.error(request, "Access denied.")
        return redirect('login')

    if request.method == 'POST':
        form = DoctorProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            user = form.save(commit=False)
            if form.cleaned_data.get('delete_photo') and user.profile_photo:
                user.profile_photo.delete(save=False)
                user.profile_photo = None
            user.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('therapist_profile')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = DoctorProfileForm(instance=request.user)

    return render(request, 'core/therapist_profile.html', {'form': form})

# 🔹 Lookup Patient — Redirect to Profile
@login_required
def lookup_patient(request):
    if request.user.role not in ['doctor', 'therapist']:
        messages.error(request, "Access denied.")
        return redirect('login')

    form = PatientLookupForm(request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            patient_id = form.cleaned_data['patient_id']
            return redirect('view_patient_profile', unique_id=patient_id)
        else:
            messages.error(request, "Invalid input. Please enter a valid Patient ID.")

    return render(request, 'core/lookup_patient.html', {'form': form})

@login_required
def view_patient_profile(request, unique_id):
    # 🔐 Role-based access control
    if request.user.role not in ['doctor', 'therapist']:
        messages.error(request, "Access denied.")
        return redirect('login')

    # 🔍 Fetch patient and related data
    patient = get_object_or_404(User, unique_id=unique_id, role='patient')
    tasks = PatientTask.objects.filter(patient=patient).order_by('-completed_at')
    visits = PatientVisit.objects.filter(patient=patient).order_by('-visit_date')
    visit_records = VisitRecord.objects.filter(patient=patient).order_by('visit_date')

    # 📝 Therapist Notes Forms (one per visit)
    notes_forms = {visit.id: TherapistNotesForm(instance=visit) for visit in visits}

    # 📊 Task Summary Stats (only for completed tasks)
    completed_tasks = tasks.filter(status='completed')
    task_stats = completed_tasks.aggregate(
        total=Count('id'),
        avg_duration=Avg('duration_minutes'),
        last_completed=Max('completed_at')
    )

    # 🚨 Therapist Alerts
    long_tasks = tasks.filter(
        status='in_progress',
        started_at__lt=timezone.now() - timedelta(minutes=60)
    )

    missed_tasks = tasks.filter(
        status='pending',
        started_at__isnull=True
    )

    # 📈 Improvement Chart Data
    chart_dates = [v.visit_date.strftime('%d %b') for v in visit_records]
    chart_scores = [v.improvement_score for v in visit_records]

    # 🧾 Render profile page
    return render(request, 'core/view_patient_profile.html', {
        'patient': patient,
        'tasks': tasks,
        'visits': visits,
        'visit_records': visit_records,
        'notes_forms': notes_forms,
        'task_stats': task_stats,
        'long_tasks': long_tasks,
        'missed_tasks': missed_tasks,
        'chart_dates': chart_dates,
        'chart_scores': chart_scores,
    })


# 🔹 Visit Details (for patient and therapist)
@login_required
def visit_details(request):
    visits = PatientVisit.objects.all() if request.user.role == 'therapist' else PatientVisit.objects.filter(patient=request.user)
    form = PatientVisitForm()
    if request.method == 'POST' and request.user.role == 'patient':
        form = PatientVisitForm(request.POST, request.FILES)
        if form.is_valid():
            visit = form.save(commit=False)
            visit.patient = request.user
            visit.save()
            messages.success(request, "Visit details submitted.")
            return redirect('visit_details')
    return render(request, 'core/details.html', {'form': form, 'visits': visits})

# 🔹 Health Log Submission (optional legacy)
@login_required
def submit_health_log(request):
    if request.user.role != 'patient':
        messages.error(request, "Access denied.")
        return redirect('login')

    form = HealthLogForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        log = form.save(commit=False)
        log.patient = request.user
        log.save()
        messages.success(request, "Health log submitted.")
        return redirect('submit_health_log')

    logs = HealthLog.objects.filter(patient=request.user).order_by('-date')
    return render(request, 'core/submit_health_log.html', {'form': form, 'logs': logs})


@login_required
def therapist_dashboard(request):
    if request.user.role != 'therapist':
        messages.error(request, "Access denied.")
        return redirect('login')

    patients = User.objects.filter(role='patient')
    # 🚨 Active SOS Alerts
    active_sos_alerts = SOSAlert.objects.filter(status='active').order_by('-created_at')
    acknowledged_sos_alerts = SOSAlert.objects.filter(status='acknowledged').order_by('-created_at')[:10]
    
    return render(request, 'core/therapist_dashboard.html', {
        'patients': patients,
        'active_sos_alerts': active_sos_alerts,
        'acknowledged_sos_alerts': acknowledged_sos_alerts,
    })


@login_required
def add_feedback(request, task_id):
    if request.user.role != 'therapist':
        messages.error(request, "Access denied.")
        return redirect('login')

    task = PatientTask.objects.get(id=task_id)
    form = TherapistFeedbackForm(request.POST or None, instance=task)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Feedback added successfully.")
        return redirect('view_patient_profile', unique_id=task.patient.unique_id)

    return render(request, 'core/add_feedback.html', {'form': form, 'task': task})


@login_required
def add_therapist_notes_inline(request, visit_id):
    if request.user.role != 'therapist':
        messages.error(request, "Access denied.")
        return redirect('login')

    visit = PatientVisit.objects.get(id=visit_id)
    form = TherapistNotesForm(request.POST, instance=visit)

    if form.is_valid():
        form.save()
        messages.success(request, "Therapist notes updated.")
    else:
        messages.error(request, "Failed to update notes.")

    return redirect('view_patient_profile', unique_id=visit.patient.unique_id)

from django.utils import timezone

# 🔹 Start Task
@login_required
def start_task(request):
    if request.user.role != 'patient':
        return redirect('login')

    if request.method == 'POST':
        form = PatientTaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.patient = request.user
            task.started_at = timezone.now()
            task.status = 'in_progress'

            # ✅ Auto-fill task_name from task_type
            task.task_name = dict(PatientTask.TASK_TYPE_CHOICES).get(task.task_type, "Unknown Task")

            task.save()
            messages.success(request, f"Task '{task.task_name}' started.")
            return redirect('patient_home')
    else:
        form = PatientTaskForm()

    active_task = PatientTask.objects.filter(patient=request.user, status='in_progress').first()
    return render(request, 'core/patient_home.html', {
        'form': form,
        'active_task': active_task,
        'now': timezone.now()
    })

# 🔹 Complete Task
@login_required
def complete_task(request, task_id):
    if request.user.role != 'patient':
        messages.error(request, "Access denied.")
        return redirect('login')

    task = get_object_or_404(PatientTask, id=task_id, patient=request.user)

    if task.status == 'in_progress':
        now = timezone.now()

        if task.started_at:
            duration = (now - task.started_at).total_seconds() / 60
            task.duration_minutes = max(1, round(duration))
        else:
            task.duration_minutes = 1  # fallback if start time is missing

        task.completed_at = now
        task.status = 'completed'
        task.save()

        messages.success(request, f"Task '{task.task_name}' completed in {task.duration_minutes} minutes.")
    else:
        messages.warning(request, "Task is not currently in progress or already completed.")

    return redirect('patient_home') 


PatientLookupForm
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from core.models import Appointment, PatientVisit, VisitRecord, User
from core.forms import PatientLookupForm
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from core.models import Appointment, PatientVisit, VisitRecord
from core.forms import PatientLookupForm
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from core.models import Appointment, PatientVisit, VisitRecord
from core.forms import PatientLookupForm

@login_required
def doctor_dashboard(request):
    # 🔐 Role check
    if request.user.role != 'doctor':
        messages.error(request, "Access denied.")
        return redirect('login')

    # 🔍 Patient lookup form
    lookup_form = PatientLookupForm()
    if request.method == 'POST':
        lookup_form = PatientLookupForm(request.POST)
        if lookup_form.is_valid():
            patient_id = lookup_form.cleaned_data['patient_id']
            return redirect('patient_detail', patient_id=patient_id)

    # 📅 Appointments grouped by status
    pending_appointments = Appointment.objects.filter(
        doctor=request.user,
        status='pending'
    ).order_by('date', 'time')

    confirmed_appointments = Appointment.objects.filter(
        doctor=request.user,
        status='confirmed'
    ).order_by('date', 'time')

    cancelled_appointments = Appointment.objects.filter(
        doctor=request.user,
        status='cancelled'
    ).order_by('date', 'time')

    completed_appointments = Appointment.objects.filter(
        doctor=request.user,
        status='completed'
    ).order_by('-date', '-time')

    # 🧾 Legacy PatientVisit records (optional)
    recent_visits = PatientVisit.objects.filter(
        doctor=request.user
    ).order_by('-visit_date')[:10]

    # 🩺 VisitRecords for update and tracking
    visit_records = VisitRecord.objects.filter(
        doctor=request.user
    ).order_by('-visit_date')

    # 🚨 Active SOS Alerts
    active_sos_alerts = SOSAlert.objects.filter(status='active').order_by('-created_at')
    acknowledged_sos_alerts = SOSAlert.objects.filter(status='acknowledged').order_by('-created_at')[:10]

    # 🧠 Render dashboard
    return render(request, 'core/doctor_dashboard.html', {
        'user': request.user,
        'lookup_form': lookup_form,
        'pending_appointments': pending_appointments,
        'confirmed_appointments': confirmed_appointments,
        'cancelled_appointments': cancelled_appointments,
        'completed_appointments': completed_appointments,
        'recent_visits': recent_visits,
        'visit_records': visit_records,
        'active_sos_alerts': active_sos_alerts,
        'acknowledged_sos_alerts': acknowledged_sos_alerts,
    })

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from core.models import Appointment

@login_required
def confirm_appointment(request, appointment_id):
    # 🔐 Ensure only doctors can confirm appointments
    if request.user.role != 'doctor':
        messages.error(request, "Access denied.")
        return redirect('doctor_dashboard')

    # 🔍 Fetch the appointment
    appointment = get_object_or_404(Appointment, id=appointment_id, doctor=request.user)

    # ✅ Update status to confirmed
    if appointment.status == 'pending':
        appointment.status = 'confirmed'
        appointment.save()
        messages.success(request, f"Appointment with {appointment.patient.get_full_name()} confirmed.")
    else:
        messages.warning(request, "This appointment is not pending or has already been processed.")

    return redirect('doctor_dashboard')
@login_required
def cancel_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id, doctor=request.user)
    appointment.status = 'cancelled'
    appointment.save()
    messages.warning(request, "Appointment cancelled.")
    return redirect('doctor_dashboard')



@login_required
def log_visit_by_id(request):
    if request.user.role != 'doctor':
        return redirect('login')

    patient_id = request.GET.get('patient_id')
    patient = None
    form = None

    if patient_id:
        patient = User.objects.filter(unique_id=patient_id, role='patient').first()
        if patient:
            if request.method == 'POST':
                form = DoctorVisitForm(request.POST, request.FILES)
                if form.is_valid():
                    visit = form.save(commit=False)
                    visit.patient = patient
                    visit.doctor = request.user
                    visit.save()
                    messages.success(request, "Visit record saved successfully.")
                    return redirect('doctor_dashboard')
            else:
                form = DoctorVisitForm()

    return render(request, 'core/log_visit.html', {'form': form, 'patient': patient})

@login_required
def book_appointment(request):
    if request.user.role != 'patient':
        return redirect('login')

    if request.method == 'POST':
        form = AppointmentForm(request.POST)
        if form.is_valid():
            appointment = form.save(commit=False)
            appointment.patient = request.user
            appointment.status = 'pending'
            appointment.save()
            messages.success(request, "Appointment request submitted.")
            return redirect('patient_dashboard')
    else:
        form = AppointmentForm()

    return render(request, 'core/book_appointment.html', {'form': form})

@login_required
def confirm_appointment(request, appointment_id):
    if request.user.role != 'doctor':
        return redirect('login')

    appointment = get_object_or_404(Appointment, id=appointment_id, doctor=request.user)

    if request.method == 'POST':
        appointment.status = 'confirmed'
        appointment.save()
        messages.success(request, "Appointment confirmed.")
        return redirect('doctor_dashboard')

    return render(request, 'core/confirm_appointment.html', {'appointment': appointment})

from django.http import JsonResponse
from .models import Hospital

def load_hospitals(request):
    location_id = request.GET.get('location')
    hospitals = Hospital.objects.filter(location_id=location_id).values('id', 'name')
    return JsonResponse(list(hospitals), safe=False)

# views.py
from django.shortcuts import get_object_or_404, redirect, render
from .models import VisitRecord
from .forms import VisitUpdateForm
from django.contrib.auth.decorators import login_required


@login_required
def update_visit_record(request, visit_id):
    # Ensure the visit belongs to the logged-in doctor
    visit = get_object_or_404(VisitRecord, id=visit_id, doctor=request.user)

    if request.method == 'POST':
        form = VisitUpdateForm(request.POST, instance=visit)
        if form.is_valid():
            form.save()
            messages.success(request, f"Visit for {visit.patient.get_full_name()} updated successfully.")
            return redirect('doctor_dashboard')
        else:
            messages.error(request, "There was an error updating the visit. Please check the form.")
    else:
        form = VisitUpdateForm(instance=visit)

    return render(request, 'core/update_visit.html', {
        'form': form,
        'visit': visit
    })
from django.shortcuts import render
from .models import VisitRecord

def patient_progress_chart(request, patient_id):
    visits = VisitRecord.objects.filter(patient_id=patient_id).order_by('visit_date')
    dates = [v.visit_date.strftime('%d %b') for v in visits]  # e.g. "08 Oct"
    scores = [v.improvement_score for v in visits]            # e.g. [20, 40, 60]
    return render(request, 'core/progress_chart.html', {
        'dates': dates,
        'scores': scores,
        'patient': visits[0].patient if visits else None
    })


from core.models import Appointment, VisitRecord
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone


@login_required
def log_visit_by_id(request, appointment_id):
    # 🔐 Ensure only doctors can access
    if request.user.role != 'doctor':
        messages.error(request, "Access denied.")
        return redirect('doctor_dashboard')

    # 🔍 Fetch the appointment
    appointment = get_object_or_404(Appointment, id=appointment_id, doctor=request.user)

    # 🚫 Prevent duplicate VisitRecord for same appointment date
    visit_exists = VisitRecord.objects.filter(
        doctor=request.user,
        patient=appointment.patient,
        visit_date=appointment.date
    ).exists()

    if visit_exists:
        messages.warning(request, "Visit already logged for this appointment.")
        return redirect('doctor_dashboard')

    # ✅ Create VisitRecord
    visit = VisitRecord.objects.create(
        doctor=request.user,
        patient=appointment.patient,
        visit_date=appointment.date,
        hospital_name=appointment.hospital.name,
        doctor_name=request.user.get_full_name(),
        current_status='pending',
        improvement_score=0,
        doctor_notes='Visit logged. Awaiting update.'
    )

    # ✅ Mark appointment as completed
    appointment.status = 'completed'
    appointment.save()

    # ✅ Success message
    messages.success(
        request,
        f"Visit for {appointment.patient.get_full_name()} recorded successfully. Appointment marked as completed."
    )

    # ✅ Redirect to dashboard
    return redirect('doctor_dashboard')



@login_required
def delete_profile_photo(request):
    user = request.user

    # 🧹 Delete profile photo if it exists
    if user.profile_photo:
        user.profile_photo.delete(save=False)
        user.profile_photo = None
        user.save()
        messages.success(request, "Profile photo deleted successfully.")
    else:
        messages.info(request, "No profile photo to delete.")

    # 🔁 Redirect based on role
    if user.role == 'patient':
        return redirect('patient_profile')
    elif user.role == 'doctor':
        return redirect('doctor_profile')
    elif user.role == 'therapist':
        return redirect('therapist_profile')
    else:
        messages.error(request, "Unknown role. Redirecting to login.")
        return redirect('login')
    
from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Avg
from core.models import MoodLog, ImprovementScore, PatientTask

def get_weekly_progress(user):
    today = timezone.now()
    week_ago = today - timedelta(days=7)

    task_count = PatientTask.objects.filter(
        patient=user,
        completed_at__gte=week_ago,
        status='completed'
    ).count()

    mood_summary = MoodLog.objects.filter(
        patient=user,
        logged_at__gte=week_ago
    ).values('mood').annotate(count=Count('mood'))

    avg_score = ImprovementScore.objects.filter(
        patient=user,
        recorded_at__gte=week_ago
    ).aggregate(avg=Avg('score'))['avg'] or 0

    return {
        'task_count': task_count,
        'mood_summary': mood_summary,
        'avg_score': round(avg_score, 1),
        'ai_summary': f"You’ve completed {task_count} tasks and improved your score to {round(avg_score)} this week."
    }


from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from core.models import MoodLog

# Optional: define mood-color mapping for future use
MOOD_COLOR_MAP = {
    'happy': '#4caf50',     # Green
    'neutral': '#9e9e9e',   # Gray
    'sad': '#f44336',       # Red
    'anxious': '#3f51b5',   # Indigo
    'excited': '#ff9800',   # Orange
    'tired': '#795548'      # Brown
}

@login_required
def log_mood(request):
    if request.method == 'POST':
        mood = request.POST.get('mood')
        if mood:
            MoodLog.objects.create(patient=request.user, mood=mood)
    return redirect('patient_profile')

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from core.models import Message, User

@login_required
def message_box(request):
    role = request.GET.get('role')
    selected_user_id = request.GET.get('user')

    # Filter users by role
    users = User.objects.filter(role=role).exclude(id=request.user.id) if role else []

    # Selected chat partner
    selected_user = User.objects.filter(id=selected_user_id).first()

    # Fetch messages
    messages = []
    if selected_user:
        messages = Message.objects.filter(
            sender__in=[request.user, selected_user],
            receiver__in=[request.user, selected_user],
            is_deleted=False
        ).order_by('timestamp')

    return render(request, 'core/message_box.html', {
        'roles': ['doctor', 'therapist', 'patient'],
        'selected_role': role,
        'users': users,
        'selected_user': selected_user,
        'messages': messages
    })

@login_required
def send_message(request):
    if request.method == 'POST':
        receiver_id = request.POST.get('receiver_id')
        content = request.POST.get('content')
        receiver = get_object_or_404(User, id=receiver_id)
        Message.objects.create(sender=request.user, receiver=receiver, content=content)
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'})

@login_required
def delete_message(request, message_id):
    message = get_object_or_404(Message, id=message_id, sender=request.user)
    message.is_deleted = True
    message.save()
    return JsonResponse({'status': 'deleted'})

# 🔹 Emergency SOS System
@login_required
def send_sos_alert(request):
    """Send emergency SOS alert to doctors and therapists"""
    if request.user.role != 'patient':
        messages.error(request, "Access denied.")
        return redirect('login')

    if request.method == 'POST':
        message = request.POST.get('message', '')
        
        # Create SOS alert
        sos_alert = SOSAlert.objects.create(
            patient=request.user,
            message=message if message else None,
            status='active'
        )
        
        messages.success(request, "🚨 Emergency SOS alert sent to all doctors and therapists!")
        return redirect('patient_home')
    
    return redirect('patient_home')

@login_required
def acknowledge_sos_alert(request, alert_id):
    """Acknowledge an SOS alert by doctor or therapist"""
    if request.user.role not in ['doctor', 'therapist']:
        messages.error(request, "Access denied.")
        return redirect('login')

    sos_alert = get_object_or_404(SOSAlert, id=alert_id)
    
    # Update acknowledgment based on role
    if request.user.role == 'doctor':
        sos_alert.acknowledged_by_doctor = True
    elif request.user.role == 'therapist':
        sos_alert.acknowledged_by_therapist = True
    
    # If both have acknowledged, mark as acknowledged
    if sos_alert.acknowledged_by_doctor and sos_alert.acknowledged_by_therapist:
        sos_alert.status = 'acknowledged'
        sos_alert.acknowledged_at = timezone.now()
    elif not sos_alert.acknowledged_at:
        sos_alert.acknowledged_at = timezone.now()
    
    sos_alert.save()
    
    messages.success(request, f"SOS alert from {sos_alert.patient.get_full_name()} acknowledged.")
    
    # Redirect based on role
    if request.user.role == 'doctor':
        return redirect('doctor_dashboard')
    else:
        return redirect('therapist_dashboard')

@login_required
def resolve_sos_alert(request, alert_id):
    """Resolve an SOS alert"""
    if request.user.role not in ['doctor', 'therapist']:
        messages.error(request, "Access denied.")
        return redirect('login')

    sos_alert = get_object_or_404(SOSAlert, id=alert_id)
    sos_alert.status = 'resolved'
    sos_alert.resolved_at = timezone.now()
    sos_alert.save()
    
    messages.success(request, f"SOS alert from {sos_alert.patient.get_full_name()} resolved.")
    
    # Redirect based on role
    if request.user.role == 'doctor':
        return redirect('doctor_dashboard')
    else:
        return redirect('therapist_dashboard')

# 🔹 Exercise Video System
@login_required
def upload_exercise_video(request):
    """Allow therapists to upload exercise videos"""
    if request.user.role != 'therapist':
        messages.error(request, "Access denied. Only therapists can upload videos.")
        return redirect('login')

    if request.method == 'POST':
        form = ExerciseVideoForm(request.POST, request.FILES)
        if form.is_valid():
            video = form.save(commit=False)
            video.therapist = request.user
            video.save()
            messages.success(request, f"Video '{video.title}' uploaded successfully!")
            return redirect('therapist_videos')
    else:
        form = ExerciseVideoForm()

    return render(request, 'core/upload_video.html', {'form': form})

@login_required
def therapist_videos(request):
    """List all videos uploaded by the therapist"""
    if request.user.role != 'therapist':
        messages.error(request, "Access denied.")
        return redirect('login')

    videos = ExerciseVideo.objects.filter(therapist=request.user).order_by('-created_at')
    return render(request, 'core/therapist_videos.html', {'videos': videos})

@login_required
def view_exercise_videos(request):
    """Display all active exercise videos to patients"""
    if request.user.role != 'patient':
        messages.error(request, "Access denied.")
        return redirect('login')

    # Get filter parameters
    exercise_type = request.GET.get('exercise_type', '')
    difficulty = request.GET.get('difficulty', '')
    
    videos = ExerciseVideo.objects.filter(is_active=True)
    
    if exercise_type:
        videos = videos.filter(exercise_type=exercise_type)
    if difficulty:
        videos = videos.filter(difficulty_level=difficulty)
    
    videos = videos.order_by('-created_at')
    
    # Get unique exercise types and difficulty levels for filter
    exercise_types = ExerciseVideo.EXERCISE_TYPE_CHOICES
    difficulty_levels = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ]
    
    return render(request, 'core/view_videos.html', {
        'videos': videos,
        'exercise_types': exercise_types,
        'difficulty_levels': difficulty_levels,
        'selected_type': exercise_type,
        'selected_difficulty': difficulty,
    })

@login_required
def watch_video(request, video_id):
    """Watch a specific exercise video"""
    if request.user.role != 'patient':
        messages.error(request, "Access denied.")
        return redirect('login')

    video = get_object_or_404(ExerciseVideo, id=video_id, is_active=True)
    
    # Increment view count
    video.increment_views()
    
    # Get related videos
    related_videos = ExerciseVideo.objects.filter(
        is_active=True,
        exercise_type=video.exercise_type
    ).exclude(id=video_id).order_by('-created_at')[:5]
    
    return render(request, 'core/watch_video.html', {
        'video': video,
        'related_videos': related_videos,
    })

@login_required
def delete_video(request, video_id):
    """Allow therapists to delete their uploaded videos"""
    if request.user.role != 'therapist':
        messages.error(request, "Access denied.")
        return redirect('login')

    video = get_object_or_404(ExerciseVideo, id=video_id, therapist=request.user)
    
    if request.method == 'POST':
        video_title = video.title
        video.video_file.delete(save=False)
        if video.thumbnail:
            video.thumbnail.delete(save=False)
        video.delete()
        messages.success(request, f"Video '{video_title}' deleted successfully.")
        return redirect('therapist_videos')
    
    return render(request, 'core/delete_video.html', {'video': video})
