from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from .models import Entry, Category
from django.utils import timezone


User = get_user_model()

EMAIL_REGEX = r'^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}(?:\.[A-Za-z]{2,})?$'

# finance/forms.py

from django import forms
from .models import Entry, Category


class EntryForm(forms.ModelForm):
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        # limit categories to this user
        if user is not None:
            self.fields['category'].queryset = Category.objects.filter(user=user)

        # shared base classes
        base_cls = (
            "mt-1 block w-full border-gray-300 rounded-md shadow-sm "
            "focus:ring-indigo-500 focus:border-indigo-500"
        )

        # placeholders for each field
        placeholders = {
            'title':    'e.g., Groceries',
            'amount':   'e.g., 50.00',
            'date':     '',
            'type':     '',                # select shows its own
            'category': '',                # we’ll rely on validation
            'notes':    'Optional notes about this entry',
        }

        for name, field in self.fields.items():
            field.widget.attrs.setdefault('class', base_cls)
            if (ph := placeholders.get(name)) is not None:
                field.widget.attrs['placeholder'] = ph

            if isinstance(field.widget, forms.Textarea):
                field.widget.attrs['class'] += " h-24 resize-none"

    # ----- field-specific validation -----

    def clean_title(self):
        title = self.cleaned_data.get('title', '').strip()
        if not title:
            raise forms.ValidationError("Title cannot be empty.")
        return title

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is None or amount <= 0:
            raise forms.ValidationError("Please enter an amount greater than zero.")
        return amount

    def clean_date(self):
        date = self.cleaned_data.get('date')
        if date and date > timezone.localdate():
            raise forms.ValidationError("Date cannot be in the future.")
        return date

    def clean_type(self):
        t = self.cleaned_data.get('type')
        # Entry.TYPE_CHOICES is something like [('IN','Income'),('EX','Expense')]
        valid = {c[0] for c in Entry.TYPE_CHOICES}
        if t not in valid:
            raise forms.ValidationError("Please select Income or Expense.")
        return t

    def clean_category(self):
        cat = self.cleaned_data.get('category')
        if cat is None:
            raise forms.ValidationError("Please pick a category.")
        return cat

    class Meta:
        model = Entry
        fields = ['title', 'amount', 'date', 'type', 'category', 'notes']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500',
                'placeholder': 'New category'
            })
        }

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

    def clean(self):
        cleaned = super().clean()
        return cleaned
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email=email).exists():
            raise forms.ValidationError(_("This email address is already in use. Please use a different email."))
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user