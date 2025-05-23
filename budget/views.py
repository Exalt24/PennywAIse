from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import TemplateView
from django.utils import timezone
from django.contrib.auth import authenticate, login, get_user_model
from . import forms
from .models import Category, Entry, Budget, EmailVerificationToken, PasswordResetToken
from django.db.models import Sum, Count, Q, Avg
from django.contrib.auth.mixins import LoginRequiredMixin
from dateutil.relativedelta import relativedelta
from django.http import HttpResponse
import csv
from django.contrib import messages
import secrets
from django.core.paginator import Paginator
from django.http           import JsonResponse
from django.template.loader import render_to_string
from django.views import View
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.http import JsonResponse
import json
from google import genai
from google.genai import types
from google.genai.errors import ClientError
import random
from django.utils import timezone
from django.db.models.functions import Lower
from decimal import Decimal

gemini_client = genai.Client(
    api_key=settings.GEMINI_API_KEY,
)

User = get_user_model()

class IndexView(TemplateView):
    template_name = "index.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['contact_form'] = forms.ContactForm()
        return context
    
    def post(self, request, *args, **kwargs):
        if 'send-message' in request.POST:
            contact_form = forms.ContactForm(request.POST)
            if contact_form.is_valid():
                contact_form.save()
                messages.success(request, "Your message has been sent! We'll get back to you soon.")
                return redirect('budget:index')
            else:
                context = self.get_context_data(**kwargs)
                context['contact_form'] = contact_form
                return self.render_to_response(context)
                
        return super().get(request, *args, **kwargs)

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "main/dashboard.html"

    def get(self, request, *args, **kwargs):
        if request.GET.get('export') == 'csv':
            return self._export_csv(request)

        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user

        # Forms and initial context
        ctx['category_form'] = forms.CategoryForm(user=user)
        ctx['edit_category_form'] = forms.CategoryForm(user=user)
        ctx['is_edit_category'] = False
        ctx['edit_category_id'] = ''
        ctx['active_tab'] = 'dashboard'
        ctx['budget_form'] = forms.BudgetForm(
            initial={'month': timezone.localdate().replace(day=1)},
            user=user
        )
        ctx['entry_form'] = forms.EntryForm(user=user)
        ctx['user_categories'] = Category.objects.filter(user=user)

        edit_id = self.request.GET.get('edit')
        if edit_id:
            entry = get_object_or_404(Entry, pk=edit_id, user=user)
            ctx['entry_form'] = forms.EntryForm(instance=entry, user=user)
            ctx['edit_id'] = entry.pk

        today = timezone.localdate()
        month_start = today.replace(day=1)

        # Overview totals
        month_qs = Entry.objects.filter(user=user, date__gte=month_start)
        income_total = (month_qs.filter(type=Entry.INCOME)
                        .aggregate(total=Sum('amount'))['total'] or 0)
        expense_total = (month_qs.filter(type=Entry.EXPENSE)
                        .aggregate(total=Sum('amount'))['total'] or 0)
        net_balance = income_total - expense_total
        ctx.update({
            'income_total': income_total,
            'expense_total': expense_total,
            'net_balance': net_balance,
            'net_balance_abs': abs(net_balance),
            'transaction_count': month_qs.count(),
        })

        # Month-over-month comparison
        last_start = month_start - relativedelta(months=1)
        last_end = month_start - relativedelta(days=1)
        last_inc = (Entry.objects.filter(user=user, type=Entry.INCOME,
                    date__gte=last_start, date__lte=last_end)
                    .aggregate(total=Sum('amount'))['total'] or 0)
        last_exp = (Entry.objects.filter(user=user, type=Entry.EXPENSE,
                    date__gte=last_start, date__lte=last_end)
                    .aggregate(total=Sum('amount'))['total'] or 0)
        def pct_change(curr, prev):
            return (curr - prev) / prev * 100 if prev else None
        ctx.update({
            'last_income_total': last_inc,
            'last_expense_total': last_exp,
            'income_pct_change': pct_change(income_total, last_inc),
            'expense_pct_change': pct_change(expense_total, last_exp),
        })

        # Averages and extremes
        avg_txn = (month_qs.aggregate(avg=Avg('amount'))['avg'] or 0)
        largest_expense = (Entry.objects.filter(user=user, type=Entry.EXPENSE, date__gte=month_start)
                .order_by('-amount').first())
        largest_income = (Entry.objects.filter(user=user, type=Entry.INCOME, date__gte=month_start)
                .order_by('-amount').first())
        ctx.update({
            'avg_transaction': avg_txn,
            'largest_expense': largest_expense,
            'largest_income': largest_income,
        })

        # Cash-flow forecast
        days_passed   = today.day
        days_in_month = (month_start + relativedelta(months=1) - relativedelta(days=1)).day

        if days_passed:
            avg_daily_spent = expense_total / Decimal(days_passed)
        else:
            avg_daily_spent = Decimal('0')
        projected_balance = income_total - (avg_daily_spent * Decimal(days_in_month))
        abs_proj_balance  = abs(projected_balance)
        ctx.update({
            'avg_daily_spent': avg_daily_spent,
            'projected_balance': projected_balance,
            'abs_proj_balance': abs_proj_balance,
            'days_remaining': days_in_month - days_passed,
        })

        # Per-category aggregates
        exp_map = {e['category__name'] or '—': e['total'] for e in
                Entry.objects.filter(user=user, type=Entry.EXPENSE, date__gte=month_start)
                        .values('category__name').annotate(total=Sum('amount'))}
        inc_map = {i['category__name'] or '—': i['total'] for i in
                Entry.objects.filter(user=user, type=Entry.INCOME, date__gte=month_start)
                        .values('category__name').annotate(total=Sum('amount'))}
        budget_qs = Budget.objects.filter(user=user, month=month_start)
        cat_budget_map = {b.category.name: b.amount for b in budget_qs.filter(category__isnull=False)}
        total_budget_obj = budget_qs.filter(category__isnull=True).first()
        total_budget = total_budget_obj.amount if total_budget_obj else None
        total_spent = expense_total
        total_remaining = (total_budget - total_spent) if total_budget is not None else None
        ctx.update({
            'total_budget': total_budget,
            'total_spent': total_spent,
            'total_remaining': total_remaining,
            'total_remaining_abs': abs(total_remaining) if total_remaining is not None else None,
            'over_budget': (total_remaining < 0) if total_remaining is not None else False,
        })

        summary = []
        for cat in ctx['user_categories']:
            name = cat.name
            inc_amt = inc_map.get(name, 0)
            exp_amt = exp_map.get(name, 0)
            budg = cat_budget_map.get(name)
            rem = (budg - exp_amt) if budg is not None else None
            summary.append({
                'name': name,
                'income': inc_amt,
                'expense': exp_amt,
                'budget': budg,
                'remaining': rem,
                'remaining_abs': abs(rem) if rem is not None else None,
                'over': (rem < 0) if rem is not None else False,
            })
        ctx['category_summary'] = summary
        ctx['top_categories_summary'] = sorted(summary, key=lambda r: r['expense'], reverse=True)[:3]

        # Entries and pagination
        inc_qs = Entry.objects.filter(user=user, type=Entry.INCOME).order_by('-date')
        exp_qs = Entry.objects.filter(user=user, type=Entry.EXPENSE).order_by('title', '-date')
        rep_qs = Entry.objects.filter(user=user).order_by('-date')
        inc_page = Paginator(inc_qs, 10).get_page(self.request.GET.get('inc_page'))
        exp_page = Paginator(exp_qs, 10).get_page(self.request.GET.get('exp_page'))
        rep_page = Paginator(rep_qs,10).get_page(self.request.GET.get('report_page'))
        ctx.update({
            'income_entries': inc_page.object_list,
            'expense_entries': exp_page.object_list,
            'report_entries': rep_page.object_list,
            'page_obj_income': inc_page,
            'page_obj_expense': exp_page,
            'page_obj_report': rep_page,
            'recent_transactions': Entry.objects.filter(user=user).order_by('-date')[:10],
        })
        # Chart data
        expenses = [r['expense'] for r in summary]
        ctx['chart_cat_labels'] = [r['name'] for r in summary]
        ctx['chart_cat_income'] = [float(r['income']) for r in summary]
        ctx['chart_cat_expense'] = [float(r['expense']) for r in summary]
        ctx['has_cat_expense']    = any(exp > 0 for exp in expenses)
        ctx['chart_budget_data'] = ([float(total_spent), float(total_remaining)]
                                    if total_budget is not None else None)
        labels, inc_vals, exp_vals = [], [], []
        for i in range(5, -1, -1):
            m = month_start - relativedelta(months=i)
            labels.append(m.strftime('%b %Y'))
            inc_vals.append(float(
                Entry.objects.filter(user=user, type=Entry.INCOME,
                    date__year=m.year, date__month=m.month)
                .aggregate(Sum('amount'))['amount__sum'] or 0
            ))
            exp_vals.append(float(
                Entry.objects.filter(user=user, type=Entry.EXPENSE,
                    date__year=m.year, date__month=m.month)
                .aggregate(Sum('amount'))['amount__sum'] or 0
            ))
        ctx.update({
            'chart_trend_labels': labels,
            'chart_trend_income': inc_vals,
            'chart_trend_expense': exp_vals,
            'chart_cat_budget': [float(r.get('budget') or 0) for r in summary],
        })
        # Category statistics
        cats = Category.objects.filter(user=user).annotate(
            entry_count=Count('entry'),
            total_inc=Sum('entry__amount', filter=Q(entry__type=Entry.INCOME)),
            total_exp=Sum('entry__amount', filter=Q(entry__type=Entry.EXPENSE)),
        ).order_by(Lower('name'))
        stats = []
        for c in cats:
            inc = c.total_inc or 0
            exp = c.total_exp or 0
            net = inc - exp
            c.net = net
            c.net_abs = abs(net)
            stats.append(c)
        cat_page = Paginator(stats, 10).get_page(self.request.GET.get('cat_page'))
        ctx['category_stats'] = cat_page.object_list
        ctx['page_obj_category'] = cat_page

        summary = sorted(summary, key=lambda r: r['name'].lower())
        budg_page = Paginator(summary, 10).get_page(self.request.GET.get('budget_page'))
        ctx['budget_rows'] = budg_page.object_list
        ctx['page_obj_budget'] = budg_page

        # Navigation and chart colors
        ctx['nav_items'] = [
            {'href': '#dashboard', 'icon': 'images/dashboard.png', 'label': 'Dashboard'},
            {'href': '#categories', 'icon': 'images/categories.png', 'label': 'Categories'},
            {'href': '#income', 'icon': 'images/income.png', 'label': 'Income'},
            {'href': '#expenses', 'icon': 'images/expense.png', 'label': 'Expenses'},
            {'href': '#budgets', 'icon': 'images/budget.png', 'label': 'Budgets'},
            {'href': '#reports', 'icon': 'images/reports.png', 'label': 'Reports'},
            {'href': '#ai', 'icon': 'images/convo.png', 'label': 'AI Assistant'},
        ]
        ctx['chart_cat_colors'] = [
            f"rgba({random.randint(50,200)}, {random.randint(50,200)}, {random.randint(50,200)}, 0.5)"
            for _ in ctx['chart_cat_labels']
        ]

        return ctx


    def _export_csv(self, request):
        user = request.user
        qs = Entry.objects.filter(user=user)
        gf = request.GET

        if gf.get('from'):
            qs = qs.filter(date__gte=gf['from'])
        if gf.get('to'):
            qs = qs.filter(date__lte=gf['to'])
        if gf.get('type'):
            qs = qs.filter(type=gf['type'])
        if gf.get('category'):
            qs = qs.filter(category_id=gf['category'])

        resp = HttpResponse(content_type='text/csv')
        resp['Content-Disposition'] = 'attachment; filename="{user}_transactions_{now}.csv"'.format(
            user=user.username,
            now=timezone.localdate().strftime('%Y-%m-%d')
        )
        writer = csv.writer(resp)
        writer.writerow(['Date','Title','Category','Type','Amount'])
        for e in qs.order_by('-date'):
            writer.writerow([
                e.date.isoformat(),
                e.title,
                e.category.name if e.category else '',
                e.get_type_display(),
                "{:.2f}".format(e.amount),
            ])
        return resp

    def post(self, request, *args, **kwargs):
        user = request.user
        tab = 'dashboard'
        base = reverse('budget:dashboard')

        if 'add-category' in request.POST:
            cat_id = request.POST.get('category-id')
            instance = get_object_or_404(Category, pk=cat_id, user=user) if cat_id else None
            form = forms.CategoryForm(request.POST, instance=instance, user=user)
            tab = 'categories'
            if cat_id:
                instance = get_object_or_404(Category, pk=cat_id, user=user)
                form    = forms.CategoryForm(request.POST, instance=instance, user=user)
            else:
                form    = forms.CategoryForm(request.POST, user=user)

            if form.is_valid():
                cat = form.save(commit=False)
                cat.user = user
                cat.save()
                if cat_id:
                    messages.success(request, "Category updated successfully.")
                else:
                    messages.success(request, "Category added successfully.")
                return redirect(f"{base}#{tab}")

            ctx = self.get_context_data(**kwargs)
            if instance:
                ctx['edit_category_form'] = form
                ctx['is_edit_category']   = True
                ctx['edit_category_id']   = cat_id
                ctx['active_tab']         = 'categories'
            else:
                ctx['category_form']      = form
            return self.render_to_response(ctx)
 
        if 'add-entry' in request.POST:
            eid = request.POST.get('entry-id')
            if eid:
                inst = get_object_or_404(Entry, pk=eid, user=user)
                form = forms.EntryForm(request.POST, instance=inst, user=user)
            else:
                form = forms.EntryForm(request.POST, user=user)

            if form.is_valid():
                e = form.save(commit=False)
                e.user = user
                e.save()
                tab = 'income' if e.type == Entry.INCOME else 'expenses'
                if eid:
                    messages.success(request, "Entry updated successfully.")
                else:
                    messages.success(request, "Entry added successfully.")
                return redirect(f"{base}#{tab}")

            ctx = self.get_context_data(**kwargs)
            ctx['entry_form'] = form
            ctx['edit_id']    = eid
            return self.render_to_response(ctx)

        if 'delete-entry' in request.POST:
            e = get_object_or_404(Entry, pk=request.POST['delete-entry'], user=user)
            tab = 'income' if e.type == Entry.INCOME else 'expenses'
            e.delete()
            messages.success(request, "Entry deleted successfully.")
            return redirect(f"{base}#{tab}")
        
        if 'set-budget' in request.POST:
            tab = 'budgets'
            bform = forms.BudgetForm(request.POST, user=user)
            if bform.is_valid():
                today = timezone.localdate()
                cat   = bform.cleaned_data['category']
                month = today.replace(day=1)
                amt   = bform.cleaned_data['amount']

                Budget.objects.update_or_create(
                    user=user,
                    category=cat,
                    month=month,
                    defaults={'amount': amt}
                )
                messages.success(request, "Budget set successfully.")
                return redirect(f"{base}#{tab}")

            ctx = self.get_context_data(**kwargs)
            ctx['budget_form'] = bform
            return self.render_to_response(ctx)\

        if 'delete-category' in request.POST:
            tab = 'categories'
            cat = get_object_or_404(Category, pk=request.POST['delete-category'], user=user)
            cat.delete()
            messages.success(request, "Category deleted successfully.")
            return redirect(f"{base}#{tab}")

        return super().post(request, *args, **kwargs)

