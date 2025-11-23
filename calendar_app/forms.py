from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from calendar_app.models import CustomUser

# Create your forms here.
class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    birthday = forms.DateField(required=True, widget=forms.DateInput(attrs={'type': 'date'}))
    gender = forms.ChoiceField(
        choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')],
        required=True
    )
    profile_picture = forms.ImageField(required=False)

    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'username', 'email', 'birthday', 'gender', 'profile_picture', 'password1', 'password2']


class LoginForm(AuthenticationForm):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)