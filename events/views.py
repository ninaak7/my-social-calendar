from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.dateparse import parse_datetime
from django.contrib import messages
from events.models import Event, EventInvitation
from friends.models import Friendship
from groups.models import Group

# Create your views here.
User = get_user_model()

def is_valid_minute_increment(dt, interval=10):
    return dt.minute % interval == 0

@login_required
def event_list(request):
    selected_tag = request.GET.get('tag', 'all')

    created_events = (((Event.objects.filter(created_by=request.user, invitations__isnull=True).distinct()) |
                      Event.objects.filter(created_by=request.user, invitations__status='accepted').distinct() |
                       Event.objects.filter(invitations__user=request.user, invitations__status='accepted').distinct())
                      .distinct().order_by('start_time'))

    if selected_tag and selected_tag != 'all':
        created_events = created_events.filter(tag=selected_tag)

    pending_invitations = (EventInvitation.objects.filter(user=request.user, status='pending')
                           .exclude(event__created_by=request.user))
    accepted_invitations = (EventInvitation.objects.filter(user=request.user, status='accepted')
                            .exclude(event__created_by=request.user))
    sent_invitations = (EventInvitation.objects.filter(event__created_by=request.user, status='pending')
                        .select_related('event', 'user'))

    return render(request, 'events/event_list.html', {
        'created_events': created_events,
        'pending_invitations': pending_invitations,
        'sent_invitations': sent_invitations,
        'accepted_invitations': accepted_invitations,
        'selected_tag': selected_tag,
    })


@login_required
def add_event(request):
    friends = Friendship.objects.filter(Q(from_user=request.user) | Q(to_user=request.user), is_accepted=True)
    friend_users = [f.to_user if f.from_user == request.user else f.from_user for f in friends]

    groups = Group.objects.filter(created_by=request.user)

    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description', '')
        tag = request.POST.get('tag', '')
        visibility = request.POST.get('visibility')
        start_time = parse_datetime(request.POST['start_time'])
        end_time = parse_datetime(request.POST['end_time'])
        invited_friend_id = request.POST.get('friend')
        invited_group_id = request.POST.get('group')

        if not all([title, start_time, end_time]):
            messages.error(request, "Please fill all required fields.")
            return render(request, 'events/add_event.html', {
                'friends': friend_users,
                'groups': groups
            })

        if start_time >= end_time:
            messages.error(request, "Start time must be before end time.")
            return render(request, 'events/add_event.html', {
                'friends': friend_users,
                'groups': groups
            })

        if not is_valid_minute_increment(start_time) or not is_valid_minute_increment(end_time):
            messages.error(request, "Minutes must be in 10-minute intervals.")
            return render(request, 'events/add_event.html', {
                'friends': friend_users,
                'groups': groups
            })

        if invited_friend_id and invited_group_id:
            messages.error(request, "You can invite either a friend OR a group, not both.")
            return render(request, 'events/add_event.html', {
                'friends': friend_users,
                'groups': groups
            })

        overlap_exists = (
            Event.objects.filter(
                created_by=request.user,
                start_time__lt=end_time,
                end_time__gt=start_time
            ).exists()
            or EventInvitation.objects.filter(
                    user=request.user,
                    status='accepted',
                    event__start_time__lt=end_time,
                    event__end_time__gt=start_time
            ).exists()
        )

        if overlap_exists:
            messages.error(request, "You already have an event scheduled during this time!")
            return render(request, 'events/add_event.html', {
                'friends': friend_users,
                'groups': groups
            })

        event = Event.objects.create(
            title=title,
            description=description,
            tag=tag,
            visibility=visibility,
            start_time=start_time,
            end_time=end_time,
            created_by=request.user
        )

        if visibility == 'custom':
            selected_friends = request.POST.getlist('visible_to_friends')
            selected_groups = request.POST.getlist('visible_to_groups')

            if selected_friends:
                event.visible_to_friends.set(User.objects.filter(id__in=selected_friends))
            if selected_groups:
                event.visible_to_groups.set(Group.objects.filter(id__in=selected_groups))

        if invited_friend_id:
            friend = User.objects.get(id=invited_friend_id)
            EventInvitation.objects.create(event=event, user=friend)

            send_mail(
                subject=f"You’ve been invited to '{event.title}'!",
                message=(f"Hi {friend.username},\n\n"
                         f"{request.user.username} has invited you to the event '{event.title}'.\n"
                         f"Time: {event.start_time.strftime('%d-%m-%Y %H:%M')} - "
                         f"{event.end_time.strftime('%d-%m-%Y %H:%M')}\n\n"
                         f"Please check your calendar and respond to the invitation.\n\n"
                         f"– MyCalendar Team"),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[friend.email],
                fail_silently=False,
            )

        elif invited_group_id:
            group = Group.objects.get(id=invited_group_id)
            for member in group.members.exclude(id=request.user.id):
                EventInvitation.objects.create(event=event, user=member, group=group)

                send_mail(
                    subject=f"You’ve been invited to '{event.title}'!",
                    message=(f"Hi {member.username},\n\n"
                        f"{request.user.username} has invited your group '{group.name}' to the event '{event.title}'.\n"
                        f"Time: {event.start_time.strftime('%d-%m-%Y %H:%M')} - "
                        f"{event.end_time.strftime('%d-%m-%Y %H:%M')}\n\n"
                        f"Please check your calendar and respond to the invitation.\n\n"
                        f"– MyCalendar Team"),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[member.email],
                    fail_silently=False,
                )

        messages.success(request, "Event created successfully!")
        return redirect('event_list')

    return render(request, 'events/add_event.html', {
        'friends': friend_users,
        'groups': groups
    })


