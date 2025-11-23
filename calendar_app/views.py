from datetime import timedelta
from django.db.models import Q
from django.utils.timezone import localdate
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from events.models import Event
from .forms import RegisterForm, LoginForm
from .models import CustomUser

# Create your views here.
def welcome_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    return render(request, 'welcome.html')


@login_required
def home_view(request):
    week_offset = int(request.GET.get("week", 0))

    today = localdate()
    start_of_week = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
    end_of_week = start_of_week + timedelta(days=7)

    prev_week = week_offset - 1
    next_week = week_offset + 1

    events = Event.objects.filter(
        Q(created_by=request.user, invitations__isnull=True) |
        Q(created_by=request.user, invitations__status='accepted') |
        Q(invitations__user=request.user, invitations__status='accepted')
    ).filter(
        start_time__date__gte=start_of_week,
        start_time__date__lt=end_of_week,
    ).distinct()

    days = []
    for i in range(7):
        day_date = start_of_week + timedelta(days=i)
        day_events = events.filter(start_time__date=day_date)

        formatted_events = []
        for e in day_events:
            start_minutes = e.start_time.hour * 60 + e.start_time.minute
            end_minutes = e.end_time.hour * 60 + e.end_time.minute

            start_offset = (start_minutes / 10) * 10
            duration_height = ((end_minutes - start_minutes) / 10) * 10

            formatted_events.append({
                "id": e.id,
                "title": e.title,
                "tag": e.tag,
                "start_offset": start_offset,
                "duration_height": duration_height,
            })

        days.append({
            "date": day_date,
            "weekday": day_date.strftime("%A"),
            "events": formatted_events,
        })

    return render(request, "home.html", {
        "days": days,
        "week_start": start_of_week,
        "week_end": end_of_week - timedelta(days=1),
        "prev_week": prev_week,
        "next_week": next_week,
        "hours": range(0, 24),
    })


def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Account created successfully!")
            return redirect('home')
        else:
            messages.error(request, "Account not created due to errors!")
    else:
        form = RegisterForm()
    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')

            try:
                user_obj = CustomUser.objects.get(email=username)
                username = user_obj.username
            except CustomUser.DoesNotExist:
                pass

            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('home')

    else:
        form = LoginForm()
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')