class AuthView(TemplateView):
    template_name = "authentication/auth.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault('login_form', forms.LoginForm())
        context.setdefault('register_form', forms.RegisterForm())
        return context

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)

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
                    messages.success(request, "Welcome back to PennywAIse, " + user.username + "!")
                    return redirect('budget:dashboard')
                context['login_error'] = "Invalid email or password."

        elif 'register-submit' in request.POST:
            register_form = forms.RegisterForm(request.POST)
            context['register_form'] = register_form

            if register_form.is_valid():
                user = register_form.save(commit=False)
                user.is_active = False
                user.save()

                token = EmailVerificationToken.objects.create(user=user)

                verify_path = reverse('budget:verify_email', args=[str(token.token)])
                verification_url = request.build_absolute_uri(verify_path)

                subject = "Verify your PennywAIse account"
                html_body = render_to_string(
                    'authentication/email_verification.html',
                    {'user': user, 'verification_url': verification_url}
                )
                email = EmailMultiAlternatives(
                    subject=subject,
                    body="Please view this email in HTML format.",
                    from_email=settings.EMAIL_HOST_USER,
                    to=[user.email],
                )
                email.attach_alternative(html_body, "text/html")
                email.send()

                messages.success(
                    request,
                    "Thanks for signing up! Check your inbox for a verification link."
                )
                return redirect('budget:auth')

        return self.render_to_response(context)

