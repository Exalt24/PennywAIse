from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import TemplateView
from django.utils import timezone
from django.contrib.auth import authenticate, login, get_user_model
from . import forms
from .models import Category, Entry, Budget
from django.db.models import Sum, Count, Q
from django.contrib.auth.mixins import LoginRequiredMixin
from dateutil.relativedelta import relativedelta
from django.http import HttpResponse
import csv
from django.contrib import messages
import secrets
from django.core.paginator import Paginator

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
        # CSV export if requested
        if request.GET.get('export') == 'csv':
            return self._export_csv(request)

        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx  = super().get_context_data(**kwargs)
        user = self.request.user

        # ─── forms & categories ────────────────────────────────────────────────────
        ctx['category_form'] = forms.CategoryForm()
        ctx.setdefault('category_form', forms.CategoryForm(user=user))     # the inline “new” form
        ctx.setdefault('edit_category_form', forms.CategoryForm(user=user))# modal’s form (blank)
        ctx.setdefault('is_edit_category', False)
        ctx.setdefault('edit_category_id', '')
        ctx.setdefault('active_tab', 'dashboard')
        ctx.setdefault('category_form', forms.CategoryForm(user=user))
        ctx['budget_form'] = forms.BudgetForm(initial={ 'month': timezone.localdate().replace(day=1) }, user=user)
        ctx['user_categories'] = Category.objects.filter(user=user)

        # ─── entry form (or edit form) ─────────────────────────────────────────────
        ctx['entry_form'] = forms.EntryForm(user=user)
        edit_id = self.request.GET.get('edit')
        if edit_id:
            entry = get_object_or_404(Entry, pk=edit_id, user=user)
            ctx['entry_form'] = forms.EntryForm(instance=entry, user=user)
            ctx['is_edit']    = True
            ctx['edit_id']    = entry.pk
        else:
            ctx['is_edit'] = False

        # ─── “this month” window ──────────────────────────────────────────────────
        today       = timezone.localdate()
        month_start = today.replace(day=1)

        # ─── totals for overview cards ─────────────────────────────────────────────
        income_agg = Entry.objects.filter(
            user=user, type=Entry.INCOME, date__gte=month_start
        ).aggregate(total=Sum('amount'))
        expense_agg = Entry.objects.filter(
            user=user, type=Entry.EXPENSE, date__gte=month_start
        ).aggregate(total=Sum('amount'))

        income_total  = income_agg['total']  or 0
        expense_total = expense_agg['total'] or 0
        net_balance   = income_total - expense_total

        ctx.update({
            'income_total':      income_total,
            'expense_total':     expense_total,
            'net_balance':       net_balance,
            'net_balance_abs':   abs(net_balance),
            'transaction_count': Entry.objects.filter(user=user, date__gte=month_start).count(),
        })

        # ─── per‐category aggregates ────────────────────────────────────────────────
        exp_qs = (
            Entry.objects
                 .filter(user=user, type=Entry.EXPENSE, date__gte=month_start)
                 .values('category__name')
                 .annotate(total=Sum('amount'))
        )
        inc_qs = (
            Entry.objects
                 .filter(user=user, type=Entry.INCOME, date__gte=month_start)
                 .values('category__name')
                 .annotate(total=Sum('amount'))
        )
        exp_map = { e['category__name'] or '—': e['total'] for e in exp_qs }
        inc_map = { i['category__name'] or '—': i['total'] for i in inc_qs }

        # ─── budgets for this month ────────────────────────────────────────────────
        budget_qs = Budget.objects.filter(user=user, month=month_start)
        cat_budget_map = {
            b.category.name: b.amount
            for b in budget_qs.filter(category__isnull=False)
        }

        # total budget (blank category)
        total_budget_obj = budget_qs.filter(category__isnull=True).first()
        total_budget = total_budget_obj.amount if total_budget_obj else None
        total_spent = expense_total

        if total_budget is not None:
            total_remaining = total_budget - total_spent
            over_budget = total_remaining < 0
        else:
            total_remaining = None
            over_budget = False

        ctx.update({
            'total_budget':         total_budget,
            'total_spent':          total_spent,
            'total_remaining':      total_remaining,
            'total_remaining_abs':  abs(total_remaining) if total_remaining is not None else None,
            'over_budget':          over_budget,
        })

        user_cats = Category.objects.filter(user=user)
        # ─── build unified category summary ────────────────────────────────────────
        summary = []
        for cat in user_cats:
            name_str = cat.name                  
            inc_amt   = inc_map.get(name_str, 0)
            exp_amt   = exp_map.get(name_str, 0)
            budg      = cat_budget_map.get(name_str)
            rem       = (budg - exp_amt) if budg is not None else None
            over      = rem < 0 if rem is not None else False
            
            summary.append({
                'name':      name_str,
                'income':    inc_amt,
                'expense':   exp_amt,
                'budget':    budg,
                'remaining': rem,
                'remaining_abs': abs(rem) if rem is not None else None,
                'over':      over,
            })

        ctx['category_summary'] = summary

        # ─── tables & recent transactions ─────────────────────────────────────────
        ctx['income_entries']      = Entry.objects.filter(user=user, type=Entry.INCOME).order_by('title', '-date')
        ctx['expense_entries']     = Entry.objects.filter(user=user, type=Entry.EXPENSE).order_by('title', '-date')
        ctx['recent_transactions'] = Entry.objects.filter(user=user).order_by('-date')[:10]

        # ─── chart data (for Chart.js) ────────────────────────────────────────────
        ctx['chart_cat_labels']    = [r['name']    for r in summary]
        ctx['chart_cat_expense']   = [float(r['expense'])  for r in summary]
        ctx['chart_cat_income']    = [float(r['income'])   for r in summary]

        ctx['chart_budget_data']   = (
            [float(total_spent), float(total_remaining)]
            if total_budget is not None
            else None
        )

        cats = (
            Category.objects
                    .filter(user=user)
                    .annotate(
                        entry_count = Count('entry'),
                        total_inc   = Sum('entry__amount', filter=Q(entry__type=Entry.INCOME)),
                        total_exp   = Sum('entry__amount', filter=Q(entry__type=Entry.EXPENSE)),
                    )
        )

        for c in cats:
            c.total_inc = c.total_inc or 0
            c.total_exp = c.total_exp or 0
            c.net       = c.total_inc - c.total_exp
            c.net_abs   = abs(c.net)

        ctx['category_stats'] = cats

        labels = []
        inc_vals = []
        exp_vals = []
        for i in range(5, -1, -1):
            m = month_start - relativedelta(months=i)
            labels.append(m.strftime('%b %Y'))
            inc = Entry.objects.filter(
                user=user, type=Entry.INCOME,
                date__year=m.year, date__month=m.month
            ).aggregate(Sum('amount'))['amount__sum'] or 0
            exp = Entry.objects.filter(
                user=user, type=Entry.EXPENSE,
                date__year=m.year, date__month=m.month
            ).aggregate(Sum('amount'))['amount__sum'] or 0
            inc_vals.append(float(inc))
            exp_vals.append(float(exp))

        ctx['chart_trend_labels']    = labels
        ctx['chart_trend_income']    = inc_vals
        ctx['chart_trend_expense']   = exp_vals

        ctx['chart_cat_budget']  = [ float(r['budget']  or 0) for r in summary ]
        ctx['chart_cat_expense'] = [ float(r['expense'] or 0) for r in summary ]

        qs = Entry.objects.filter(user=user)
        gf = self.request.GET

        if gf.get('from'):
            qs = qs.filter(date__gte=gf['from'])
        if gf.get('to'):
            qs = qs.filter(date__lte=gf['to'])
        if gf.get('type'):
            qs = qs.filter(type=gf['type'])
        if gf.get('category'):
            qs = qs.filter(category_id=gf['category'])

        ctx['report_entries'] = qs.order_by('-date')

        inc_qs = ctx['income_entries']
        inc_page = Paginator(inc_qs,10).get_page(self.request.GET.get('inc_page'))
        ctx['page_obj_income']   = inc_page
        ctx['income_entries']     = inc_page.object_list

        exp_qs = ctx['expense_entries']
        exp_page = Paginator(exp_qs,10).get_page(self.request.GET.get('exp_page'))
        ctx['page_obj_expense']   = exp_page
        ctx['expense_entries']     = exp_page.object_list

        recent_qs = Entry.objects.filter(user=user).order_by('-date')
        recent_page = Paginator(recent_qs,10).get_page(self.request.GET.get('recent_page'))
        ctx['page_obj_recent']       = recent_page
        ctx['recent_transactions']   = recent_page.object_list

        full_qs = Entry.objects.filter(user=user).order_by('-date')
        ctx['report_entries_all'] = full_qs

        rep_qs = ctx['report_entries']
        rep_page = Paginator(rep_qs,10).get_page(self.request.GET.get('report_page'))
        ctx['page_obj_report']      = rep_page
        ctx['report_entries']       = rep_page.object_list

        cat_qs = ctx['category_stats']
        cat_page = Paginator(cat_qs,10).get_page(self.request.GET.get('cat_page'))
        ctx['page_obj_category']     = cat_page
        ctx['category_stats']        = cat_page.object_list
        
        ctx['budget_rows_list'] = summary  
        budg_page = Paginator(ctx['budget_rows_list'],10).get_page(self.request.GET.get('budget_page'))
        ctx['page_obj_budget']   = budg_page
        ctx['budget_rows']       = budg_page.object_list

        return ctx

    def _export_csv(self, request):
        user = request.user
        qs = Entry.objects.filter(user=user)
        gf = request.GET

        # same filters
        if gf.get('from'):
            qs = qs.filter(date__gte=gf['from'])
        if gf.get('to'):
            qs = qs.filter(date__lte=gf['to'])
        if gf.get('type'):
            qs = qs.filter(type=gf['type'])
        if gf.get('category'):
            qs = qs.filter(category_id=gf['category'])

        # stream CSV
        resp = HttpResponse(content_type='text/csv')
        resp['Content-Disposition'] = 'attachment; filename="report.csv"'
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
                is_edit = True
               
                form    = forms.CategoryForm(request.POST, instance=instance, user=user)
            else:
                is_edit = False
                form    = forms.CategoryForm(request.POST, user=user)

            if form.is_valid():
                cat = form.save(commit=False)
                cat.user = user
                cat.save()
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
 
        # 2) Create or update entry
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
                return redirect(f"{base}#{tab}")

            ctx = self.get_context_data(**kwargs)
            ctx['entry_form'] = form
            ctx['is_edit']    = bool(eid)
            ctx['edit_id']    = eid
            return self.render_to_response(ctx)

        # 3) Delete entry
        if 'delete-entry' in request.POST:
            e = get_object_or_404(Entry, pk=request.POST['delete-entry'], user=user)
            tab = 'income' if e.type == Entry.INCOME else 'expenses'
            e.delete()
            return redirect(f"{base}#{tab}")
        
         # 4) Create or update a budget
        if 'set-budget' in request.POST:
            tab = 'budgets'
            bform = forms.BudgetForm(request.POST, user=user)
            if bform.is_valid():
                today = timezone.localdate()
                cat   = bform.cleaned_data['category']   # maybe None for total
                month = today.replace(day=1)
                amt   = bform.cleaned_data['amount']

                Budget.objects.update_or_create(
                    user=user,
                    category=cat,
                    month=month,
                    defaults={'amount': amt}
                )
                return redirect(f"{base}#{tab}")

            ctx = self.get_context_data(**kwargs)
            ctx['budget_form'] = bform
            return self.render_to_response(ctx)\

        # 5) Delete
        if 'delete-category' in request.POST:
            tab = 'categories'
            cat = get_object_or_404(Category, pk=request.POST['delete-category'], user=user)
            cat.delete()
            return redirect(f"{base}#{tab}")

        # fallback to GET
        return super().post(request, *args, **kwargs)

