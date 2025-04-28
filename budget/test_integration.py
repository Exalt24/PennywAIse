from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from .models import Category, Entry
import json

User = get_user_model()

class BudgetTrackerIntegrationTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.index_url = reverse('budget:index')
        self.auth_url = reverse('budget:auth')
        self.dashboard_url = reverse('budget:dashboard')
        
        # Create a test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='Test@123'
        )
    
    def test_full_user_journey(self):
        """Test the full user journey from landing page through multiple actions"""
        # Create some necessary data first
        Category.objects.create(name="Salary", user=self.user)
        Category.objects.create(name="Groceries", user=self.user)
        
        # 1. User visits the landing page
        response = self.client.get(reverse('budget:index'))
        self.assertEqual(response.status_code, 200)
        
        # 2. User logs in
        response = self.client.post(reverse('budget:auth'), {
            'login-submit': 'login',
            'email': 'test@example.com',
            'password': 'Test@123',
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard.html')
        
        # 3. User adds an income entry
        salary_category = Category.objects.get(name="Salary", user=self.user)
        response = self.client.post(reverse('budget:dashboard'), {
            'add-entry': 'add',
            'title': 'Salary',
            'amount': '1000.00',
            'date': timezone.now().date().isoformat(),
            'type': Entry.INCOME,
            'category': salary_category.id,
            'notes': 'Monthly salary'
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        
        # Ensure the entry was created
        self.assertTrue(Entry.objects.filter(user=self.user, title='Salary').exists())
        
        # 4. User adds an expense entry
        grocery_category = Category.objects.get(name="Groceries", user=self.user)
        response = self.client.post(reverse('budget:dashboard'), {
            'add-entry': 'add',
            'title': 'Weekly Groceries',
            'amount': '150.00',
            'date': timezone.now().date().isoformat(),
            'type': Entry.EXPENSE,
            'category': grocery_category.id,
            'notes': 'Weekly grocery shopping'
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        
        # Ensure both entries exist
        self.assertEqual(Entry.objects.filter(user=self.user).count(), 2)
        
        # 5. Check dashboard context after adding entries
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)
        
        # Verify financial totals
        self.assertEqual(response.context['income_total'], Decimal('1000.00'))
        self.assertEqual(response.context['expense_total'], Decimal('150.00'))
        self.assertEqual(response.context['net_balance'], Decimal('850.00'))
        self.assertEqual(response.context['transaction_count'], 2)
        
        # 6. Edit an expense entry
        expense_entry = Entry.objects.get(user=self.user, title='Weekly Groceries')
        response = self.client.post(self.dashboard_url, {
            'add-entry': 'add',
            'entry-id': str(expense_entry.id),
            'title': 'Updated Groceries',
            'amount': '160.00',
            'date': timezone.now().date().isoformat(),
            'type': Entry.EXPENSE,
            'category': grocery_category.id,
            'notes': 'Updated weekly shopping'
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        
        # Verify the entry was updated
        expense_entry.refresh_from_db()
        self.assertEqual(expense_entry.title, 'Updated Groceries')
        self.assertEqual(expense_entry.amount, Decimal('160.00'))
        
        # 7. Check dashboard again after update
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)
        
        # Verify updated financial totals
        self.assertEqual(response.context['income_total'], Decimal('1000.00'))
        self.assertEqual(response.context['expense_total'], Decimal('160.00'))
        self.assertEqual(response.context['net_balance'], Decimal('840.00'))
        
        # 8. Delete an entry
        response = self.client.post(self.dashboard_url, {
            'delete-entry': str(expense_entry.id)
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        
        # Verify the entry was deleted
        self.assertFalse(Entry.objects.filter(id=expense_entry.id).exists())
        
        # 9. Check dashboard again after deletion
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)
        
        # Verify updated financial totals (only income should remain)
        self.assertEqual(response.context['income_total'], Decimal('1000.00'))
        self.assertEqual(response.context['expense_total'], Decimal('0'))
        self.assertEqual(response.context['net_balance'], Decimal('1000.00'))
        self.assertEqual(response.context['transaction_count'], 1)
        
        # 10. Logout
        self.client.logout()
        
        # Try to access dashboard after logout - should not be accessible
        response = self.client.get(self.dashboard_url)
        self.assertNotEqual(response.status_code, 200)

class MultipleUserIntegrationTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.index_url = reverse('budget:index')
        self.auth_url = reverse('budget:auth')
        self.dashboard_url = reverse('budget:dashboard')
        
        # Create test users
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='password1'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='password2'
        )
    
    def test_category_isolation(self):
        """Test that categories are properly isolated between users"""
        # Login as user1
        self.client.login(username='user1', password='password1')
        
        # Add a category for user1
        self.client.post(self.dashboard_url, {
            'add-category': 'add',
            'name': 'Food'
        })
        
        # Verify user1 can see their category
        response = self.client.get(self.dashboard_url)
        self.assertEqual(len(response.context['user_categories']), 1)
        self.assertEqual(response.context['user_categories'][0].name, 'Food')
        
        # Logout and login as user2
        self.client.logout()
        self.client.login(username='user2', password='password2')
        
        # Add a different category for user2
        self.client.post(self.dashboard_url, {
            'add-category': 'add',
            'name': 'Entertainment'
        })
        
        # Verify user2 can only see their category, not user1's
        response = self.client.get(self.dashboard_url)
        self.assertEqual(len(response.context['user_categories']), 1)
        self.assertEqual(response.context['user_categories'][0].name, 'Entertainment')
        
        # Make sure we have two categories total, but each user only sees their own
        self.assertEqual(Category.objects.count(), 2)
    
    def test_entry_isolation_and_calculation(self):
        """Test that entries are isolated between users and calculations are correct"""
        # Create categories for both users
        cat1 = Category.objects.create(name="Salary1", user=self.user1)
        cat2 = Category.objects.create(name="Salary2", user=self.user2)
        
        # Add entries for user1
        Entry.objects.create(
            user=self.user1,
            category=cat1,
            title='Monthly Salary',
            amount=Decimal('1000.00'),
            date=timezone.now().date(),
            type=Entry.INCOME,
            notes='Monthly salary'
        )
        Entry.objects.create(
            user=self.user1,
            category=cat1,
            title='Groceries',
            amount=Decimal('200.00'),
            date=timezone.now().date(),
            type=Entry.EXPENSE,
            notes='Weekly groceries'
        )
        
        # Add entries for user2
        Entry.objects.create(
            user=self.user2,
            category=cat2,
            title='Freelance Income',
            amount=Decimal('500.00'),
            date=timezone.now().date(),
            type=Entry.INCOME,
            notes='Freelance work'
        )
        Entry.objects.create(
            user=self.user2,
            category=cat2,
            title='Dining Out',
            amount=Decimal('80.00'),
            date=timezone.now().date(),
            type=Entry.EXPENSE,
            notes='Restaurant dinner'
        )
        
        # Login as user1 and check dashboard
        self.client.login(username='user1', password='password1')
        response = self.client.get(self.dashboard_url)
        
        # Verify user1 sees only their entries
        self.assertEqual(response.context['income_total'], Decimal('1000.00'))
        self.assertEqual(response.context['expense_total'], Decimal('200.00'))
        self.assertEqual(response.context['net_balance'], Decimal('800.00'))
        self.assertEqual(response.context['transaction_count'], 2)
        
        # Logout and login as user2
        self.client.logout()
        self.client.login(username='user2', password='password2')
        response = self.client.get(self.dashboard_url)
        
        # Verify user2 sees only their entries
        self.assertEqual(response.context['income_total'], Decimal('500.00'))
        self.assertEqual(response.context['expense_total'], Decimal('80.00'))
        self.assertEqual(response.context['net_balance'], Decimal('420.00'))
        self.assertEqual(response.context['transaction_count'], 2)
        
        # Verify totals across the system (both users combined)
        self.assertEqual(Entry.objects.count(), 4)
        self.assertEqual(Entry.objects.filter(type=Entry.INCOME).count(), 2)
        self.assertEqual(Entry.objects.filter(type=Entry.EXPENSE).count(), 2) 