class ForgotPasswordView(TemplateView):
    template_name = "authentication/forgot_password.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault('forgot_password_form', forms.ForgotPasswordForm())
        return context
    
    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        form = forms.ForgotPasswordForm(request.POST)
        context['forgot_password_form'] = form

        if form.is_valid():
            user = form.cleaned_data['user_obj']

            token = secrets.token_urlsafe(32)
            PasswordResetToken.objects.create(user=user, token=token)

            path = reverse('budget:reset_password', kwargs={'token': token})
            reset_url = request.build_absolute_uri(path)

            subject = "Reset your PennywAIse password"
            html_body = render_to_string(
                'authentication/password_reset_email.html',
                {'user': user, 'reset_url': reset_url}
            )
            msg = EmailMultiAlternatives(
                subject=subject,
                body="Please view this email in HTML format.",
                from_email=settings.EMAIL_HOST_USER,
                to=[user.email],
            )
            msg.attach_alternative(html_body, "text/html")
            msg.send(fail_silently=False)

            messages.success(
                request,
                "Check your inbox for a password reset link!"
            )
            return redirect('budget:auth')

        return self.render_to_response(context)

class ResetPasswordView(TemplateView):
    template_name = "authentication/reset_password.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        token = self.kwargs.get('token')
        context['token'] = token
        context.setdefault('reset_password_form', forms.ResetPasswordForm())

        cutoff = timezone.now() - timezone.timedelta(hours=24)
        PasswordResetToken.objects.filter(
            token=token,
            expired=False,
            created_at__lt=cutoff
        ).update(expired=True)

        token_obj = PasswordResetToken.objects.filter(
            token=token,
            expired=False,
            created_at__gte=cutoff
        ).first()
        
        context['valid_token'] = token_obj is not None
        return context
    
    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        reset_password_form = forms.ResetPasswordForm(request.POST)
        context['reset_password_form'] = reset_password_form
        
        if not context['valid_token']:
            messages.error(request, "That reset link is invalid or has expired. Please request a new one.")
            return redirect('budget:forgot_password')
        
        if reset_password_form.is_valid():
            token = self.kwargs.get('token')
            from .models import PasswordResetToken
            token_obj = PasswordResetToken.objects.get(token=token)
            user = token_obj.user

            user.set_password(reset_password_form.cleaned_data['password1'])
            user.save()
            
            token_obj.expired = True
            token_obj.save()
            
            user = authenticate(request, username=user.username, password=reset_password_form.cleaned_data['password1'])
            if user:
                login(request, user)
            
            context['password_reset_complete'] = True
            
        return self.render_to_response(context)

