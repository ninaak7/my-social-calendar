from django.contrib import admin

from calendar_app.models import CustomUser
from events.models import Event, EventInvitation
from friends.models import Friendship
from groups.models import Group

admin.site.register(CustomUser)
admin.site.register(Friendship)
admin.site.register(Group)
admin.site.register(Event)
admin.site.register(EventInvitation)