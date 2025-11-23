from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings

# Create your models here.
class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    birthday = models.DateField(null=False, blank=False)
    gender = models.CharField(
        max_length=10,
        choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')],
        null=False,
        blank=False
    )
    profile_picture = models.ImageField(
        upload_to='profile_pics/',
        null=True,
        blank=True,
        default='profile_pics/default.jpg'
    )

    def __str__(self):
        return self.first_name + ' ' + self.last_name

    def get_profile_picture(self):
        if self.profile_picture:
            return self.profile_picture.url
        return settings.MEDIA_URL + 'profile_pics/default.jpg'