class EntriesAjaxView(View):
    def get(self, request, *args, **kwargs):
        prefix = request.GET.get('prefix')
        user = request.user

        if prefix == 'inc':
            entry_type    = Entry.INCOME
            page_param    = 'inc_page'
            section_id    = 'income'
            aria_label    = 'Income entries'
            tbody_id      = 'incomeTable'
            amount_prefix = '+'
            amount_class  = 'text-green-600'
            empty_msg     = 'No income entries found.'
        elif prefix == 'exp':
            entry_type    = Entry.EXPENSE
            page_param    = 'exp_page'
            section_id    = 'expenses'
            aria_label    = 'Expense entries'
            tbody_id      = 'expenseTable'
            amount_prefix = '-'
            amount_class  = 'text-red-600'
            empty_msg     = 'No expense entries found.'
        else:
            return JsonResponse({'error': 'Invalid prefix'}, status=400)

        qs = Entry.objects.filter(user=user, type=entry_type)

        date_from = request.GET.get(f'{prefix}DateFrom')
        date_to   = request.GET.get(f'{prefix}DateTo')
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)

        title_q = request.GET.get(f'{prefix}TitleFilter', '').strip()
        if title_q:
            qs = qs.filter(title__icontains=title_q)

        cat_q = request.GET.get(f'{prefix}CategoryFilter', '').strip().lower()
        if cat_q:
            qs = qs.filter(category__name__iexact=cat_q)

        min_amt = request.GET.get(f'{prefix}MinAmount')
        max_amt = request.GET.get(f'{prefix}MaxAmount')
        if min_amt:
            try:
                qs = qs.filter(amount__gte=float(min_amt))
            except ValueError:
                pass
        if max_amt:
            try:
                qs = qs.filter(amount__lte=float(max_amt))
            except ValueError:
                pass

        qs = qs.order_by('-date')
        page_num = request.GET.get(page_param) or 1
        page_obj = Paginator(qs, 10).get_page(page_num)

        html = render_to_string('main/components/tables/entries_table.html', {
            'entries':        page_obj.object_list,
            'page_obj':       page_obj,
            'page_param':     page_param,
            'section_id':     section_id,
            'aria_label':     aria_label,
            'tbody_id':       tbody_id,
            'amount_prefix':  amount_prefix,
            'amount_class':   amount_class,
            'empty_message':  empty_msg,
        }, request=request)

        return JsonResponse({'html': html})
    
