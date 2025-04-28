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
        # 1. Visit index page
        response = self.client.get(self.index_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'index.html')
        
        # 2. Go to auth page
        response = self.client.get(self.auth_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'auth.html')
        
        # 3. Login
        response = self.client.post(self.auth_url, {
            'login-submit': 'login',
            'email': 'test@example.com',
            'password': 'Test@123'
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard.html')
        
        # 4. Add a category
        response = self.client.post(self.dashboard_url, {
            'add-category': 'add',
            'name': 'Food'
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Category.objects.filter(user=self.user, name='Food').exists())
        category = Category.objects.get(user=self.user, name='Food')
        
        # 5. Add an expense entry
        response = self.client.post(self.dashboard_url, {
            'add-entry': 'add',
            'title': 'Groceries',
            'amount': '50.00',
            'date': timezone.now().date().isoformat(),
            'type': Entry.EXPENSE,
            'category': category.id,
            'notes': 'Weekly shopping'
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Entry.objects.filter(user=self.user, title='Groceries').exists())
        expense_entry = Entry.objects.get(user=self.user, title='Groceries')
        
        # 6. Add an income entry
        response = self.client.post(self.dashboard_url, {
            'add-entry': 'add',
            'title': 'Salary',
            'amount': '1000.00',
            'date': timezone.now().date().isoformat(),
            'type': Entry.INCOME,
            'category': '',  # Income might not need a category
            'notes': 'Monthly salary'
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Entry.objects.filter(user=self.user, title='Salary').exists())
        
        # 7. Check dashboard context after adding entries
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)
        
        # Verify financial totals
        self.assertEqual(response.context['income_total'], Decimal('1000.00'))
        self.assertEqual(response.context['expense_total'], Decimal('50.00'))
        self.assertEqual(response.context['net_balance'], Decimal('950.00'))
        self.assertEqual(response.context['transaction_count'], 2)
        
        # 8. Edit an expense entry
        response = self.client.post(self.dashboard_url, {
            'add-entry': 'add',
            'entry-id': str(expense_entry.id),
            'title': 'Updated Groceries',
            'amount': '60.00',
            'date': timezone.now().date().isoformat(),
            'type': Entry.EXPENSE,
            'category': category.id,
            'notes': 'Updated weekly shopping'
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        
        # Verify the entry was updated
        expense_entry.refresh_from_db()
        self.assertEqual(expense_entry.title, 'Updated Groceries')
        self.assertEqual(expense_entry.amount, Decimal('60.00'))
        
        # 9. Check dashboard again after update
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)
        
        # Verify updated financial totals
        self.assertEqual(response.context['income_total'], Decimal('1000.00'))
        self.assertEqual(response.context['expense_total'], Decimal('60.00'))
        self.assertEqual(response.context['net_balance'], Decimal('940.00'))
        
        # 10. Delete an entry
        response = self.client.post(self.dashboard_url, {
            'delete-entry': str(expense_entry.id)
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        
        # Verify the entry was deleted
        self.assertFalse(Entry.objects.filter(id=expense_entry.id).exists())
        
        # 11. Check dashboard again after deletion
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)
        
        # Verify updated financial totals (only income should remain)
        self.assertEqual(response.context['income_total'], Decimal('1000.00'))
        self.assertEqual(response.context['expense_total'], Decimal('0'))
        self.assertEqual(response.context['net_balance'], Decimal('1000.00'))
        self.assertEqual(response.context['transaction_count'], 1)
        
        # 12. Logout
        self.client.logout()
        
        # Try to access dashboard after logout - should not be accessible
        response = self.client.get(self.dashboard_url)
        self.assertNotEqual(response.status_code, 200)

class MultipleUserIntegrationTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.auth_url = reverse('budget:auth')
        self.dashboard_url = reverse('budget:dashboard')
        
        # Create two users
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='User1@123'
        )
        
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='User2@123'
        )
    
    def test_category_isolation(self):
        """Test that categories are properly isolated between users"""
        # Login as user1
        self.client.login(username='user1', password='User1@123')
        
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
        self.client.login(username='user2', password='User2@123')
        
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
        # Set up categories for both users
        category1 = Category.objects.create(name='Food', user=self.user1)
        category2 = Category.objects.create(name='Entertainment', user=self.user2)
        
        # Login as user1
        self.client.login(username='user1', password='User1@123')
        
        # Add an income entry for user1
        self.client.post(self.dashboard_url, {
            'add-entry': 'add',
            'title': 'User1 Salary',
            'amount': '1000.00',
            'date': timezone.now().date().isoformat(),
            'type': Entry.INCOME,
            'notes': 'User1 monthly salary'
        })
        
        # Add an expense entry for user1
        self.client.post(self.dashboard_url, {
            'add-entry': 'add',
            'title': 'User1 Groceries',
            'amount': '50.00',
            'date': timezone.now().date().isoformat(),
            'type': Entry.EXPENSE,
            'category': category1.id,
            'notes': 'User1 weekly shopping'
        })
        
        # Verify correct calculations for user1
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.context['income_total'], Decimal('1000.00'))
        self.assertEqual(response.context['expense_total'], Decimal('50.00'))
        self.assertEqual(response.context['net_balance'], Decimal('950.00'))
        self.assertEqual(response.context['transaction_count'], 2)
        
        # Logout and login as user2
        self.client.logout()
        self.client.login(username='user2', password='User2@123')
        
        # Add an income entry for user2
        self.client.post(self.dashboard_url, {
            'add-entry': 'add',
            'title': 'User2 Salary',
            'amount': '2000.00',
            'date': timezone.now().date().isoformat(),
            'type': Entry.INCOME,
            'notes': 'User2 monthly salary'
        })
        
        # Add an expense entry for user2
        self.client.post(self.dashboard_url, {
            'add-entry': 'add',
            'title': 'User2 Movies',
            'amount': '20.00',
            'date': timezone.now().date().isoformat(),
            'type': Entry.EXPENSE,
            'category': category2.id,
            'notes': 'User2 entertainment'
        })
        
        # Verify correct calculations for user2
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.context['income_total'], Decimal('2000.00'))
        self.assertEqual(response.context['expense_total'], Decimal('20.00'))
        self.assertEqual(response.context['net_balance'], Decimal('1980.00'))
        self.assertEqual(response.context['transaction_count'], 2)
        
        # Verify totals across the system (both users combined)
        self.assertEqual(Entry.objects.count(), 4)
        self.assertEqual(Entry.objects.filter(type=Entry.INCOME).count(), 2)
        self.assertEqual(Entry.objects.filter(type=Entry.EXPENSE).count(), 2) 