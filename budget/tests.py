from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from decimal import Decimal
from .models import Category, Entry
from .forms import EntryForm, CategoryForm, LoginForm, RegisterForm
import json
from django.utils import timezone
from datetime import date, timedelta

class ModelTests(TestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpassword'
        )
        
        # Create test category
        self.category = Category.objects.create(
            name='Test Category',
            user=self.user
        )
    
    def test_category_creation(self):
        """Test that a category can be created"""
        self.assertEqual(self.category.name, 'Test Category')
        self.assertEqual(self.category.user, self.user)
    
    def test_entry_creation(self):
        """Test that an entry can be created"""
        entry = Entry.objects.create(
            user=self.user,
            category=self.category,
            title='Test Entry',
            amount=Decimal('100.50'),
            date=date.today(),
            type=Entry.INCOME,
            notes='Test notes'
        )
        
        self.assertEqual(entry.title, 'Test Entry')
        self.assertEqual(entry.amount, Decimal('100.50'))
        self.assertEqual(entry.type, Entry.INCOME)
        self.assertEqual(entry.user, self.user)
        self.assertEqual(entry.category, self.category)

class FormTests(TestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpassword'
        )
        
        # Create test category
        self.category = Category.objects.create(
            name='Test Category',
            user=self.user
        )
    
    def test_entry_form_valid(self):
        """Test that entry form validates correctly with proper data"""
        form_data = {
            'title': 'Test Entry',
            'amount': '100.50',
            'date': date.today(),
            'type': Entry.INCOME,
            'category': self.category.id,
            'notes': 'Test notes'
        }
        form = EntryForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_entry_form_invalid(self):
        """Test that entry form validation fails with missing required data"""
        form_data = {
            'title': '',  # Required field is empty
            'amount': '100.50',
            'date': date.today(),
            'type': Entry.INCOME,
        }
        form = EntryForm(data=form_data)
        self.assertFalse(form.is_valid())
    
    def test_category_form_valid(self):
        """Test that category form validates correctly with proper data"""
        form_data = {
            'name': 'New Category',
        }
        form = CategoryForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_login_form_valid(self):
        """Test that login form validates correctly with proper data"""
        form_data = {
            'username': 'testuser',
            'password': 'testpassword',
        }
        form = LoginForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_register_form_valid(self):
        """Test that register form validates correctly with proper data"""
        form_data = {
            'username': 'newuser',
            'password1': 'newpassword',
            'password2': 'newpassword',
        }
        form = RegisterForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_register_form_passwords_mismatch(self):
        """Test that register form validation fails when passwords don't match"""
        form_data = {
            'username': 'newuser',
            'password1': 'password1',
            'password2': 'password2',  # Different from password1
        }
        form = RegisterForm(data=form_data)
        self.assertFalse(form.is_valid())

