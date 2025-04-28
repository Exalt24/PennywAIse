from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
from .models import Category, Entry
from .forms import EntryForm, CategoryForm, LoginForm, RegisterForm

User = get_user_model()

class CategoryFormTest(TestCase):
    def test_category_form_valid(self):
        """Test that the category form validates correctly"""
        form = CategoryForm(data={'name': 'Transportation'})
        self.assertTrue(form.is_valid())
    
    def test_category_form_empty(self):
        """Test that the category form requires a name"""
        form = CategoryForm(data={'name': ''})
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)

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
    
    def test_entry_form_title_validation(self):
        """Test title validation in the entry form"""
        # Test with empty title
        data = self.valid_data.copy()
        data['title'] = ''
        form = EntryForm(data=data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('title', form.errors)
        
        # Test with whitespace title
        data['title'] = '   '
        form = EntryForm(data=data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('title', form.errors)
    
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
        future_date = timezone.now().date() + timedelta(days=10)
        data = self.valid_data.copy()
        data['date'] = future_date
        form = EntryForm(data=data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('date', form.errors)
    
    def test_entry_form_type_validation(self):
        """Test type validation in the entry form"""
        # Test with invalid type
        data = self.valid_data.copy()
        data['type'] = 'INVALID'
        form = EntryForm(data=data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('type', form.errors)
    
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

class LoginFormTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='Test@123'
        )
    
    def test_login_form_valid(self):
        """Test that the login form validates correctly with valid data"""
        form = LoginForm(data={
            'email': 'test@example.com',
            'password': 'Test@123'
        })
        self.assertTrue(form.is_valid())
    
    def test_login_form_invalid_email(self):
        """Test login form with invalid email format"""
        form = LoginForm(data={
            'email': 'invalid-email',
            'password': 'Test@123'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
    
    def test_login_form_nonexistent_email(self):
        """Test login form with email that doesn't exist in the database"""
        form = LoginForm(data={
            'email': 'nonexistent@example.com',
            'password': 'Test@123'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
    
    def test_login_form_password_validation(self):
        """Test login form password validation"""
        form = LoginForm(data={
            'email': 'test@example.com',
            'password': 'short'  # Too short
        })
        self.assertFalse(form.is_valid())
        self.assertIn('password', form.errors)

class RegisterFormTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='Test@123'
        )
        self.valid_data = {
            'username': 'newuser',
            'email': 'new@example.com',
            'password1': 'New@12345',
            'password2': 'New@12345'
        }
    
    def test_register_form_valid(self):
        """Test that the register form validates correctly with valid data"""
        form = RegisterForm(data=self.valid_data)
        self.assertTrue(form.is_valid())
    
    def test_register_form_password_mismatch(self):
        """Test register form with mismatched passwords"""
        data = self.valid_data.copy()
        data['password2'] = 'Different@12345'
        form = RegisterForm(data=data)
        self.assertFalse(form.is_valid())
    
    def test_register_form_email_exists(self):
        """Test register form with existing email"""
        data = self.valid_data.copy()
        data['email'] = 'test@example.com'  # Already exists
        form = RegisterForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
    
    def test_register_form_username_exists(self):
        """Test register form with existing username"""
        data = self.valid_data.copy()
        data['username'] = 'testuser'  # Already exists
        form = RegisterForm(data=data)
        self.assertFalse(form.is_valid())
    
    def test_register_form_password_validation(self):
        """Test register form password validation rules"""
        # Test password without special character
        data = self.valid_data.copy()
        data['password1'] = 'New12345'
        data['password2'] = 'New12345'
        form = RegisterForm(data=data)
        self.assertFalse(form.is_valid())
        
        # Test password without number
        data['password1'] = 'New@abcde'
        data['password2'] = 'New@abcde'
        form = RegisterForm(data=data)
        self.assertFalse(form.is_valid())
        
        # Test password too short
        data['password1'] = 'N@1'
        data['password2'] = 'N@1'
        form = RegisterForm(data=data)
        self.assertFalse(form.is_valid()) 