from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Entry, Category

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
    username = forms.CharField(
        max_length=150,
        label="Username",
        widget=forms.TextInput(attrs={
            'class': 'mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500',
            'placeholder': 'Your username'
        })
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            'class': 'mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500',
            'placeholder': '••••••••'
        })
    )


class RegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        label="Email",
        widget=forms.EmailInput(attrs={
            'class': 'mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500',
            'placeholder': 'you@example.com'
        })
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

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user