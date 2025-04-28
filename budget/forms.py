from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from .models import Entry, Category, Budget
from django.utils import timezone
from django.db.models import Sum
from datetime import date
from dateutil.relativedelta import relativedelta

User = get_user_model()

EMAIL_REGEX = r'^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}(?:\.[A-Za-z]{2,})?$'

class EntryForm(forms.ModelForm):
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

        # limit categories to this user
        if user is not None:
            self.fields['category'].queryset = Category.objects.filter(user=user)

        # shared base classes
        base_cls = (
            "mt-1 block w-full border-gray-300 rounded-md py-2 px-3 focus:ring-indigo-500 focus:border-indigo-500 border"
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
                 field.widget.attrs['class'] += " h-24 resize-none px-3"

    # ----- field-specific validation -----

    def clean(self):
        cleaned = super().clean()
        title    = cleaned.get('title')
        date     = cleaned.get('date')
        category = cleaned.get('category')

        if title and date and category and self.user:
            qs = Entry.objects.filter(
                user=self.user,
                title__iexact=title.strip(),
                date=date,
                category=category
            )
            # if we’re editing, exclude ourselves
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(
                    "You already have an entry in “%(cat)s” on %(date)s titled “%(title)s.”",
                    code='duplicate_entry',
                    params={
                        'cat':      category.name,
                        'date':     date.strftime("%b %-d, %Y"),
                        'title':    title.strip(),
                    }
                )
        return cleaned

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
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user  # remember who we’re validating for

        # apply your existing styling/placeholder
        self.fields['name'].widget.attrs.update({
            'class': 'mt-1 block w-full border-gray-300 rounded-md py-2 px-3 focus:ring-indigo-500 focus:border-indigo-500 border',
            'placeholder': 'New category',
        })

    def clean_name(self):
        name = self.cleaned_data['name'].strip()
        # build a queryset for this user, same name (case-insensitive)
        qs = Category.objects.filter(user=self.user, name__iexact=name)
        # if we’re editing, exclude our own instance
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("You already have a category with that name.")
        return name

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
    
class BudgetForm(forms.ModelForm):
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        # limit categories to this user
        if user is not None:
            self.fields['category'].queryset = Category.objects.filter(user=user)
        self.fields['category'].empty_label = "Total Budget"
        # we no longer expose `month` to the form
        self.fields.pop('month', None)

    def clean(self):
        cleaned = super().clean()
        amount   = cleaned.get('amount')
        category = cleaned.get('category')
        month    = timezone.localdate().replace(day=1)

        # all per-category budgets for this user/month
        qs = Budget.objects.filter(user=self.user, month=month, category__isnull=False)
        total_cat = qs.aggregate(total=Sum('amount'))['total'] or 0

        # if there’s already a budget on this same category, drop it from the sum
        if category is not None:
            old = qs.filter(category=category).first()
            if old:
                total_cat -= old.amount

        # Now total_cat is “all other categories,” so adding the new amount is safe
        if category is None:
            # total‐budget branch: must be ≥ sum of category budgets
            if amount is not None and amount < total_cat:
                raise forms.ValidationError(
                    f"Your total budget (₱{amount:.2f}) cannot be less than "
                    f"the sum of your per-category budgets (₱{total_cat:.2f})."
                )
        else:
            # per-category branch: ensure new sum ≤ total‐budget
            total_obj = Budget.objects.filter(
                user=self.user, month=month, category__isnull=True
            ).first()
            if total_obj and (total_cat + amount) > total_obj.amount:
                raise forms.ValidationError(
                    f"The sum of all category budgets (₱{total_cat + amount:.2f}) "
                    f"cannot exceed your total budget (₱{total_obj.amount:.2f})."
                )

        return cleaned


    class Meta:
        model = Budget
        fields = ['category', 'amount']
        widgets = {
            'category': forms.Select(attrs={
                'class': 'mt-1 block w-full border-gray-300 rounded-md shadow-sm '
                         'focus:ring-indigo-500 focus:border-indigo-500',
            }),
            'amount': forms.NumberInput(attrs={
                'step':'0.01',
                'class':'mt-1 block w-full',
                'placeholder':'e.g. 15000.00'
            }),
        }
        help_texts = {
            'category': 'Leave blank to set the overall budget for this month',
        }
