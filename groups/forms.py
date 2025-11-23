from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Q
from friends.models import Friendship
from groups.models import Group

# Create your forms here.
User = get_user_model()

class GroupForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ['name', 'members']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user:
            friends = Friendship.objects.filter(
                (Q(from_user=user) | Q(to_user=user)),
                is_accepted=True
            )

            friend_ids = [
                f.from_user.id if f.to_user == user else f.to_user.id
                for f in friends
            ]

            self.fields['members'].queryset = User.objects.filter(Q(id__in=friend_ids) | Q(id=user.id))