from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q
from django.contrib.auth import get_user_model
from django.contrib import messages
from calendar_app.models import CustomUser
from events.models import EventInvitation, Event
from friends.models import Friendship
from groups.forms import GroupForm
from groups.models import Group

# Create your views here.
User = get_user_model()

@login_required
def group_list(request):
    user_groups = Group.objects.filter(created_by=request.user)
    member_groups = Group.objects.filter(members=request.user).exclude(created_by=request.user)

    return render(request, 'groups/group_list.html', {
        'user_groups': user_groups,
        'member_groups': member_groups
    })


@login_required
def group_details(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    members = group.members.all()

    return render(request, 'groups/group_details.html', {
        'group': group,
        'members': members
    })


@login_required
def add_group(request):
    friends = Friendship.objects.filter(
        (Q(from_user=request.user) | Q(to_user=request.user)),
        is_accepted=True
    )

    friend_users = [
        f.from_user if f.to_user == request.user else f.to_user
        for f in friends
    ]

    if request.method == 'POST':
        form = GroupForm(request.POST, user=request.user)
        if form.is_valid():
            group = form.save(commit=False)
            group.created_by = request.user
            group.save()
            form.save_m2m()
            group.members.add(request.user)
            messages.success(request, "Group created successfully!")
            return redirect('group_list')
    else:
        form = GroupForm(user=request.user)

    return render(request, 'groups/add_group.html', {
        'form': form,
        'friend_users': friend_users
    })


@login_required
def edit_group(request, group_id):
    group = get_object_or_404(Group, id=group_id, created_by=request.user)

    if request.method == 'POST':
        form = GroupForm(request.POST, instance=group, user=request.user)
        if form.is_valid():
            group = form.save(commit=False)
            group.save()
            form.save_m2m()
            messages.success(request, "Group updated successfully!")
            return redirect('group_list')
        else:
            messages.error(request, "There was an error saving the group.")
    else:
        form = GroupForm(instance=group, user=request.user)

    friendships = Friendship.objects.filter(
        (Q(from_user=request.user) | Q(to_user=request.user)),
        is_accepted=True
    )

    friend_ids = [
        f.from_user.id if f.to_user == request.user else f.to_user.id
        for f in friendships
    ]

    friends = CustomUser.objects.filter(id__in=friend_ids)
    selected_members = group.members.all()
    available_friends = friends.exclude(id__in=selected_members.values_list('id', flat=True))

    return render(request, 'groups/edit_group.html', {
        'form': form,
        'group': group,
        'selected_members': selected_members,
        'available_friends': available_friends,
    })


@login_required
def delete_group(request, group_id):
    group = get_object_or_404(Group, id=group_id, created_by=request.user)

    invitations_to_group = EventInvitation.objects.filter(event__created_by=request.user, group=group)
    if invitations_to_group.exists():
        events_to_delete = Event.objects.filter(id__in=invitations_to_group.values_list('event_id', flat=True)).distinct()
        events_to_delete.delete()

    events = Event.objects.filter(created_by=request.user)
    for event in events:
        if group in event.visible_to_groups.all():
            event.visible_to_groups.remove(group)

    group.delete()

    messages.success(request, "Group deleted successfully.")
    return redirect('group_list')