class AuthView(TemplateView):
    template_name = "authentication/auth.html"
    
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

        return self.render_to_response(context)

class ForgotPasswordView(TemplateView):
    template_name = "authentication/forgot_password.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault('forgot_password_form', forms.ForgotPasswordForm())
        return context
    
    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        forgot_password_form = forms.ForgotPasswordForm(request.POST)
        context['forgot_password_form'] = forgot_password_form
        
        if forgot_password_form.is_valid():
            email = forgot_password_form.cleaned_data['email']
            user = User.objects.get(email__iexact=email)
            
            # Generate a unique token
            token = secrets.token_urlsafe(32)
            
            # Save the token in the database
            from .models import PasswordResetToken
            PasswordResetToken.objects.create(
                user=user,
                token=token
            )
            
            # Build the reset URL
            reset_url = request.build_absolute_uri(
                reverse('budget:reset_password', kwargs={'token': token})
            )
            
            context['reset_url'] = reset_url
            context['success'] = True
            
        return self.render_to_response(context)


class ResetPasswordView(TemplateView):
    template_name = "authentication/reset_password.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        token = self.kwargs.get('token')
        context['token'] = token
        context.setdefault('reset_password_form', forms.ResetPasswordForm())
        
        # Validate token
        from .models import PasswordResetToken
        token_obj = PasswordResetToken.objects.filter(
            token=token, 
            expired=False,
            created_at__gte=timezone.now() - timezone.timedelta(hours=24)
        ).first()
        
        context['valid_token'] = token_obj is not None
        
        return context
    
    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        reset_password_form = forms.ResetPasswordForm(request.POST)
        context['reset_password_form'] = reset_password_form
        
        if not context['valid_token']:
            return self.render_to_response(context)
        
        if reset_password_form.is_valid():
            token = self.kwargs.get('token')
            from .models import PasswordResetToken
            token_obj = PasswordResetToken.objects.get(token=token)
            user = token_obj.user
            
            # Set new password
            user.set_password(reset_password_form.cleaned_data['password1'])
            user.save()
            
            # Mark token as expired
            token_obj.expired = True
            token_obj.save()
            
            # Auto login user
            user = authenticate(request, username=user.username, password=reset_password_form.cleaned_data['password1'])
            if user:
                login(request, user)
            
            context['password_reset_complete'] = True
            
        return self.render_to_response(context)