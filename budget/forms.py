from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from .models import Entry, Category

User = get_user_model()

EMAIL_REGEX = r'^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}(?:\.[A-Za-z]{2,})?$'

class EntryForm(forms.ModelForm):
    class Meta:
        model = Entry
        fields = ['title','amount','date','type','category','notes']
        widgets = {'date': forms.DateInput(attrs={'type':'date'})}

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name']


class LoginForm(forms.Form):
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={
            'class': 'mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500',
            'placeholder': 'you@example.com'
        }),
        validators=[
            RegexValidator(
                regex=EMAIL_REGEX,
                message="Enter a valid email address."
            )
        ]
    )
    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500',
            'placeholder': '••••••••'
        }),
        validators=[
            RegexValidator(
                regex=r'^.{8,}$',
                message="Password must be at least 8 characters long."
            )
        ]
    )

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if not User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("No account is registered with this email.")
        return email

class RegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        label=_("Email"),
        widget=forms.EmailInput(attrs={
            'class': 'mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500',
            'placeholder': 'you@example.com'
        }),
        validators=[
            RegexValidator(
                regex=EMAIL_REGEX,
                message=_("Enter a valid email address.")
            )
        ]
    )

    password1 = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500',
            'placeholder': 'At least 8 chars, 1 digit, 1 special'
        }),
        validators=[
            RegexValidator(
                regex=r'^(?=.*[A-Za-z])(?=.*\d)(?=.*[@$!%*#?&])[A-Za-z\d@$!%*#?&]{8,}$',
                message=_("Password must be ≥8 characters, include a letter, a number & a special character.")
            )
        ]
    )

    password2 = forms.CharField(
        label=_("Confirm Password"),
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500',
            'placeholder': 'Repeat your password'
        }),
    )

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500',
                'placeholder': 'Pick a username'
            }),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if not User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("No account is registered with this email.")
        return email

    def clean(self):
        cleaned = super().clean()
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user