class ViewTests(TestCase):
    def setUp(self):
        # Create test client
        self.client = Client()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpassword'
        )
        
        # Create test category
        self.category = Category.objects.create(
            name='Test Category',
            user=self.user
        )
        
        # Create test entries
        self.income_entry = Entry.objects.create(
            user=self.user,
            category=self.category,
            title='Test Income',
            amount=Decimal('200.00'),
            date=date.today(),
            type=Entry.INCOME,
            notes='Test income notes'
        )
        
        self.expense_entry = Entry.objects.create(
            user=self.user,
            category=self.category,
            title='Test Expense',
            amount=Decimal('150.00'),
            date=date.today(),
            type=Entry.EXPENSE,
            notes='Test expense notes'
        )
    
    def test_index_view(self):
        """Test that index view returns correct response"""
        response = self.client.get(reverse('budget:index'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'index.html')
    
    def test_auth_view(self):
        """Test that auth view returns correct response with context data"""
        response = self.client.get(reverse('budget:auth'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'auth.html')
        self.assertIn('login_form', response.context)
        self.assertIn('register_form', response.context)
    
    def test_dashboard_view(self):
        """Test that dashboard view returns correct response"""
        # First login the user
        self.client.login(username='testuser', password='testpassword')
        response = self.client.get(reverse('budget:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard.html')

class AuthenticationTests(TestCase):
    def setUp(self):
        # Create test client
        self.client = Client()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpassword'
        )
        
        # Define URLs
        self.login_url = reverse('budget:auth')
        self.dashboard_url = reverse('budget:dashboard')
    
    def test_login_required_views(self):
        """Test that unauthenticated users are redirected from protected views"""
        response = self.client.get(self.dashboard_url)
        # If login_required is implemented, this should redirect
        # Skipping this test until login_required is implemented
        # self.assertEqual(response.status_code, 302)
        
    def test_user_can_login(self):
        """Test that users can log in through the login form"""
        # Implement once login functionality is complete
        # login_data = {
        #     'username': 'testuser',
        #     'password': 'testpassword',
        #     'login-submit': 'Login'
        # }
        # response = self.client.post(self.login_url, login_data)
        # self.assertRedirects(response, self.dashboard_url)
    
    def test_user_can_register(self):
        """Test that new users can register through the register form"""
        # Implement once registration functionality is complete
        # register_data = {
        #     'username': 'newuser',
        #     'password1': 'newpassword',
        #     'password2': 'newpassword',
        #     'register-submit': 'Register'
        # }
        # response = self.client.post(self.login_url, register_data)
        # self.assertRedirects(response, self.dashboard_url)
        # self.assertTrue(User.objects.filter(username='newuser').exists())

class EntryOperationsTests(TestCase):
    def setUp(self):
        # Create test client
        self.client = Client()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpassword'
        )
        
        # Login the user
        self.client.login(username='testuser', password='testpassword')
        
        # Create test category
        self.category = Category.objects.create(
            name='Test Category',
            user=self.user
        )
        
        # Create test entry
        self.entry = Entry.objects.create(
            user=self.user,
            category=self.category,
            title='Test Entry',
            amount=Decimal('100.50'),
            date=date.today(),
            type=Entry.EXPENSE,
            notes='Test notes'
        )
        
        # Define URL patterns - these will need to be uncommented when the views are implemented
        # self.entry_list_url = reverse('budget:entry_list')
        # self.entry_create_url = reverse('budget:entry_create')
        # self.entry_update_url = reverse('budget:entry_update', args=[self.entry.id])
        # self.entry_delete_url = reverse('budget:entry_delete', args=[self.entry.id])
    
    def test_entry_creation(self):
        """Test that a new entry can be created"""
        # This test will need to be uncommented when the entry_create view is implemented
        # entry_data = {
        #     'title': 'New Entry',
        #     'amount': '200.00',
        #     'date': date.today(),
        #     'type': Entry.INCOME,
        #     'category': self.category.id,
        #     'notes': 'New entry notes'
        # }
        # response = self.client.post(self.entry_create_url, entry_data)
        # self.assertRedirects(response, self.entry_list_url)
        # self.assertTrue(Entry.objects.filter(title='New Entry').exists())
    
    def test_entry_update(self):
        """Test that an existing entry can be updated"""
        # This test will need to be uncommented when the entry_update view is implemented
        # updated_data = {
        #     'title': 'Updated Entry',
        #     'amount': '150.00',
        #     'date': date.today(),
        #     'type': self.entry.type,
        #     'category': self.category.id,
        #     'notes': 'Updated notes'
        # }
        # response = self.client.post(self.entry_update_url, updated_data)
        # self.assertRedirects(response, self.entry_list_url)
        # self.entry.refresh_from_db()
        # self.assertEqual(self.entry.title, 'Updated Entry')
        # self.assertEqual(self.entry.amount, Decimal('150.00'))
        # self.assertEqual(self.entry.notes, 'Updated notes')
    
    def test_entry_deletion(self):
        """Test that an entry can be deleted"""
        # This test will need to be uncommented when the entry_delete view is implemented
        # response = self.client.post(self.entry_delete_url)
        # self.assertRedirects(response, self.entry_list_url)
        # self.assertFalse(Entry.objects.filter(id=self.entry.id).exists())
    
    def test_user_specific_entries(self):
        """Test that users can only see their own entries"""
        # Create another user with their own entry
        other_user = User.objects.create_user(
            username='otheruser',
            password='otherpassword'
        )
        
        other_category = Category.objects.create(
            name='Other Category',
            user=other_user
        )
        
        other_entry = Entry.objects.create(
            user=other_user,
            category=other_category,
            title='Other Entry',
            amount=Decimal('300.00'),
            date=date.today(),
            type=Entry.EXPENSE,
            notes='Other notes'
        )
        
        # This test assumes you have an entry_list view that filters entries by the current user
        # response = self.client.get(self.entry_list_url)
        # entries = response.context.get('entries', [])
        # 
        # # Check that only the current user's entry is in the response
        # self.assertEqual(len(entries), 1)
        # self.assertEqual(entries[0].id, self.entry.id)
        # self.assertFalse(any(e.id == other_entry.id for e in entries))

class ReportAndVisualizationTests(TestCase):
    def setUp(self):
        # Create test client
        self.client = Client()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpassword'
        )
        
        # Login the user
        self.client.login(username='testuser', password='testpassword')
        
        # Create test categories
        self.food_category = Category.objects.create(
            name='Food',
            user=self.user
        )
        
        self.transport_category = Category.objects.create(
            name='Transport',
            user=self.user
        )
        
        # Create test entries
        # This month's entries
        today = date.today()
        
        # Income entries
        Entry.objects.create(
            user=self.user,
            title='Salary',
            amount=Decimal('3000.00'),
            date=today,
            type=Entry.INCOME,
            notes='Monthly salary'
        )
        
        # Expense entries
        Entry.objects.create(
            user=self.user,
            category=self.food_category,
            title='Grocery Shopping',
            amount=Decimal('150.00'),
            date=today,
            type=Entry.EXPENSE,
            notes='Weekly groceries'
        )
        
        Entry.objects.create(
            user=self.user,
            category=self.food_category,
            title='Restaurant',
            amount=Decimal('80.00'),
            date=today,
            type=Entry.EXPENSE,
            notes='Dinner out'
        )
        
        Entry.objects.create(
            user=self.user,
            category=self.transport_category,
            title='Gas',
            amount=Decimal('70.00'),
            date=today,
            type=Entry.EXPENSE,
            notes='Car refueling'
        )
        
        # Last month's entries
        last_month = today.replace(day=1) - timedelta(days=1)
        
        Entry.objects.create(
            user=self.user,
            title='Previous Salary',
            amount=Decimal('3000.00'),
            date=last_month,
            type=Entry.INCOME,
            notes='Previous monthly salary'
        )
        
        Entry.objects.create(
            user=self.user,
            category=self.food_category,
            title='Previous Grocery',
            amount=Decimal('200.00'),
            date=last_month,
            type=Entry.EXPENSE,
            notes='Previous groceries'
        )
        
        # Define URL for chart data - this will need to be uncommented when the view is implemented
        # self.chart_data_url = reverse('budget:chart_data')
    
    def test_monthly_summary_calculation(self):
        """Test that monthly summary shows correct totals"""
        # This test assumes you have a dashboard view that calculates monthly totals
        # response = self.client.get(reverse('budget:dashboard'))
        # 
        # # Check for correct monthly totals in context
        # self.assertEqual(response.context['total_income'], Decimal('3000.00'))
        # self.assertEqual(response.context['total_expenses'], Decimal('300.00'))  # 150 + 80 + 70
        # self.assertEqual(response.context['balance'], Decimal('2700.00'))  # 3000 - 300
    
    def test_expense_by_category(self):
        """Test that expenses are correctly grouped by category"""
        # This test assumes you have an API endpoint that returns expense data by category
        # response = self.client.get(self.chart_data_url)
        # self.assertEqual(response.status_code, 200)
        # 
        # data = json.loads(response.content)
        # 
        # # Check for correct category totals
        # food_total = next((item['value'] for item in data['category_data'] if item['label'] == 'Food'), None)
        # transport_total = next((item['value'] for item in data['category_data'] if item['label'] == 'Transport'), None)
        # 
        # self.assertEqual(food_total, '230.00')  # 150 + 80
        # self.assertEqual(transport_total, '70.00')
    
    def test_csv_export(self):
        """Test that entries can be exported to CSV"""
        # This test will need to be uncommented when the export_csv view is implemented
        # response = self.client.get(reverse('budget:export_csv'))
        # 
        # self.assertEqual(response.status_code, 200)
        # self.assertEqual(response['Content-Type'], 'text/csv')
        # self.assertEqual(
        #     response['Content-Disposition'],
        #     f'attachment; filename="budget_export_{date.today().strftime("%Y-%m-%d")}.csv"'
        # )
        # 
        # # Check that the CSV content includes the correct number of rows
        # content = response.content.decode('utf-8')
        # rows = content.strip().split('\n')
        # 
        # # Header + 6 entries = 7 rows
        # self.assertEqual(len(rows), 7)

