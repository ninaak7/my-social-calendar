from django.db import models
from django.conf import settings

# Create your models here.
class Group(models.Model):
    name = models.CharField(max_length=100)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='groups_created')
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='group_membership', blank=True)

    def __str__(self):
        return f"{self.name} ({self.created_by.username})"