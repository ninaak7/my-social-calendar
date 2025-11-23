from datetime import timedelta
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.utils.timezone import localdate
from events.models import EventInvitation, Event
from friends.models import Friendship
from django.db.models import Q
from django.contrib.auth import get_user_model
from django.contrib import messages
from groups.models import Group

# Create your views here.
User = get_user_model()

@login_required
def friend_list(request):
    accepted_friendships = Friendship.objects.filter(
        (Q(from_user=request.user) | Q(to_user=request.user)),
        is_accepted=True
    )

    friends = []
    friend_ids = []

    for f in accepted_friendships:
        if f.from_user == request.user:
            friends.append(f.to_user)
            friend_ids.append(f.to_user.id)
        else:
            friends.append(f.from_user)
            friend_ids.append(f.from_user.id)

    received_requests = Friendship.objects.filter(to_user=request.user, is_accepted=False)

    return render(request, 'friends/friend_list.html', {
        'friends': friends,
        'received_requests': received_requests
    })


@login_required
def send_friend_request(request, user_id):
    to_user = get_object_or_404(User, id=user_id)

    if Friendship.objects.filter(from_user=request.user, to_user=to_user).exists() or \
            Friendship.objects.filter(from_user=to_user, to_user=request.user).exists():
        messages.warning(request, f"A request or friendship already exists with {to_user.username}.")

        return redirect('friend_list')

    Friendship.objects.create(from_user=request.user, to_user=to_user)
    messages.success(request, f"Friend request sent to {to_user.username}!")

    return redirect('friend_list')


@login_required
def accept_friend_request(request, friendship_id):
    friendship = get_object_or_404(Friendship, id=friendship_id, to_user=request.user, is_accepted=False)
    friendship.is_accepted = True
    friendship.save()

    messages.success(request, f"You are now friends with {friendship.from_user.username}!")
    return redirect('friend_list')


@login_required
def decline_friend_request(request, friendship_id):
    friendship = get_object_or_404(Friendship, id=friendship_id, to_user=request.user, is_accepted=False)
    friendship.delete()

    messages.info(request, f"Friend request from {friendship.from_user.username} declined.")
    return redirect('friend_list')


@login_required
def remove_friend(request, user_id):
    friend = get_object_or_404(User, id=user_id)

    Friendship.objects.filter(
        Q(from_user=request.user, to_user=friend) |
        Q(from_user=friend, to_user=request.user)
    ).delete()

    groups = Group.objects.filter(created_by=request.user, members=friend)
    for g in groups:
        g.members.remove(friend)

    for event in Event.objects.filter(created_by=request.user, visible_to_friends=friend):
        event.visible_to_friends.remove(friend)

    for event in Event.objects.filter(created_by=request.user, visible_to_groups__members=friend).distinct():
        event.visible_to_groups.remove(*event.visible_to_groups.filter(members=friend))

    invitations = EventInvitation.objects.filter(event__created_by=request.user, user=friend)

    for invitation in invitations:
        event = invitation.event
        other_invitations = EventInvitation.objects.filter(event=event).exclude(user=friend)
        if not other_invitations.exists():
            event.delete()
        else:
            invitation.delete()

    EventInvitation.objects.filter(event__created_by=friend, user=request.user).delete()

    messages.info(request, f"You unfriended {friend.username}.")
    return redirect('friend_list')


@login_required
def search_users(request):
    q = request.GET.get('q', '')
    users = User.objects.filter(username__icontains=q).exclude(id=request.user.id)[:10]
    data = [{'id': u.id, 'username': u.username} for u in users]
    return JsonResponse(data, safe=False)


@login_required
def invite_friend(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        sender = request.user

        if User.objects.filter(email=email).exists():
            messages.warning(request, "That person already has an account!")
            return redirect(request.META.get('HTTP_REFERER', '/'))

        subject = f"{sender.first_name} {sender.last_name} invited you to join MyCalendar 🎉"
        message = (
            f"Hey there!\n\n"
            f"{sender.username} is inviting you to join MyCalendar.\n"
            f"Join now to plan events and share calendars together!\n\n"
            f"Click the link below to register:\n"
            f"http://127.0.0.1:8000/register/\n\n"
            f"See you soon!\n"
            f"- The MyCalendar Team"
        )

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )

        messages.success(request, f"Invitation sent to {email}!")
        return redirect(request.META.get('HTTP_REFERER', '/'))

    return redirect('/')


@login_required
def friend_calendar_view(request, friend_id):
    friend = get_object_or_404(User, id=friend_id)

    week_offset = int(request.GET.get("week", 0))

    today = localdate()
    start_of_week = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
    end_of_week = start_of_week + timedelta(days=7)

    prev_week = week_offset - 1
    next_week = week_offset + 1

    events = Event.objects.filter(
        Q(created_by=friend, invitations__isnull=True) |
        Q(created_by=friend, invitations__status='accepted') |
        Q(invitations__user=friend, invitations__status='accepted')
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
                "title": e.title if e.can_user_view(request.user) else "",
                "tag": e.tag if e.can_user_view(request.user) else "hidden",
                "visible": e.can_user_view(request.user),
                "start_offset": start_offset,
                "duration_height": duration_height,
            })

        days.append({
            "date": day_date,
            "weekday": day_date.strftime("%A"),
            "events": formatted_events,
        })

    return render(request, "friends/friend_calendar.html", {
        "friend": friend,
        "days": days,
        "week_start": start_of_week,
        "week_end": end_of_week - timedelta(days=1),
        "prev_week": prev_week,
        "next_week": next_week,
        "hours": range(0, 24),
    })