@login_required
def delete_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    event.delete()

    messages.success(request, "Event deleted successfully.")
    return redirect('event_list')


@login_required
def event_details(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    invitations = event.invitations
    accepted_invitations = event.invitations.filter(status='accepted')

    return render(request, 'events/event_details.html', {
        'event': event,
        'invitations': invitations,
        'accepted_invitations': accepted_invitations,
    })


@login_required
def edit_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    if event.created_by != request.user:
        return redirect('event_list')

    friends = Friendship.objects.filter(Q(from_user=request.user) | Q(to_user=request.user), is_accepted=True)
    friend_users = [f.to_user if f.from_user == request.user else f.from_user for f in friends]
    groups = Group.objects.filter(created_by=request.user)

    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description', '')
        tag = request.POST.get('tag', '')
        visibility = request.POST.get('visibility')
        start_time = parse_datetime(request.POST.get('start_time'))
        end_time = parse_datetime(request.POST.get('end_time'))

        if start_time >= end_time:
            messages.error(request, "Start time must be before end time.")
            return redirect('edit_event', event_id=event.id)

        if not is_valid_minute_increment(start_time) or not is_valid_minute_increment(end_time):
            messages.error(request, "Minutes must be in 10-minute intervals.")
            return redirect('edit_event', event_id=event.id)

        start_time = timezone.make_aware(start_time) if timezone.is_naive(start_time) else start_time
        end_time = timezone.make_aware(end_time) if timezone.is_naive(end_time) else end_time

        old_start = event.start_time
        old_end = event.end_time

        time_changed = (
                old_start.replace(microsecond=0) != start_time.replace(microsecond=0) or
                old_end.replace(microsecond=0) != end_time.replace(microsecond=0)
        )

        overlap_created = Event.objects.filter(
            created_by=request.user,
            start_time__lt=end_time,
            end_time__gt=start_time
        ).exclude(id=event.id).exists()

        overlap_invited = EventInvitation.objects.filter(
            user=request.user,
            status='accepted',
            event__start_time__lt=end_time,
            event__end_time__gt=start_time
        ).exclude(event=event).exists()

        if overlap_created or overlap_invited:
            messages.error(request, "You already have an event scheduled during this time.")
            return redirect('edit_event', event_id=event.id)

        event.title = title
        event.description = description
        event.tag = tag
        event.visibility = visibility
        event.start_time = start_time
        event.end_time = end_time
        event.save()

        if event.visibility == 'custom':
            selected_friends = request.POST.getlist('visible_to_friends')
            selected_groups = request.POST.getlist('visible_to_groups')

            event.visible_to_friends.set(User.objects.filter(id__in=selected_friends))
            event.visible_to_groups.set(Group.objects.filter(id__in=selected_groups))
        else:
            event.visible_to_friends.clear()
            event.visible_to_groups.clear()

        has_invites = EventInvitation.objects.filter(event=event).exclude(user=request.user)

        if time_changed and has_invites.exists():
            has_invites.update(status='pending')
            messages.info(request, "Time changed — all invited users must accept again.")

            for invite in has_invites:
                send_mail(
                    subject=f"Event '{event.title}' has been rescheduled",
                    message=(
                        f"Hi {invite.user.username},\n\n"
                        f"The event '{event.title}' has new start/end times.\n"
                        f"New time: {event.start_time.strftime('%d-%m-%Y %H:%M')} - "
                        f"{event.end_time.strftime('%d-%m-%Y %H:%M')}\n\n"
                        f"Please check your calendar and re-accept the invitation.\n\n"
                        f"– MyCalendar Team"
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[invite.user.email],
                    fail_silently=True,
                )
        else:
            messages.success(request, "Event updated successfully.")

        return redirect('event_details', event_id=event.id)

    return render(request, 'events/edit_event.html', {
        'event': event,
        'friends': friend_users,
        'groups': groups,
    })


@login_required
def invitation_response(request, invitation_id):
    invitation = get_object_or_404(EventInvitation, id=invitation_id, user=request.user)

    if request.method == 'POST':
        response = request.POST.get('response')
        event = invitation.event

        if response == 'accept':
            overlap_exists = (
                    EventInvitation.objects.filter(
                    user=request.user,
                    status='accepted',
                    event__start_time__lt=event.end_time,
                    event__end_time__gt=event.start_time
                ).exists()
                or Event.objects.filter(
                    created_by=request.user,
                    start_time__lt=event.end_time,
                    end_time__gt=event.start_time
                ).exists()
            )

            if overlap_exists:
                messages.error(request, f"You already have an event scheduled during this time.")
                return redirect('event_list')

            invitation.status = 'accepted'
            messages.success(request, f"You accepted the invitation to {invitation.event.title}.")

        elif response == 'decline':
            invitation.status = 'declined'
            messages.info(request, f"You declined the invitation to {invitation.event.title}.")

        invitation.save()

    return redirect('event_list')