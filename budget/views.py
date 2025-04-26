from django.db.models import F
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views import generic
from django.views.generic import TemplateView
from django.utils import timezone
from budget import forms

class IndexView(TemplateView):
    template_name = "index.html"

class DashboardView(TemplateView):
    template_name = "dashboard.html"

class AuthView(TemplateView):
    template_name = "auth.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['login_form'] = forms.LoginForm()
        context['register_form'] = forms.RegisterForm()
        return context
    
    # def post(self, request, *args, **kwargs):
    #     context = self.get_context_data(**kwargs)
        
    #     if 'login-submit' in request.POST:
    #         login_form = forms.LoginForm(request.POST)
    #         if login_form.is_valid():
    #             user = authenticate(
    #                 username=login_form.cleaned_data['username'],
    #                 password=login_form.cleaned_data['password']
    #             )
    #             if user is not None:
    #                 login(request, user)
    #                 return redirect('budget:dashboard')
    #             else:
    #                 context['login_form'] = login_form
    #                 context['login_error'] = "Invalid username or password"
    #         else:
    #             context['login_form'] = login_form
        
    #     elif 'register-submit' in request.POST:
    #         register_form = forms.RegisterForm(request.POST)
    #         if register_form.is_valid():
    #             user = register_form.save()
    #             login(request, user)
    #             return redirect('budget:dashboard')
    #         else:
    #             context['register_form'] = register_form
        
    #     return render(request, self.template_name, context)
    