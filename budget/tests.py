from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from .models import Category, Entry
from .forms import EntryForm, CategoryForm, LoginForm, RegisterForm

# Import all tests from modularized test files
from .test_models import CategoryModelTest, EntryModelTest
from .test_forms import CategoryFormTest, EntryFormTest, LoginFormTest, RegisterFormTest
from .test_views import IndexViewTest, AuthViewTest, DashboardViewTest
from .test_security import SecurityTest
from .test_integration import BudgetTrackerIntegrationTest, MultipleUserIntegrationTest

User = get_user_model()

class CategoryModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.category = Category.objects.create(
            name='Food',
            user=self.user
        )
    
    def test_category_creation(self):
        """Test that a category can be created correctly"""
        self.assertEqual(self.category.name, 'Food')
        self.assertEqual(self.category.user, self.user)
        self.assertEqual(str(self.category), 'Food')
        
    def test_category_user_relationship(self):
        """Test that categories are correctly associated with users"""
        user_categories = Category.objects.filter(user=self.user)
        self.assertEqual(user_categories.count(), 1)
        self.assertEqual(user_categories.first(), self.category)

class EntryModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.category = Category.objects.create(
            name='Food',
            user=self.user
        )
        self.entry = Entry.objects.create(
            user=self.user,
            category=self.category,
            title='Groceries',
            amount=Decimal('50.00'),
            date=timezone.now().date(),
            type=Entry.EXPENSE,
            notes='Weekly shopping'
        )
    
    def test_entry_creation(self):
        """Test that an entry can be created correctly"""
        self.assertEqual(self.entry.title, 'Groceries')
        self.assertEqual(self.entry.amount, Decimal('50.00'))
        self.assertEqual(self.entry.type, Entry.EXPENSE)
        self.assertEqual(self.entry.category, self.category)
        self.assertEqual(self.entry.user, self.user)
        
    def test_entry_user_relationship(self):
        """Test that entries are correctly associated with users"""
        user_entries = Entry.objects.filter(user=self.user)
        self.assertEqual(user_entries.count(), 1)
        self.assertEqual(user_entries.first(), self.entry)

class CategoryFormTest(TestCase):
    def test_category_form_valid(self):
        """Test that the category form validates correctly"""
        form = CategoryForm(data={'name': 'Transportation'})
        self.assertTrue(form.is_valid())
    
    def test_category_form_empty(self):
        """Test that the category form requires a name"""
        form = CategoryForm(data={'name': ''})
        self.assertFalse(form.is_valid())

class EntryFormTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.category = Category.objects.create(
            name='Food',
            user=self.user
        )
        self.valid_data = {
            'title': 'Groceries',
            'amount': Decimal('50.00'),
            'date': timezone.now().date(),
            'type': Entry.EXPENSE,
            'category': self.category.id,
            'notes': 'Weekly shopping'
        }
    
    def test_entry_form_valid(self):
        """Test that the entry form validates correctly with valid data"""
        form = EntryForm(data=self.valid_data, user=self.user)
        self.assertTrue(form.is_valid())
    
    def test_entry_form_amount_validation(self):
        """Test amount validation in the entry form"""
        # Test with zero amount
        data = self.valid_data.copy()
        data['amount'] = 0
        form = EntryForm(data=data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('amount', form.errors)
        
        # Test with negative amount
        data['amount'] = -10
        form = EntryForm(data=data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('amount', form.errors)
    
    def test_entry_form_date_validation(self):
        """Test date validation in the entry form"""
        # Test with future date
        future_date = timezone.now().date() + timezone.timedelta(days=10)
        data = self.valid_data.copy()
        data['date'] = future_date
        form = EntryForm(data=data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('date', form.errors)

    def test_entry_form_user_categories(self):
        """Test that entry form only shows categories for the current user"""
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpass123'
        )
        other_category = Category.objects.create(
            name='Other Food',
            user=other_user
        )
        
        # Form for first user should only show their categories
        form = EntryForm(user=self.user)
        self.assertIn(self.category, form.fields['category'].queryset)
        self.assertNotIn(other_category, form.fields['category'].queryset)

class AuthViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.auth_url = reverse('budget:auth')
        self.dashboard_url = reverse('budget:dashboard')
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='Test@123'
        )
    
    def test_auth_page_load(self):
        """Test that auth page loads correctly"""
        response = self.client.get(self.auth_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'auth.html')
    
    def test_login_success(self):
        """Test successful login"""
        response = self.client.post(self.auth_url, {
            'login-submit': 'login',
            'email': 'test@example.com',
            'password': 'Test@123'
        })
        self.assertRedirects(response, self.dashboard_url)
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = self.client.post(self.auth_url, {
            'login-submit': 'login',
            'email': 'test@example.com',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'auth.html')
        self.assertContains(response, "Invalid email or password")
    
    def test_register_success(self):
        """Test successful user registration"""
        response = self.client.post(self.auth_url, {
            'register-submit': 'register',
            'username': 'newuser',
            'email': 'new@example.com',
            'password1': 'New@123456',
            'password2': 'New@123456'
        })
        self.assertRedirects(response, self.dashboard_url)
        self.assertTrue(User.objects.filter(email='new@example.com').exists())
    
    def test_register_duplicate_email(self):
        """Test registration with duplicate email"""
        response = self.client.post(self.auth_url, {
            'register-submit': 'register',
            'username': 'anotheruser',
            'email': 'test@example.com',  # Already exists
            'password1': 'Test@123456',
            'password2': 'Test@123456'
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'auth.html')
        self.assertContains(response, "email address is already in use")

class DashboardViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.dashboard_url = reverse('budget:dashboard')
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='Test@123'
        )
        self.category = Category.objects.create(
            name='Food',
            user=self.user
        )
        self.income_entry = Entry.objects.create(
            user=self.user,
            title='Salary',
            amount=Decimal('1000.00'),
            date=timezone.now().date(),
            type=Entry.INCOME,
            notes='Monthly salary'
        )
        self.expense_entry = Entry.objects.create(
            user=self.user,
            category=self.category,
            title='Groceries',
            amount=Decimal('50.00'),
            date=timezone.now().date(),
            type=Entry.EXPENSE,
            notes='Weekly shopping'
        )
        # Login the user
        self.client.login(username='testuser', password='Test@123')
    
    def test_dashboard_requires_login(self):
        """Test that dashboard requires user login"""
        # Logout the user
        self.client.logout()
        response = self.client.get(self.dashboard_url)
        self.assertNotEqual(response.status_code, 200)
    
    def test_dashboard_context(self):
        """Test that dashboard provides the correct context data"""
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard.html')
        
        # Check context data
        self.assertEqual(response.context['income_total'], Decimal('1000.00'))
        self.assertEqual(response.context['expense_total'], Decimal('50.00'))
        self.assertEqual(response.context['net_balance'], Decimal('950.00'))
        self.assertEqual(response.context['transaction_count'], 2)
        
        # Check that forms are in context
        self.assertIn('category_form', response.context)
        self.assertIn('entry_form', response.context)
        
        # Check that entries and categories are filtered by user
        self.assertEqual(len(response.context['recent_transactions']), 2)
        self.assertEqual(len(response.context['user_categories']), 1)
    
    def test_add_category(self):
        """Test adding a new category"""
        response = self.client.post(self.dashboard_url, {
            'add-category': 'add',
            'name': 'Entertainment'
        })
        self.assertRedirects(response, self.dashboard_url)
        self.assertTrue(Category.objects.filter(user=self.user, name='Entertainment').exists())
    
    def test_add_entry(self):
        """Test adding a new entry"""
        response = self.client.post(self.dashboard_url, {
            'add-entry': 'add',
            'title': 'Movie tickets',
            'amount': '20.00',
            'date': timezone.now().date().isoformat(),
            'type': Entry.EXPENSE,
            'category': self.category.id,
            'notes': 'Weekend movie'
        })
        self.assertRedirects(response, self.dashboard_url)
        self.assertTrue(Entry.objects.filter(user=self.user, title='Movie tickets').exists())
    
    def test_edit_entry(self):
        """Test editing an existing entry"""
        response = self.client.post(self.dashboard_url, {
            'add-entry': 'add',
            'entry-id': str(self.expense_entry.id),
            'title': 'Updated groceries',
            'amount': '60.00',
            'date': timezone.now().date().isoformat(),
            'type': Entry.EXPENSE,
            'category': self.category.id,
            'notes': 'Updated weekly shopping'
        })
        self.assertRedirects(response, self.dashboard_url)
        updated_entry = Entry.objects.get(id=self.expense_entry.id)
        self.assertEqual(updated_entry.title, 'Updated groceries')
        self.assertEqual(updated_entry.amount, Decimal('60.00'))
    
    def test_delete_entry(self):
        """Test deleting an entry"""
        response = self.client.post(self.dashboard_url, {
            'delete-entry': str(self.expense_entry.id)
        })
        self.assertRedirects(response, self.dashboard_url)
        self.assertFalse(Entry.objects.filter(id=self.expense_entry.id).exists())
    
    def test_edit_nonexistent_entry(self):
        """Test attempting to edit a nonexistent entry"""
        response = self.client.get(f"{self.dashboard_url}?edit=9999")  # Assume ID 9999 doesn't exist
        self.assertEqual(response.status_code, 404)  # Should return 404 Not Found

class IndexViewTest(TestCase):
    def test_index_view(self):
        """Test that the index page loads correctly"""
        response = self.client.get(reverse('budget:index'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'index.html')
