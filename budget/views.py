from django.db.models import F
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views import generic
from django.views.generic import TemplateView
from django.utils import timezone
from django.contrib.auth import authenticate, login, get_user_model
from . import forms
from .models import Category, Entry
from django.db.models import Sum
from django.contrib.auth.mixins import LoginRequiredMixin


User = get_user_model()

class IndexView(TemplateView):
    template_name = "index.html"

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard.html"

    def get_context_data(self, **kwargs):
        ctx  = super().get_context_data(**kwargs)
        user = self.request.user

        # Category form + list
        ctx['category_form']   = forms.CategoryForm()
        ctx['user_categories'] = Category.objects.filter(user=user)

        # Entry form for the modal
        ctx['entry_form']      = forms.EntryForm(user=user)

        # Overview cards…
        today       = timezone.localdate()
        month_start = today.replace(day=1)

        income_agg  = Entry.objects.filter(
            user=user, type=Entry.INCOME, date__gte=month_start
        ).aggregate(total=Sum('amount'))

        expense_agg = Entry.objects.filter(
            user=user, type=Entry.EXPENSE, date__gte=month_start
        ).aggregate(total=Sum('amount'))

        ctx['income_total']      = income_agg['total']   or 0
        ctx['expense_total']     = expense_agg['total']  or 0
        ctx['net_balance']       = ctx['income_total'] - ctx['expense_total']
        ctx['transaction_count'] = Entry.objects.filter(
            user=user, date__gte=month_start
        ).count()

        # Data for charts & recent transactions
        ctx['expense_by_category'] = (
            Entry.objects
                 .filter(user=user, type=Entry.EXPENSE, date__gte=month_start)
                 .values('category__name')
                 .annotate(total=Sum('amount'))
        )
        ctx['recent_transactions'] = (
            Entry.objects
                 .filter(user=user)
                 .order_by('-date')[:10]
        )

        ctx['income_entries'] = (
            Entry.objects
                 .filter(user=user, type=Entry.INCOME)
                 .order_by('-date')
        )
        ctx['expense_entries'] = (
            Entry.objects
                 .filter(user=user, type=Entry.EXPENSE)
                 .order_by('-date')
        )

        return ctx

    def post(self, request, *args, **kwargs):
        # 1) New category?
        if 'add-category' in request.POST:
            cat_form = forms.CategoryForm(request.POST)
            if cat_form.is_valid():
                cat = cat_form.save(commit=False)
                cat.user = request.user
                cat.save()
            return redirect(reverse('budget:dashboard'))

        # 2) New entry?
        if 'add-entry' in request.POST:
            entry_form = forms.EntryForm(request.POST, user=request.user)
            if entry_form.is_valid():
                entry = entry_form.save(commit=False)
                entry.user = request.user
                entry.save()
                return redirect(reverse('budget:dashboard'))
            # re‐render with errors bound to entry_form
            ctx = self.get_context_data(**kwargs)
            ctx['entry_form'] = entry_form
            return self.render_to_response(ctx)

        # fallback
        return self.get(request, *args, **kwargs)

class AuthView(TemplateView):
    template_name = "auth.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # ensure each render has fresh forms (unless overridden in post)
        context.setdefault('login_form', forms.LoginForm())
        context.setdefault('register_form', forms.RegisterForm())
        return context

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)

        # --- LOGIN FLOW ---
        if 'login-submit' in request.POST:
            login_form = forms.LoginForm(request.POST)
            context['login_form'] = login_form

            if login_form.is_valid():
                email = login_form.cleaned_data['email']
                password = login_form.cleaned_data['password']
                try:
                    user_obj = User.objects.get(email__iexact=email)
                    user = authenticate(request, username=user_obj.username, password=password)
                except User.DoesNotExist:
                    user = None

                if user:
                    login(request, user)
                    return redirect('budget:dashboard')
                context['login_error'] = "Invalid email or password."

        # --- REGISTER FLOW ---
        elif 'register-submit' in request.POST:
            register_form = forms.RegisterForm(request.POST)
            context['register_form'] = register_form

            if register_form.is_valid():
                user = register_form.save()
                login(request, user)
                return redirect('budget:dashboard')
            # else: form errors will be shown via {{ register_form.errors }}

        # re-render with bound forms + any errors
        return self.render_to_response(context)
    