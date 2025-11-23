from django.core.exceptions import ValidationError
from django.db import models
from django.conf import settings

# Create your models here.
def validate_10_min_interval(dt):
    if dt.minute % 10 != 0:
        raise ValidationError("Time must be in 10-minute intervals.")

class Event(models.Model):
    TAG_CHOICES = [
        ('personal', 'Personal'),
        ('family', 'Family'),
        ('social', 'Social'),
        ('entertainment', 'Entertainment'),
        ('education', 'Education'),
        ('holiday', 'Holiday'),
    ]

    VISIBILITY_CHOICES = [
        ('private', 'Only me'),
        ('public', 'Everyone'),
        ('invited', 'Only invited users'),
        ('custom', 'Custom selection'),
    ]

    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    start_time = models.DateTimeField(validators=[validate_10_min_interval])
    end_time = models.DateTimeField(validators=[validate_10_min_interval])
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='events_created')
    tag = models.CharField(max_length=20, choices=TAG_CHOICES, blank=True, null=True)
    visibility = models.CharField(max_length=10, choices=VISIBILITY_CHOICES, default='private')
    visible_to_friends = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='events_visibility')
    visible_to_groups = models.ManyToManyField('groups.Group', blank=True, related_name='events_visibility')

    def __str__(self):
        return f"{self.title} ({self.created_by.username})"

    def can_user_view(self, user):
        if user == self.created_by:
            return True
        if self.visibility == 'public':
            return True
        if self.visibility == 'invited':
            return EventInvitation.objects.filter(event=self, user=user).exists()
        if self.visibility == 'custom':
            return (
                    self.visible_to_friends.filter(id=user.id).exists() or
                    self.visible_to_groups.filter(members=user).exists()
            )
        if EventInvitation.objects.filter(event=self, user=user, status='accepted').exists():
            return True
        return False


class EventInvitation(models.Model):
    INVITE_STATUS = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
    ]

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='invitations')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='friend_invitations')
    group = models.ForeignKey('groups.Group', on_delete=models.CASCADE, null=True, blank=True, related_name='group_invitations')
    status = models.CharField(max_length=10, choices=INVITE_STATUS, default='pending')

    def __str__(self):
        return f"{self.user.username} → {self.event.title} ({self.status})"