class ReportsAjaxView(View):
    def get(self, request, *args, **kwargs):
        user    = request.user
        qs      = Entry.objects.filter(user=user).order_by('-date')
        
        frm     = request.GET.get('repFrom')
        to      = request.GET.get('repTo')
        ttype   = request.GET.get('repType')
        cat     = request.GET.get('repCat')

        if frm:
            qs = qs.filter(date__gte=frm)
        if to:
            qs = qs.filter(date__lte=to)
        if ttype:
            typemap = {'IN': Entry.INCOME, 'EX': Entry.EXPENSE}
            if ttype in typemap:
                qs = qs.filter(type=typemap[ttype])
        if cat:
            qs = qs.filter(category__id=cat)

        page_num = request.GET.get('report_page') or 1
        page_obj = Paginator(qs, 10).get_page(page_num)
        entries  = page_obj.object_list
        
        html = render_to_string(
            'main/components/tables/report_table.html',
            {
              'report_entries':      entries,
              'report_entries_all':  Entry.objects.filter(user=user).order_by('-date'),
              'page_obj':            page_obj,
              'page_param':          'report_page',
              'section_id':          'reports',
              'aria_label':          'Report entries table',
              'table_id':            'reportTable',
              'tbody_id':            'reportTable',
            },
            request=request
        )
        return JsonResponse({'html': html})
    
