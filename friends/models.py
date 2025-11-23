from django.db import models
from django.conf import settings

# Create your models here.
class Friendship(models.Model):
    from_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='friendship_requests_sent')
    to_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='friendship_requests_received')
    is_accepted = models.BooleanField(default=False)

    class Meta:
        unique_together = ('from_user', 'to_user')

    def __str__(self):
        status = "Accepted" if self.is_accepted else "Pending"
        return f"{self.from_user.username} → {self.to_user.username} ({status})"