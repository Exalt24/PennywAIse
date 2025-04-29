from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from ..models import Category, Entry

User = get_user_model()

class SecurityTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.dashboard_url = reverse('budget:dashboard')
        self.auth_url = reverse('budget:auth')
        
        # Create two users with their own data
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
        
        # Create categories for both users
        self.category1 = Category.objects.create(
            name='Food',
            user=self.user1
        )
        
        self.category2 = Category.objects.create(
            name='Entertainment',
            user=self.user2
        )
        
        # Create entries for both users
        self.entry1 = Entry.objects.create(
            user=self.user1,
            category=self.category1,
            title='User1 Groceries',
            amount=Decimal('50.00'),
            date=timezone.now().date(),
            type=Entry.EXPENSE,
            notes='User1 shopping'
        )
        
        self.entry2 = Entry.objects.create(
            user=self.user2,
            category=self.category2,
            title='User2 Movies',
            amount=Decimal('20.00'),
            date=timezone.now().date(),
            type=Entry.EXPENSE,
            notes='User2 entertainment'
        )
    
    def test_dashboard_access_without_login(self):
        """Test that unauthenticated users cannot access the dashboard"""
        response = self.client.get(self.dashboard_url)
        self.assertNotEqual(response.status_code, 200)  # Should not be 200 OK
        
    def test_user_data_isolation(self):
        """Test that one user cannot see another user's data"""
        # Login as user1
        self.client.login(username='user1', password='User1@123')
        
        # Access dashboard
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)
        
        # Check that only user1's data is in the context
        # 1. Check categories
        self.assertEqual(len(response.context['user_categories']), 1)
        self.assertEqual(response.context['user_categories'][0].name, 'Food')
        
        # 2. Check entries
        for entry in response.context['recent_transactions']:
            self.assertEqual(entry.user, self.user1)
            
        # 3. Check transactions count
        self.assertEqual(response.context['transaction_count'], 1)
            
        # Check that user2's data is not accessible
        # Check that we can't see user2's entry
        entries = response.context['recent_transactions']
        entry_titles = [e.title for e in entries]
        self.assertNotIn('User2 Movies', entry_titles)
        
        # Logout and login as user2
        self.client.logout()
        self.client.login(username='user2', password='User2@123')
        
        # Access dashboard
        response = self.client.get(self.dashboard_url)
        
        # Check that only user2's data is in the context
        # Similar checks for user2
        self.assertEqual(len(response.context['user_categories']), 1)
        self.assertEqual(response.context['user_categories'][0].name, 'Entertainment')
        
        # Check that user1's data is not accessible
        entries = response.context['recent_transactions']
        entry_titles = [e.title for e in entries]
        self.assertNotIn('User1 Groceries', entry_titles)
    
    def test_user_cannot_modify_others_data(self):
        """Test that one user cannot modify another user's data"""
        # Login as user1
        self.client.login(username='user1', password='User1@123')
        
        # Try to edit user2's entry
        response = self.client.post(self.dashboard_url, {
            'add-entry': 'add',
            'entry-id': str(self.entry2.id),
            'title': 'Hacked entry',
            'amount': '999.99',
            'date': timezone.now().date().isoformat(),
            'type': Entry.EXPENSE,
            'category': self.category1.id,
            'notes': 'This should not work'
        })
        
        # Should get a 404 or similar error, not 200 or redirect
        self.assertEqual(response.status_code, 404)
        
        # Check that user2's entry was not modified
        self.entry2.refresh_from_db()
        self.assertEqual(self.entry2.title, 'User2 Movies')
        self.assertEqual(self.entry2.amount, Decimal('20.00'))
        
        # Try to delete user2's entry
        response = self.client.post(self.dashboard_url, {
            'delete-entry': str(self.entry2.id)
        })
        
        # Should get a 404 or similar error
        self.assertEqual(response.status_code, 404)
        
        # Check that user2's entry still exists
        self.assertTrue(Entry.objects.filter(id=self.entry2.id).exists())
        
        # Try to add a category for user2
        response = self.client.post(self.dashboard_url, {
            'add-category': 'add',
            'name': 'Hacked Category',
            'user': self.user2.id  # This would be rejected by the server-side check
        })
        
        # Even if it redirects, the category should be created for user1, not user2
        categories = Category.objects.filter(name='Hacked Category')
        for cat in categories:
            self.assertNotEqual(cat.user, self.user2)
    
    def test_session_fixation_protection(self):
        """Test protection against session fixation attacks"""
        # Get a session ID before logging in
        response = self.client.get(self.auth_url)
        pre_login_session_id = self.client.session.session_key
        
        # Login
        self.client.post(self.auth_url, {
            'login-submit': 'login',
            'email': 'user1@example.com',
            'password': 'User1@123'
        })
        
        # Get the new session ID
        post_login_session_id = self.client.session.session_key
        
        # Session ID should change after login to prevent session fixation
        self.assertNotEqual(pre_login_session_id, post_login_session_id)
    
    def test_csrf_protection(self):
        """Test CSRF protection"""
        # Login first
        self.client.login(username='user1', password='User1@123')
        
        # Get the dashboard page to get a CSRF token
        response = self.client.get(self.dashboard_url)
        
        # Create a client with CSRF checks disabled
        csrf_disabled_client = Client(enforce_csrf_checks=True)
        csrf_disabled_client.login(username='user1', password='User1@123')
        
        # Try to post without CSRF token
        response = csrf_disabled_client.post(self.dashboard_url, {
            'add-entry': 'add',
            'title': 'CSRF Test',
            'amount': '10.00',
            'date': timezone.now().date().isoformat(),
            'type': Entry.EXPENSE,
            'category': self.category1.id
        })
        
        # Request should be rejected with 403 Forbidden
        self.assertEqual(response.status_code, 403)
        
        # Entry should not be created
        self.assertFalse(Entry.objects.filter(title='CSRF Test').exists()) 