class VerifyEmailView(View):
    def get(self, request, token):
        try:
            tok = EmailVerificationToken.objects.get(token=token, used=False)
        except EmailVerificationToken.DoesNotExist:
            messages.error(request, "Invalid or expired verification link.")
            return redirect('budget:auth')

        user = tok.user
        user.is_active = True
        user.save()

        tok.used = True
        tok.save()

        login(request, user)
        messages.success(request, "Your email has been verified. Welcome to PennywAIse!")
        return redirect('budget:dashboard')
    
class AIQueryView(LoginRequiredMixin, View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            prompt = data.get('prompt', '').strip()
            if not prompt:
                return JsonResponse({'error': 'Prompt cannot be empty.'}, status=400)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data.'}, status=400)

        system_instruction = """
You are PennywAise, a friendly personal finance assistant.

1. If a user asks about **their own data** (transactions, budgets, categories, or reports in PennywAise), answer by referencing exactly those records.
2. If a user asks a **general finance question**—e.g. budgeting best practices, saving strategies, how credit cards work—provide a clear, concise, and actionable answer.
3. You **do not** answer non-finance questions (sports, weather, trivia). If asked anything outside personal finance, reply:
   "I'm sorry, but I can only answer questions about personal finance."

Always be polite, accurate, and to the point.
""".strip()

        # 3) assemble the conversation
        contents = [
            types.Content(role="model",
                          parts=[types.Part.from_text(text=system_instruction)]),
            types.Content(role="user",
                          parts=[types.Part.from_text(text=prompt)]),
        ]
        config = types.GenerateContentConfig(response_mime_type="text/plain")

        answer_fragments = []
        try:
            for chunk in gemini_client.models.generate_content_stream(
                model="gemini-2.5-pro-exp-03-25",
                contents=contents,
                config=config,
            ):
                answer_fragments.append(chunk.text or "")
        except ClientError as e:
            if "429" in str(e):
                return JsonResponse({
                    'error': 'AI service is temporarily unavailable due to quota limits. Please try again in a minute.'
                }, status=503)
            else:
                return JsonResponse({'error': 'An error occurred while processing your request. Please try again later.'}, status=500)
            raise   

        full_answer = "".join(answer_fragments).strip()
        return JsonResponse({'answer': full_answer})
    
class EntryDataView(LoginRequiredMixin, View):
    def get(self, request, pk):
        entry = get_object_or_404(Entry, pk=pk, user=request.user)
        return JsonResponse({
            'id':       entry.pk,
            'date':     entry.date.isoformat(),
            'title':    entry.title,
            'category': entry.category_id or '',
            'type':     entry.type,
            'amount':   str(entry.amount),
            'notes':    entry.notes or '',
        })