from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from .models import Category, Entry

User = get_user_model()

class IndexViewTest(TestCase):
    def test_index_view(self):
        """Test that the index page loads correctly"""
        response = self.client.get(reverse('budget:index'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'index.html')

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
        # Check that user is logged in
        self.assertTrue(response.wsgi_request.user.is_authenticated)
    
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
        # Check that user is not logged in
        self.assertFalse(response.wsgi_request.user.is_authenticated)
    
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
        # Check that user is logged in
        self.assertTrue(response.wsgi_request.user.is_authenticated)
    
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
        # Check that user is not logged in
        self.assertFalse(response.wsgi_request.user.is_authenticated)

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
        # Should redirect to login page
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
    
    def test_delete_nonexistent_entry(self):
        """Test attempting to delete a nonexistent entry"""
        response = self.client.post(self.dashboard_url, {
            'delete-entry': '9999'  # Assume ID 9999 doesn't exist
        })
        self.assertEqual(response.status_code, 404)  # Should return 404 Not Found
    
    def test_edit_entry_from_other_user(self):
        """Test attempting to edit an entry belonging to another user"""
        # Create another user with their own entry
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='Other@123'
        )
        other_entry = Entry.objects.create(
            user=other_user,
            title='Other expense',
            amount=Decimal('30.00'),
            date=timezone.now().date(),
            type=Entry.EXPENSE,
            notes='Expense from other user'
        )
        
        # Attempt to edit the other user's entry
        response = self.client.get(f"{self.dashboard_url}?edit={other_entry.id}")
        self.assertEqual(response.status_code, 404)  # Should return 404 Not Found
        
        # Attempt to post edit to the other user's entry
        response = self.client.post(self.dashboard_url, {
            'add-entry': 'add',
            'entry-id': str(other_entry.id),
            'title': 'Trying to edit other users entry',
            'amount': '100.00',
            'date': timezone.now().date().isoformat(),
            'type': Entry.EXPENSE,
            'category': self.category.id,
            'notes': 'Should not work'
        })
        self.assertEqual(response.status_code, 404)  # Should return 404 Not Found
        
        # Check that the entry was not modified
        other_entry.refresh_from_db()
        self.assertEqual(other_entry.title, 'Other expense')
    
    def test_delete_entry_from_other_user(self):
        """Test attempting to delete an entry belonging to another user"""
        # Create another user with their own entry
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='Other@123'
        )
        other_entry = Entry.objects.create(
            user=other_user,
            title='Other expense',
            amount=Decimal('30.00'),
            date=timezone.now().date(),
            type=Entry.EXPENSE,
            notes='Expense from other user'
        )
        
        # Attempt to delete the other user's entry
        response = self.client.post(self.dashboard_url, {
            'delete-entry': str(other_entry.id)
        })
        self.assertEqual(response.status_code, 404)  # Should return 404 Not Found
        
        # Check that the entry still exists
        self.assertTrue(Entry.objects.filter(id=other_entry.id).exists()) 