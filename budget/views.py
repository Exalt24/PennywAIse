from django.db.models import F
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views import generic
from django.views.generic import TemplateView
from django.utils import timezone
from django.contrib.auth import authenticate, login
from . import forms

class IndexView(TemplateView):
    template_name = "index.html"

class DashboardView(TemplateView):
    template_name = "dashboard.html"

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
                user = authenticate(
                    username=login_form.cleaned_data['username'],
                    password=login_form.cleaned_data['password']
                )
                if user:
                    login(request, user)
                    return redirect('budget:dashboard')
                # authentication failed
                context['login_error'] = "Invalid username or password."

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
    