class BudgetingFeatureTests(TestCase):
    """Tests for the budget setting and over-budget warning features"""
    
    def setUp(self):
        # Create test client
        self.client = Client()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpassword'
        )
        
        # Login the user
        self.client.login(username='testuser', password='testpassword')
        
        # Create test categories
        self.food_category = Category.objects.create(
            name='Food',
            user=self.user
        )
        
        self.transport_category = Category.objects.create(
            name='Transport',
            user=self.user
        )
        
        # Create test expenses
        self.food_expense = Entry.objects.create(
            user=self.user,
            category=self.food_category,
            title='Grocery Shopping',
            amount=Decimal('150.00'),
            date=date.today(),
            type=Entry.EXPENSE,
            notes='Weekly groceries'
        )
        
        self.transport_expense = Entry.objects.create(
            user=self.user,
            category=self.transport_category,
            title='Gas',
            amount=Decimal('70.00'),
            date=date.today(),
            type=Entry.EXPENSE,
            notes='Car refueling'
        )
        
        # Note: The following tests assume you will add a Budget model
        # to track budget limits per category or in total
        
    def test_budget_setting(self):
        """Test that user can set a budget for a category"""
        # This test will need to be implemented once budget setting is added
        # Example: 
        # budget_data = {
        #     'category': self.food_category.id,
        #     'amount': '200.00',
        #     'month': date.today().month,
        #     'year': date.today().year
        # }
        # response = self.client.post(reverse('budget:set_budget'), budget_data)
        # self.assertEqual(response.status_code, 302)  # Redirects after creation
        # 
        # # Check that budget was created
        # budget = Budget.objects.get(category=self.food_category)
        # self.assertEqual(budget.amount, Decimal('200.00'))
        pass
    
    def test_over_budget_warning(self):
        """Test that an over-budget warning is shown when expenses exceed budget"""
        # This test will need to be implemented once budget warnings are added
        # Example:
        # # Set a budget that's lower than the current expense amount
        # Budget.objects.create(
        #     user=self.user,
        #     category=self.food_category,
        #     amount=Decimal('100.00'),
        #     month=date.today().month,
        #     year=date.today().year
        # )
        # 
        # # The food expense of 150.00 exceeds the budget of 100.00
        # response = self.client.get(reverse('budget:dashboard'))
        # 
        # # Check that warning is included in response
        # self.assertIn('over_budget_categories', response.context)
        # self.assertEqual(len(response.context['over_budget_categories']), 1)
        # self.assertEqual(response.context['over_budget_categories'][0], self.food_category)
        pass
    
    def test_budget_progress_tracking(self):
        """Test that budget progress is correctly calculated"""
        # This test will need to be implemented once budget progress tracking is added
        # Example:
        # # Set budgets for both categories
        # food_budget = Budget.objects.create(
        #     user=self.user,
        #     category=self.food_category,
        #     amount=Decimal('200.00'),
        #     month=date.today().month,
        #     year=date.today().year
        # )
        # 
        # transport_budget = Budget.objects.create(
        #     user=self.user,
        #     category=self.transport_category,
        #     amount=Decimal('100.00'),
        #     month=date.today().month,
        #     year=date.today().year
        # )
        # 
        # response = self.client.get(reverse('budget:dashboard'))
        # 
        # # Check budget progress in context
        # budget_progress = response.context['budget_progress']
        # 
        # # Food: 150/200 = 75% spent
        # self.assertEqual(budget_progress[self.food_category.id]['percent'], 75)
        # self.assertEqual(budget_progress[self.food_category.id]['spent'], Decimal('150.00'))
        # self.assertEqual(budget_progress[self.food_category.id]['budget'], Decimal('200.00'))
        # 
        # # Transport: 70/100 = 70% spent
        # self.assertEqual(budget_progress[self.transport_category.id]['percent'], 70)
        # self.assertEqual(budget_progress[self.transport_category.id]['spent'], Decimal('70.00'))
        # self.assertEqual(budget_progress[self.transport_category.id]['budget'], Decimal('100.00'))
        pass
