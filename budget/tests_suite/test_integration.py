from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from ..models import Category, Entry, Budget, EmailVerificationToken, PasswordResetToken, ContactMessage
import json
import uuid
from unittest.mock import patch, MagicMock
from datetime import timedelta

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
        self.assertTemplateUsed(response, 'main/dashboard.html')
        
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
        
        # 10. Set a budget (using the first day of the current month)
        month_start = timezone.now().date().replace(day=1)
        response = self.client.post(self.dashboard_url, {
            'set-budget': 'set',
            'category': '',  # Total budget (no category)
            'amount': '2000.00',
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        
        # Check if budget was set correctly
        self.assertTrue(Budget.objects.filter(user=self.user, category=None, month=month_start).exists())
        budget = Budget.objects.get(user=self.user, category=None, month=month_start)
        self.assertEqual(budget.amount, Decimal('2000.00'))
        
        # 11. Test CSV export
        response = self.client.get(f"{self.dashboard_url}?export=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertTrue('attachment; filename="report.csv"' in response['Content-Disposition'])
        
        # 12. Logout
        self.client.logout()
        
        # Try to access dashboard after logout - should not be accessible
        response = self.client.get(self.dashboard_url)
        self.assertRedirects(response, f"/auth/?next={self.dashboard_url}")

    def test_contact_form_submission(self):
        """Test submitting a contact form from the index page"""
        # Before submission
        self.assertEqual(ContactMessage.objects.count(), 0)
        
        # Submit contact form
        response = self.client.post(self.index_url, {
            'send-message': 'send',
            'name': 'Test Contact',
            'email': 'contact@example.com',
            'subject': 'Test Subject',
            'message': 'This is a test contact message'
        }, follow=True)
        
        # Check response and record creation
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ContactMessage.objects.count(), 1)
        
        # Verify message contents
        message = ContactMessage.objects.first()
        self.assertEqual(message.name, 'Test Contact')
        self.assertEqual(message.email, 'contact@example.com')
        self.assertEqual(message.subject, 'Test Subject')
        self.assertEqual(message.message, 'This is a test contact message')
        self.assertFalse(message.is_read)

    def test_invalid_form_submissions(self):
        """Test invalid form submissions to cover error paths"""
        # Login user
        self.client.login(username='testuser', password='Test@123')
        
        # Test invalid entry form (missing required fields)
        response = self.client.post(self.dashboard_url, {
            'add-entry': 'add',
            'title': '',  # Empty title
            'amount': 'not-a-number',  # Invalid amount
            'date': 'invalid-date',  # Invalid date
            'type': 'invalid-type',  # Invalid type
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        
        # Test invalid budget form
        response = self.client.post(self.dashboard_url, {
            'set-budget': 'set',
            'amount': 'not-a-number',  # Invalid amount
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        
        # Test invalid category form
        response = self.client.post(self.dashboard_url, {
            'add-category': 'add',
            'name': '',  # Empty name
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        
        # Test invalid category deletion (nonexistent ID)
        response = self.client.post(self.dashboard_url, {
            'delete-category': '999999',  # Nonexistent ID
        }, follow=True)
        self.assertEqual(response.status_code, 404)
        
        # Test invalid entry deletion (nonexistent ID)
        response = self.client.post(self.dashboard_url, {
            'delete-entry': '999999',  # Nonexistent ID
        }, follow=True)
        self.assertEqual(response.status_code, 404)

    def test_csv_export_with_filters(self):
        """Test CSV export with various filters"""
        # Login user
        self.client.login(username='testuser', password='Test@123')
        
        # Create category and entries
        category = Category.objects.create(name="Test Category", user=self.user)
        today = timezone.now().date()
        
        Entry.objects.create(
            user=self.user,
            title='Test Income',
            amount=Decimal('500.00'),
            date=today,
            type=Entry.INCOME,
            category=category
        )
        Entry.objects.create(
            user=self.user,
            title='Test Expense',
            amount=Decimal('200.00'),
            date=today,
            type=Entry.EXPENSE,
            category=category
        )
        
        # Test export with date filter
        response = self.client.get(f"{self.dashboard_url}?export=csv&from={today}&to={today}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        
        # Test export with type filter
        response = self.client.get(f"{self.dashboard_url}?export=csv&type={Entry.INCOME}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        
        # Test export with category filter
        response = self.client.get(f"{self.dashboard_url}?export=csv&category={category.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        
        # Test export with all filters combined
        response = self.client.get(
            f"{self.dashboard_url}?export=csv&from={today}&to={today}&type={Entry.INCOME}&category={category.id}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')

class EntriesFilterTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.entries_filter_url = reverse('budget:entries-filter')
        
        # Create a test user
        self.user = User.objects.create_user(
            username='filteruser',
            email='filter@example.com',
            password='Filter@123'
        )
        
        # Create a category
        self.category = Category.objects.create(name="Test Category", user=self.user)
        
        # Create test entries
        Entry.objects.create(
            user=self.user,
            category=self.category,
            title='Income Entry',
            amount=Decimal('1000.00'),
            date=timezone.now().date(),
            type=Entry.INCOME,
            notes='Test income'
        )
        Entry.objects.create(
            user=self.user,
            category=self.category,
            title='Expense Entry',
            amount=Decimal('200.00'),
            date=timezone.now().date(),
            type=Entry.EXPENSE,
            notes='Test expense'
        )
    
    def test_entries_filter(self):
        """Test the entries filter endpoint"""
        # Login user
        self.client.login(username='filteruser', password='Filter@123')
        
        # Make AJAX request for income entries
        response = self.client.get(
            f"{self.entries_filter_url}?type=IN",
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        # Check response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('entries_html', data)
        
        # Make AJAX request for expense entries
        response = self.client.get(
            f"{self.entries_filter_url}?type=EX",
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        # Check response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('entries_html', data)

    def test_unauthorized_access(self):
        """Test that unauthorized users cannot access the entries filter"""
        # Try to access without login
        response = self.client.get(
            self.entries_filter_url,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        # Should redirect to login page
        self.assertEqual(response.status_code, 302)
        
        # Login as different user
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='Other@123'
        )
        self.client.login(username='otheruser', password='Other@123')
        
        # Make request - should not see entries from first user
        response = self.client.get(
            self.entries_filter_url,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        # Should have response but with no entries
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('entries_html', data)
        # HTML should not contain entries from other user
        self.assertNotIn('Income Entry', data['entries_html'])
        self.assertNotIn('Expense Entry', data['entries_html'])

    def test_filter_with_parameters(self):
        """Test filtering with additional parameters"""
        # Login user
        self.client.login(username='filteruser', password='Filter@123')
        
        # Add additional entry with specific date
        past_date = (timezone.now().date() - timedelta(days=30))
        Entry.objects.create(
            user=self.user,
            category=self.category,
            title='Old Income',
            amount=Decimal('500.00'),
            date=past_date,
            type=Entry.INCOME
        )
        
        # Test date range filter
        response = self.client.get(
            f"{self.entries_filter_url}?type=IN&from={past_date.isoformat()}&to={past_date.isoformat()}",
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        # Check response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('entries_html', data)
        self.assertIn('Old Income', data['entries_html'])
        self.assertNotIn('Income Entry', data['entries_html'])

class ReportsFilterTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.reports_filter_url = reverse('budget:reports-filter')
        
        # Create a test user
        self.user = User.objects.create_user(
            username='reportuser',
            email='report@example.com',
            password='Report@123'
        )
        
        # Create a category
        self.category = Category.objects.create(name="Test Category", user=self.user)
        
        # Create some entries
        Entry.objects.create(
            user=self.user,
            category=self.category,
            title='Monthly Income',
            amount=Decimal('1000.00'),
            date=timezone.now().date(),
            type=Entry.INCOME,
            notes='Monthly income'
        )
        Entry.objects.create(
            user=self.user,
            category=self.category,
            title='Food Expense',
            amount=Decimal('200.00'),
            date=timezone.now().date(),
            type=Entry.EXPENSE,
            notes='Food expense'
        )
    
    def test_reports_filter(self):
        """Test the reports filter endpoint"""
        # Login user
        self.client.login(username='reportuser', password='Report@123')
        
        # Make AJAX request
        response = self.client.get(
            self.reports_filter_url,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        # Check response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('report_html', data)
        
        # Test with date filters
        today = timezone.now().date()
        response = self.client.get(
            f"{self.reports_filter_url}?from={today.isoformat()}&to={today.isoformat()}",
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        # Check response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('report_html', data)

    def test_unauthorized_access(self):
        """Test unauthorized access to reports filter"""
        # Try to access without login
        response = self.client.get(
            self.reports_filter_url,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        # Should redirect to login page
        self.assertEqual(response.status_code, 302)
        
        # Login as different user
        other_user = User.objects.create_user(
            username='otherreportuser',
            email='otherreport@example.com',
            password='Other@123'
        )
        self.client.login(username='otherreportuser', password='Other@123')
        
        # Make request - should not see entries from first user
        response = self.client.get(
            self.reports_filter_url,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        # Should have response but with no entries from other user
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('report_html', data)
        self.assertNotIn('Monthly Income', data['report_html'])
        self.assertNotIn('Food Expense', data['report_html'])

    def test_filter_with_category(self):
        """Test reports filter with category filter"""
        # Login user
        self.client.login(username='reportuser', password='Report@123')
        
        # Create another category and entry
        second_category = Category.objects.create(name="Another Category", user=self.user)
        Entry.objects.create(
            user=self.user,
            category=second_category,
            title='Entertainment Expense',
            amount=Decimal('150.00'),
            date=timezone.now().date(),
            type=Entry.EXPENSE
        )
        
        # Test category filter
        response = self.client.get(
            f"{self.reports_filter_url}?category={second_category.id}",
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        # Check response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('report_html', data)
        self.assertIn('Entertainment Expense', data['report_html'])
        self.assertNotIn('Food Expense', data['report_html'])

class VerifyEmailTest(TestCase):
    @patch('budget.views.EmailMultiAlternatives')
    def test_email_verification(self, mock_email):
        """Test the email verification flow"""
        # Mock the email sending
        mock_email.return_value.send.return_value = 1
        
        # Create user and token
        user = User.objects.create_user(
            username='verifyuser',
            email='verify@example.com',
            password='Verify@123',
            is_active=False
        )
        
        token = EmailVerificationToken.objects.create(
            user=user,
            token=uuid.uuid4()
        )
        
        # Access verification URL
        verify_url = reverse('budget:verify_email', args=[token.token])
        response = self.client.get(verify_url, follow=True)
        
        # Check if user is now active
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        
        # Check if token is marked as used
        token.refresh_from_db()
        self.assertTrue(token.used)

    def test_invalid_token_verification(self):
        """Test verification with invalid token"""
        # Access verification URL with invalid token
        non_existent_token = uuid.uuid4()
        verify_url = reverse('budget:verify_email', args=[non_existent_token])
        response = self.client.get(verify_url, follow=True)
        
        # Should redirect to auth page with error
        self.assertRedirects(response, reverse('budget:auth'))

    def test_already_used_token(self):
        """Test verification with already used token"""
        # Create user and token that's already been used
        user = User.objects.create_user(
            username='usedtokenuser',
            email='usedtoken@example.com',
            password='Token@123',
            is_active=True
        )
        
        token = EmailVerificationToken.objects.create(
            user=user,
            token=uuid.uuid4(),
            used=True
        )
        
        # Access verification URL
        verify_url = reverse('budget:verify_email', args=[token.token])
        response = self.client.get(verify_url, follow=True)
        
        # Should redirect to auth page
        self.assertRedirects(response, reverse('budget:auth'))

class PasswordResetTest(TestCase):
    @patch('budget.views.EmailMultiAlternatives')
    def test_password_reset_flow(self, mock_email):
        """Test the full password reset flow"""
        # Mock the email sending
        mock_email.return_value.send.return_value = 1
        
        # Create a test user
        user = User.objects.create_user(
            username='resetuser',
            email='reset@example.com',
            password='OldPass@123'
        )
        
        # 1. Request password reset
        forgot_password_url = reverse('budget:forgot_password')
        response = self.client.post(forgot_password_url, {
            'email': 'reset@example.com'
        }, follow=True)
        
        # Verify token created
        self.assertTrue(PasswordResetToken.objects.filter(user=user).exists())
        token = PasswordResetToken.objects.get(user=user)
        
        # 2. Access reset form
        reset_url = reverse('budget:reset_password', args=[token.token])
        response = self.client.get(reset_url)
        self.assertEqual(response.status_code, 200)
        
        # 3. Submit new password
        response = self.client.post(reset_url, {
            'password1': 'NewPass@123',
            'password2': 'NewPass@123'
        }, follow=True)
        
        # 4. Token should be marked as expired
        token.refresh_from_db()
        self.assertTrue(token.expired)
        
        # 5. Login with new password
        auth_url = reverse('budget:auth')
        response = self.client.post(auth_url, {
            'login-submit': 'login',
            'email': 'reset@example.com',
            'password': 'NewPass@123'
        }, follow=True)
        
        # Should be logged in and redirected to dashboard
        self.assertRedirects(response, reverse('budget:dashboard'))

    def test_reset_with_invalid_token(self):
        """Test password reset with invalid token"""
        # Access reset URL with non-existent token
        non_existent_token = 'invalid-token-123456'
        reset_url = reverse('budget:reset_password', args=[non_existent_token])
        response = self.client.get(reset_url, follow=True)
        
        # Should redirect to forgot password page
        self.assertRedirects(response, reverse('budget:forgot_password'))

    def test_reset_with_expired_token(self):
        """Test password reset with expired token"""
        # Create user and expired token
        user = User.objects.create_user(
            username='expiredtokenuser',
            email='expiredtoken@example.com',
            password='Old@123'
        )
        
        token = PasswordResetToken.objects.create(
            user=user,
            token='expired-token-123',
            expired=True
        )
        
        # Access reset URL
        reset_url = reverse('budget:reset_password', args=[token.token])
        response = self.client.get(reset_url, follow=True)
        
        # Should redirect to forgot password page
        self.assertRedirects(response, reverse('budget:forgot_password'))

    def test_password_mismatch(self):
        """Test password reset with mismatched passwords"""
        # Create user and token
        user = User.objects.create_user(
            username='mismatchuser',
            email='mismatch@example.com',
            password='Old@123'
        )
        
        token = PasswordResetToken.objects.create(
            user=user,
            token='mismatch-token-123'
        )
        
        # Access reset URL
        reset_url = reverse('budget:reset_password', args=[token.token])
        response = self.client.get(reset_url)
        self.assertEqual(response.status_code, 200)
        
        # Submit mismatched passwords
        response = self.client.post(reset_url, {
            'password1': 'NewPass@123',
            'password2': 'DifferentPass@123'  # Different password
        })
        
        # Should stay on same page with error
        self.assertEqual(response.status_code, 200)
        # Token should not be expired
        token.refresh_from_db()
        self.assertFalse(token.expired)

class AIQueryTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.ai_query_url = reverse('budget:ai-query')
        
        # Create a test user
        self.user = User.objects.create_user(
            username='aiuser',
            email='ai@example.com',
            password='AI@123'
        )
    
    @patch('budget.views.gemini_client.generate_content')
    def test_ai_query(self, mock_generate_content):
        """Test the AI query endpoint"""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.text = "This is a mock AI response."
        mock_generate_content.return_value = mock_response
        
        # Login user
        self.client.login(username='aiuser', password='AI@123')
        
        # Make AI query
        response = self.client.post(
            self.ai_query_url,
            json.dumps({'question': 'How can I save money?'}),
            content_type='application/json'
        )
        
        # Check response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['response'], "This is a mock AI response.")
        
        # Test invalid request format
        response = self.client.post(
            self.ai_query_url,
            "invalid json",
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)

    def test_unauthorized_access(self):
        """Test unauthorized access to AI endpoint"""
        # Try without login
        response = self.client.post(
            self.ai_query_url,
            json.dumps({'question': 'How can I save money?'}),
            content_type='application/json'
        )
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)

    @patch('budget.views.gemini_client.generate_content')
    def test_ai_error_handling(self, mock_generate_content):
        """Test AI error handling"""
        # Setup mock to raise exception
        mock_generate_content.side_effect = Exception("API error")
        
        # Login user
        self.client.login(username='aiuser', password='AI@123')
        
        # Make AI query
        response = self.client.post(
            self.ai_query_url,
            json.dumps({'question': 'How can I save money?'}),
            content_type='application/json'
        )
        
        # Should return error response
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.content)
        self.assertIn('error', data)

    @patch('budget.views.gemini_client.generate_content')
    def test_empty_question(self, mock_generate_content):
        """Test AI query with empty question"""
        # Login user
        self.client.login(username='aiuser', password='AI@123')
        
        # Make AI query with empty question
        response = self.client.post(
            self.ai_query_url,
            json.dumps({'question': ''}),
            content_type='application/json'
        )
        
        # Should return error
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data) 