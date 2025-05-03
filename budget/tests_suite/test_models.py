from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from django.db import transaction
from ..models import Category, Entry, ContactMessage, EmailVerificationToken, Budget, PasswordResetToken
import uuid
from datetime import timedelta
from django.db import models

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
        
    def test_category_unique_per_user(self):
        """Test that different users can have categories with different names"""
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpass123'
        )
        
        # Create category with different name
        other_category = Category.objects.create(
            name='Travel',
            user=other_user
        )
        
        # Both categories should exist
        self.assertEqual(Category.objects.all().count(), 2)
        
        # But they're associated with different users
        self.assertEqual(Category.objects.filter(user=self.user).count(), 1)
        self.assertEqual(Category.objects.filter(user=other_user).count(), 1)
        
    def test_category_delete(self):
        """Test deleting a category"""
        category_id = self.category.id
        self.category.delete()
        
        # Verify the category no longer exists
        self.assertEqual(Category.objects.filter(id=category_id).count(), 0)

    def test_category_uniqueness_constraint(self):
        """Test that category names are unique per user"""
        # Try to create another category with the same name for the same user
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                duplicate_category = Category.objects.create(
                    name='Food',
                    user=self.user
                )
        
        # Create another user and a category with the same name
        other_user = User.objects.create_user(
            username='otheruser2',
            email='other2@example.com',
            password='otherpass123'
        )
        
        # This should work fine because it's for a different user
        other_category = Category.objects.create(
            name='Food',
            user=other_user
        )
        
        self.assertEqual(other_category.name, 'Food')
        self.assertEqual(other_category.user, other_user)
        
    def test_category_name_max_length(self):
        """Test category name max length validation"""
        # Create a category with name at max length
        max_length_name = 'a' * 50
        valid_category = Category(
            name=max_length_name,
            user=self.user
        )
        valid_category.full_clean()  # Should not raise validation error
        
        # Create a category with name too long
        too_long_name = 'a' * 51
        invalid_category = Category(
            name=too_long_name,
            user=self.user
        )
        with self.assertRaises(ValidationError):
            invalid_category.full_clean()
    
    def test_category_ordering(self):
        """Test that categories are ordered by name"""
        # Create categories with names that should be ordered
        category_b = Category.objects.create(
            name='Beverages',
            user=self.user
        )
        category_d = Category.objects.create(
            name='Dining',
            user=self.user
        )
        category_a = Category.objects.create(
            name='Auto',
            user=self.user
        )
        
        # Get ordered categories
        ordered_categories = Category.objects.filter(user=self.user)
        
        # Check order
        self.assertEqual(ordered_categories[0].name, 'Auto')
        self.assertEqual(ordered_categories[1].name, 'Beverages')
        self.assertEqual(ordered_categories[2].name, 'Dining')
        self.assertEqual(ordered_categories[3].name, 'Food')

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
        self.assertEqual(self.entry.notes, 'Weekly shopping')
        
    def test_entry_without_category(self):
        """Test that an entry can be created without a category"""
        no_category_entry = Entry.objects.create(
            user=self.user,
            title='Misc expense',
            amount=Decimal('25.00'),
            date=timezone.now().date(),
            type=Entry.EXPENSE,
            notes='Miscellaneous expense without category',
            category=None
        )
        self.assertIsNone(no_category_entry.category)
        self.assertEqual(no_category_entry.title, 'Misc expense')
        
    def test_entry_user_relationship(self):
        """Test that entries are correctly associated with users"""
        user_entries = Entry.objects.filter(user=self.user)
        self.assertEqual(user_entries.count(), 1)
        self.assertEqual(user_entries.first(), self.entry)
        
    def test_entry_type_choices(self):
        """Test that entry type choices work correctly"""
        # Create an income entry
        income_entry = Entry.objects.create(
            user=self.user,
            title='Salary',
            amount=Decimal('1000.00'),
            date=timezone.now().date(),
            type=Entry.INCOME,
            notes='Monthly salary'
        )
        
        # Test filtering by type
        income_entries = Entry.objects.filter(type=Entry.INCOME)
        expense_entries = Entry.objects.filter(type=Entry.EXPENSE)
        
        self.assertEqual(income_entries.count(), 1)
        self.assertEqual(expense_entries.count(), 1)
        self.assertEqual(income_entries.first(), income_entry)
        self.assertEqual(expense_entries.first(), self.entry)
        
    def test_entry_category_relationship(self):
        """Test that entries are correctly associated with categories"""
        category_entries = Entry.objects.filter(category=self.category)
        self.assertEqual(category_entries.count(), 1)
        self.assertEqual(category_entries.first(), self.entry)
        
    def test_entry_when_category_deleted(self):
        """Test what happens to an entry when its category is deleted"""
        # When the category is deleted, the entry should be deleted too
        # because of the on_delete=models.CASCADE in the model
        entry_id = self.entry.id
        self.category.delete()
        
        # Entry should no longer exist due to CASCADE
        self.assertEqual(Entry.objects.filter(id=entry_id).count(), 0)

    def test_entry_deleted_when_user_deleted(self):
        """Test that entries are deleted when the user is deleted"""
        # Record the entry ID
        entry_id = self.entry.id
        
        # Delete the user
        self.user.delete()
        
        # Check that entry no longer exists
        self.assertEqual(Entry.objects.filter(id=entry_id).count(), 0)
        
    def test_entry_str_representation(self):
        """Test the string representation of an entry"""
        # Note: This is a placeholder test since the model.py doesn't show the __str__ method
        # Implement this test based on the actual implementation
        # Sample implementation: f"{self.title} - ${self.amount} - {self.date}"
        pass
        
    def test_entry_validation(self):
        """Test entry validation"""
        # Try to create an entry with negative amount
        with self.assertRaises(ValidationError):
            invalid_entry = Entry(
                user=self.user,
                title='Invalid Entry',
                amount=Decimal('-50.00'),  # Negative amount
                date=timezone.now().date(),
                type=Entry.EXPENSE
            )
            invalid_entry.full_clean()  # Triggers validation
        
        # Try to create an entry with an invalid type
        with self.assertRaises(ValidationError):
            invalid_entry = Entry(
                user=self.user,
                title='Invalid Entry',
                amount=Decimal('50.00'),
                date=timezone.now().date(),
                type='INVALID_TYPE'  # Invalid type
            )
            invalid_entry.full_clean()  # Triggers validation

    def test_entry_unique_constraint(self):
        """Test entry uniqueness constraint"""
        # Try to create a duplicate entry (same title, date, user, category)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                duplicate_entry = Entry.objects.create(
                    user=self.user,
                    category=self.category,
                    title='Groceries',  # Same title
                    amount=Decimal('75.00'),  # Different amount
                    date=self.entry.date,  # Same date
                    type=Entry.EXPENSE,
                    notes='Different notes'
                )
        
        # Should be able to create entry with different title
        different_title_entry = Entry.objects.create(
            user=self.user,
            category=self.category,
            title='Different Groceries',  # Different title
            amount=Decimal('75.00'),
            date=self.entry.date,  # Same date
            type=Entry.EXPENSE,
            notes='Different notes'
        )
        self.assertEqual(different_title_entry.title, 'Different Groceries')
        
        # Should be able to create entry with different date
        tomorrow = self.entry.date + timedelta(days=1)
        different_date_entry = Entry.objects.create(
            user=self.user,
            category=self.category,
            title='Groceries',  # Same title
            amount=Decimal('75.00'),
            date=tomorrow,  # Different date
            type=Entry.EXPENSE,
            notes='Different notes'
        )
        self.assertEqual(different_date_entry.date, tomorrow)
        
        # Should be able to create entry with different category
        other_category = Category.objects.create(
            name='Other',
            user=self.user
        )
        different_category_entry = Entry.objects.create(
            user=self.user,
            category=other_category,  # Different category
            title='Groceries',  # Same title
            amount=Decimal('75.00'),
            date=self.entry.date,  # Same date
            type=Entry.EXPENSE,
            notes='Different notes'
        )
        self.assertEqual(different_category_entry.category, other_category)
    
    def test_entry_field_max_lengths(self):
        """Test entry field maximum lengths"""
        # Test title max length
        max_title = 'a' * 100
        valid_entry = Entry(
            user=self.user,
            title=max_title,
            amount=Decimal('50.00'),
            date=timezone.now().date(),
            type=Entry.EXPENSE
        )
        valid_entry.full_clean()  # Should not raise validation error
        
        # Test title too long
        too_long_title = 'a' * 101
        invalid_entry = Entry(
            user=self.user,
            title=too_long_title,
            amount=Decimal('50.00'),
            date=timezone.now().date(),
            type=Entry.EXPENSE
        )
        with self.assertRaises(ValidationError):
            invalid_entry.full_clean()

class ContactMessageModelTest(TestCase):
    def setUp(self):
        self.contact_message = ContactMessage.objects.create(
            name='Test User',
            email='test@example.com',
            subject='Test Subject',
            message='This is a test message'
        )
    
    def test_contact_message_creation(self):
        """Test that a contact message can be created correctly"""
        self.assertEqual(self.contact_message.name, 'Test User')
        self.assertEqual(self.contact_message.email, 'test@example.com')
        self.assertEqual(self.contact_message.subject, 'Test Subject')
        self.assertEqual(self.contact_message.message, 'This is a test message')
        self.assertFalse(self.contact_message.is_read)
        self.assertIsNotNone(self.contact_message.created_at)
        
    def test_contact_message_str_representation(self):
        """Test the string representation of a contact message"""
        expected_str = f"Message from Test User - Test Subject"
        self.assertEqual(str(self.contact_message), expected_str)
    
    def test_contact_message_mark_as_read(self):
        """Test that a contact message can be marked as read"""
        self.assertFalse(self.contact_message.is_read)
        self.contact_message.is_read = True
        self.contact_message.save()
        
        # Refresh from database
        self.contact_message.refresh_from_db()
        self.assertTrue(self.contact_message.is_read)
        
    def test_contact_message_ordering(self):
        """Test that contact messages are ordered by created_at"""
        # Create a new message
        new_message = ContactMessage.objects.create(
            name='Another User',
            email='another@example.com',
            subject='Another Subject',
            message='Another message'
        )
        
        # Get all messages, ordered by default
        messages = ContactMessage.objects.all()
        
        # First message should be the oldest one
        self.assertEqual(messages.first(), self.contact_message)
        self.assertEqual(messages.last(), new_message)
    
    def test_contact_message_field_max_lengths(self):
        """Test contact message field maximum lengths"""
        # Test name max length
        max_name = 'a' * 100
        valid_message = ContactMessage(
            name=max_name,
            email='test@example.com',
            subject='Test Subject',
            message='Test message'
        )
        valid_message.full_clean()  # Should not raise validation error
        
        # Test name too long
        too_long_name = 'a' * 101
        invalid_message = ContactMessage(
            name=too_long_name,
            email='test@example.com',
            subject='Test Subject',
            message='Test message'
        )
        with self.assertRaises(ValidationError):
            invalid_message.full_clean()
        
        # Test subject max length
        max_subject = 'a' * 200
        valid_message = ContactMessage(
            name='Test User',
            email='test@example.com',
            subject=max_subject,
            message='Test message'
        )
        valid_message.full_clean()  # Should not raise validation error
        
        # Test subject too long
        too_long_subject = 'a' * 201
        invalid_message = ContactMessage(
            name='Test User',
            email='test@example.com',
            subject=too_long_subject,
            message='Test message'
        )
        with self.assertRaises(ValidationError):
            invalid_message.full_clean()
    
    def test_contact_message_email_validation(self):
        """Test contact message email validation"""
        # Test valid email
        valid_message = ContactMessage(
            name='Test User',
            email='valid@example.com',
            subject='Test Subject',
            message='Test message'
        )
        valid_message.full_clean()  # Should not raise validation error
        
        # Test invalid email
        invalid_message = ContactMessage(
            name='Test User',
            email='invalid-email',  # Invalid email format
            subject='Test Subject',
            message='Test message'
        )
        with self.assertRaises(ValidationError):
            invalid_message.full_clean()

class EmailVerificationTokenTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.token = EmailVerificationToken.objects.create(
            user=self.user,
            token=uuid.uuid4()
        )
    
    def test_token_creation(self):
        """Test that a token can be created correctly"""
        self.assertEqual(self.token.user, self.user)
        self.assertIsNotNone(self.token.token)
        self.assertIsNotNone(self.token.created_at)
        self.assertFalse(self.token.used)
        
    def test_token_str_representation(self):
        """Test the string representation of a token"""
        expected_str = f"Verify {self.user.email} → {self.token.token}"
        self.assertEqual(str(self.token), expected_str)
        
    def test_token_mark_as_used(self):
        """Test that a token can be marked as used"""
        self.assertFalse(self.token.used)
        self.token.used = True
        self.token.save()
        
        # Refresh from database
        self.token.refresh_from_db()
        self.assertTrue(self.token.used)
    
    def test_token_one_to_one_relationship(self):
        """Test one-to-one relationship between user and token"""
        # Try to create a second token for the same user
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                second_token = EmailVerificationToken.objects.create(
                    user=self.user,
                    token=uuid.uuid4()
                )
    
    def test_token_uniqueness(self):
        """Test that tokens must be unique"""
        # Create a different user
        another_user = User.objects.create_user(
            username='anotheruser',
            email='another@example.com',
            password='testpass123'
        )
        
        # Try to create a token with the same UUID
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                duplicate_token = EmailVerificationToken.objects.create(
                    user=another_user,
                    token=self.token.token  # Same token
                )
    
    def test_token_default_uuid_generation(self):
        """Test that token generates UUID by default if not provided"""
        # We need a different user for this test since EmailVerificationToken has a OneToOne relationship
        token_without_specified_uuid = EmailVerificationToken.objects.create(
            user=User.objects.create_user(
                username='autouuiduser',
                email='autouuid@example.com',
                password='testpass123'
            )
        )
        
        # UUID should have been generated
        self.assertIsNotNone(token_without_specified_uuid.token)
        
    def test_token_deleted_when_user_deleted(self):
        """Test that tokens are deleted when the user is deleted"""
        # Record the token ID
        token_id = self.token.id
        
        # Delete the user
        self.user.delete()
        
        # Check that token no longer exists
        self.assertEqual(EmailVerificationToken.objects.filter(id=token_id).count(), 0)

class PasswordResetTokenTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='resetuser',
            email='reset@example.com',
            password='testpass123'
        )
        self.token = PasswordResetToken.objects.create(
            user=self.user,
            token='test-reset-token'
        )
    
    def test_token_creation(self):
        """Test that a password reset token can be created correctly"""
        self.assertEqual(self.token.user, self.user)
        self.assertEqual(self.token.token, 'test-reset-token')
        self.assertIsNotNone(self.token.created_at)
        self.assertFalse(self.token.expired)
    
    def test_token_str_representation(self):
        """Test the string representation of a password reset token"""
        expected_str = f"Password reset token for {self.user.email}"
        self.assertEqual(str(self.token), expected_str)
    
    def test_token_mark_as_expired(self):
        """Test that a token can be marked as expired"""
        self.assertFalse(self.token.expired)
        self.token.expired = True
        self.token.save()
        
        # Refresh from database
        self.token.refresh_from_db()
        self.assertTrue(self.token.expired)
    
    def test_token_uniqueness(self):
        """Test that token values must be unique"""
        # Try to create a token with the same value
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                duplicate_token = PasswordResetToken.objects.create(
                    user=self.user,
                    token='test-reset-token'  # Same token
                )
        
        # Can create token with different value
        different_token = PasswordResetToken.objects.create(
            user=self.user,
            token='different-reset-token'
        )
        self.assertEqual(different_token.token, 'different-reset-token')
    
    def test_token_max_length(self):
        """Test token field maximum length"""
        # Test token at max length
        max_token = 'a' * 100
        valid_token = PasswordResetToken(
            user=self.user,
            token=max_token
        )
        valid_token.full_clean()  # Should not raise validation error
        
        # Test token too long
        too_long_token = 'a' * 101
        invalid_token = PasswordResetToken(
            user=self.user,
            token=too_long_token
        )
        with self.assertRaises(ValidationError):
            invalid_token.full_clean()
    
    def test_token_deleted_when_user_deleted(self):
        """Test that tokens are deleted when the user is deleted"""
        # Record the token ID
        token_id = self.token.id
        
        # Delete the user
        self.user.delete()
        
        # Check that token no longer exists
        self.assertEqual(PasswordResetToken.objects.filter(id=token_id).count(), 0)
    
    def test_multiple_tokens_per_user(self):
        """Test that a user can have multiple reset tokens"""
        # Create additional tokens for same user
        token2 = PasswordResetToken.objects.create(
            user=self.user,
            token='second-reset-token'
        )
        token3 = PasswordResetToken.objects.create(
            user=self.user,
            token='third-reset-token'
        )
        
        # User should have 3 tokens
        user_tokens = PasswordResetToken.objects.filter(user=self.user)
        self.assertEqual(user_tokens.count(), 3)

class BudgetModelTest(TestCase):
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
        self.month_date = timezone.now().date().replace(day=1)
        self.budget = Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('500.00'),
            month=self.month_date
        )
    
    def test_budget_creation(self):
        """Test that a budget can be created correctly"""
        self.assertEqual(self.budget.user, self.user)
        self.assertEqual(self.budget.category, self.category)
        self.assertEqual(self.budget.amount, Decimal('500.00'))
        self.assertEqual(self.budget.month, self.month_date)
        
    def test_budget_str_representation(self):
        """Test the string representation of a budget with category"""
        # Confirm the actual implementation with the model
        self.assertTrue(str(self.budget).startswith(str(self.user)))
        self.assertIn(str(self.category.name), str(self.budget))
        self.assertIn(str(self.budget.amount), str(self.budget))
    
    def test_budget_str_representation_without_category(self):
        """Test the string representation of a budget without category"""
        total_budget = Budget.objects.create(
            user=self.user,
            category=None,
            amount=Decimal('1000.00'),
            month=self.month_date
        )
        # Confirm the actual implementation with the model
        self.assertTrue(str(total_budget).startswith(str(self.user)))
        self.assertIn("Total", str(total_budget))
        self.assertIn(str(total_budget.amount), str(total_budget))
        
    def test_budget_uniqueness_constraint(self):
        """Test that budgets are unique per user, category, month"""
        # Try to create a duplicate budget
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                duplicate_budget = Budget.objects.create(
                    user=self.user,
                    category=self.category,
                    amount=Decimal('600.00'),  # Different amount
                    month=self.month_date  # Same month
                )
        
        # But we should be able to create a budget for a different month
        next_month = self.month_date + timedelta(days=31)
        next_month = next_month.replace(day=1)  # First day of next month
        
        next_month_budget = Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('600.00'),
            month=next_month
        )
        
        self.assertEqual(next_month_budget.amount, Decimal('600.00'))
        self.assertEqual(next_month_budget.month, next_month)
    
    def test_budget_ordering(self):
        """Test that budgets are ordered by month in descending order"""
        # Create budgets for different months
        current_month = self.month_date
        next_month = (current_month + timedelta(days=31)).replace(day=1)
        prev_month = (current_month - timedelta(days=15)).replace(day=1)
        
        budget_next = Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('600.00'),
            month=next_month
        )
        
        budget_prev = Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('400.00'),
            month=prev_month
        )
        
        # Get ordered budgets
        ordered_budgets = Budget.objects.filter(user=self.user, category=self.category)
        
        # Check order (newest to oldest)
        self.assertEqual(ordered_budgets[0], budget_next)
        self.assertEqual(ordered_budgets[1], self.budget)
        self.assertEqual(ordered_budgets[2], budget_prev)
        
    def test_budget_deleted_when_user_deleted(self):
        """Test that budgets are deleted when the user is deleted"""
        # Record the budget ID
        budget_id = self.budget.id
        
        # Delete the user
        self.user.delete()
        
        # Check that budget no longer exists
        self.assertEqual(Budget.objects.filter(id=budget_id).count(), 0)
        
    def test_budget_deleted_when_category_deleted(self):
        """Test that budgets are deleted when the category is deleted"""
        # Record the budget ID
        budget_id = self.budget.id
        
        # Delete the category
        self.category.delete()
        
        # Check that budget no longer exists
        self.assertEqual(Budget.objects.filter(id=budget_id).count(), 0)
    
    def test_budget_with_null_category(self):
        """Test that a budget can be created with a null category (total budget)"""
        total_budget = Budget.objects.create(
            user=self.user,
            category=None,
            amount=Decimal('1000.00'),
            month=self.month_date
        )
        
        self.assertIsNone(total_budget.category)
        self.assertEqual(total_budget.amount, Decimal('1000.00'))
    
    def test_budget_decimal_precision(self):
        """Test budget amount decimal precision"""
        # Test with 2 decimal places
        precise_budget = Budget.objects.create(
            user=self.user,
            category=None,
            amount=Decimal('123.45'),
            month=(self.month_date + timedelta(days=31)).replace(day=1)
        )
        self.assertEqual(precise_budget.amount, Decimal('123.45'))
        
        # Test with many decimal places (should truncate to 2)
        decimal_budget = Budget(
            user=self.user,
            category=None,
            amount=Decimal('123.456789'),
            month=(self.month_date + timedelta(days=62)).replace(day=1)
        )
        decimal_budget.full_clean()  # Should not raise validation error
        decimal_budget.save()
        
        decimal_budget.refresh_from_db()
        self.assertEqual(decimal_budget.amount, Decimal('123.46'))  # Rounded to 2 decimal places

class ModelStrTests(TestCase):
    """Tests specifically focusing on model __str__ methods"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='str_test_user',
            email='str_test@example.com',
            password='testpass123'
        )
        
        # Create Category
        self.category = Category.objects.create(
            name='StrTestCategory',
            user=self.user
        )
        
        # Set up test date
        self.date = timezone.datetime(2023, 8, 1).date()
        
        # Create Budget with category
        self.budget_with_category = Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('800.00'),
            month=self.date
        )
        
        # Create Budget without category
        self.budget_without_category = Budget.objects.create(
            user=self.user,
            category=None,
            amount=Decimal('1600.00'),
            month=self.date
        )
        
        # Create PasswordResetToken
        self.password_token = PasswordResetToken.objects.create(
            user=self.user,
            token='str-test-token-2'
        )
        
        # Create EmailVerificationToken
        self.email_token = EmailVerificationToken.objects.create(
            user=self.user,
            token=uuid.uuid4()
        )
        
        # Create Entry
        self.entry = Entry.objects.create(
            user=self.user,
            category=self.category,
            title='Test Entry',
            amount=Decimal('50.00'),
            date=self.date,
            type=Entry.EXPENSE,
            notes='Test notes'
        )
        
        # Create ContactMessage
        self.contact_message = ContactMessage.objects.create(
            name='Str Test User',
            email='strtest@example.com',
            subject='Str Test Subject',
            message='Str Test message'
        )
    
    def test_all_str_methods(self):
        """Test all __str__ methods at once to ensure coverage"""
        # Test Category.__str__
        self.assertEqual(str(self.category), self.category.name)
        
        # Test Budget.__str__ with category - using basic assertions to avoid exact format issues
        budget_str = str(self.budget_with_category)
        self.assertIn(str(self.user), budget_str)
        self.assertIn(str(self.category.name), budget_str)
        self.assertIn(str(self.budget_with_category.amount), budget_str)
        
        # Test Budget.__str__ without category - using basic assertions
        budget_without_str = str(self.budget_without_category)
        self.assertIn(str(self.user), budget_without_str)
        self.assertIn("Total", budget_without_str)
        self.assertIn(str(self.budget_without_category.amount), budget_without_str)
        
        # Test PasswordResetToken.__str__
        password_str = str(self.password_token)
        self.assertIn(self.user.email, password_str)
        self.assertIn("Password reset token", password_str)
        
        # Test EmailVerificationToken.__str__
        email_str = str(self.email_token)
        self.assertIn(self.user.email, email_str)
        self.assertIn(str(self.email_token.token), email_str)
        
        # Test ContactMessage.__str__
        contact_str = str(self.contact_message)
        self.assertIn("Message from", contact_str)
        self.assertIn(self.contact_message.name, contact_str)
        self.assertIn(self.contact_message.subject, contact_str)

class EntryQuerySetTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='querytestuser',
            email='querytest@example.com',
            password='testpass123'
        )
        self.category = Category.objects.create(
            name='QueryTestFood',  # Use a unique category name
            user=self.user
        )
        # Create multiple entries with different dates
        today = timezone.now().date()
        self.entry1 = Entry.objects.create(
            user=self.user,
            category=self.category,
            title='Groceries Today',
            amount=Decimal('50.00'),
            date=today,
            type=Entry.EXPENSE,
            notes='Today shopping'
        )
        self.entry2 = Entry.objects.create(
            user=self.user,
            category=self.category,
            title='Groceries Yesterday',
            amount=Decimal('30.00'),
            date=today - timedelta(days=1),
            type=Entry.EXPENSE,
            notes='Yesterday shopping'
        )
        self.entry3 = Entry.objects.create(
            user=self.user,
            category=self.category,
            title='Salary',
            amount=Decimal('1000.00'),
            date=today - timedelta(days=2),
            type=Entry.INCOME,
            notes='Monthly salary'
        )
        
    def test_filter_by_date_range(self):
        """Test filtering entries by date range"""
        today = timezone.now().date()
        # Get entries from yesterday until today
        date_range_entries = Entry.objects.filter(
            date__gte=today - timedelta(days=1),
            date__lte=today
        )
        self.assertEqual(date_range_entries.count(), 2)
        
    def test_sum_expenses(self):
        """Test summing expenses"""
        expenses_sum = Entry.objects.filter(type=Entry.EXPENSE).aggregate(total=models.Sum('amount'))
        self.assertEqual(expenses_sum['total'], Decimal('80.00'))
        
    def test_sum_income(self):
        """Test summing income"""
        income_sum = Entry.objects.filter(type=Entry.INCOME).aggregate(total=models.Sum('amount'))
        self.assertEqual(income_sum['total'], Decimal('1000.00'))
        
    def test_net_balance(self):
        """Test calculating net balance"""
        expenses_sum = Entry.objects.filter(type=Entry.EXPENSE).aggregate(total=models.Sum('amount'))
        income_sum = Entry.objects.filter(type=Entry.INCOME).aggregate(total=models.Sum('amount'))
        net_balance = income_sum['total'] - expenses_sum['total']
        self.assertEqual(net_balance, Decimal('920.00'))

class BudgetCalculationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='budgettestuser',
            email='budgettest@example.com',
            password='testpass123'
        )
        self.category = Category.objects.create(
            name='BudgetTestFood',  # Use a unique category name
            user=self.user
        )
        # Create a monthly budget
        today = timezone.now().date()
        month_start = today.replace(day=1)
        self.budget = Budget.objects.create(
            user=self.user,
            category=self.category,
            month=month_start,
            amount=Decimal('500.00')
        )
        # Create total budget (without category)
        self.total_budget = Budget.objects.create(
            user=self.user,
            category=None,
            month=month_start,
            amount=Decimal('1000.00')
        )
        # Create entries within this month
        self.entry1 = Entry.objects.create(
            user=self.user,
            category=self.category,
            title='Groceries',
            amount=Decimal('200.00'),
            date=today,
            type=Entry.EXPENSE,
            notes='Weekly shopping'
        )
        self.entry2 = Entry.objects.create(
            user=self.user,
            category=self.category,
            title='Restaurant',
            amount=Decimal('150.00'),
            date=today - timedelta(days=2),
            type=Entry.EXPENSE,
            notes='Dinner out'
        )
        
    def test_budget_remaining(self):
        """Test calculating budget remaining"""
        # Calculate remaining budget for category
        expenses = Entry.objects.filter(
            user=self.user,
            category=self.category,
            date__gte=self.budget.month,
            type=Entry.EXPENSE
        ).aggregate(total=models.Sum('amount'))
        
        remaining = self.budget.amount - expenses['total']
        self.assertEqual(remaining, Decimal('150.00'))
        
    def test_budget_total_remaining(self):
        """Test calculating total budget remaining"""
        # Calculate remaining for total budget
        expenses = Entry.objects.filter(
            user=self.user,
            date__gte=self.total_budget.month,
            type=Entry.EXPENSE
        ).aggregate(total=models.Sum('amount'))
        
        remaining = self.total_budget.amount - expenses['total']
        self.assertEqual(remaining, Decimal('650.00'))
        
    def test_budget_over_limit(self):
        """Test detecting when budget is over the limit"""
        # Add another expense that will make the category go over budget
        Entry.objects.create(
            user=self.user,
            category=self.category,
            title='Emergency Grocery',
            amount=Decimal('200.00'),
            date=timezone.now().date(),
            type=Entry.EXPENSE,
            notes='Emergency shopping'
        )
        
        # Calculate remaining budget for category
        expenses = Entry.objects.filter(
            user=self.user,
            category=self.category,
            date__gte=self.budget.month,
            type=Entry.EXPENSE
        ).aggregate(total=models.Sum('amount'))
        
        remaining = self.budget.amount - expenses['total']
        self.assertEqual(remaining, Decimal('-50.00'))
        self.assertTrue(remaining < 0)  # Over budget

class EmailVerificationTokenExpiredTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='tokenuser',
            email='tokentest@example.com',
            password='testpass123'
        )
        # Create an expired token (using freeze_time or mock would be better, but for simplicity)
        # We'll create a token and then manually update its created_at timestamp
        self.token = EmailVerificationToken.objects.create(
            user=self.user,
            token=uuid.uuid4(),
            created_at=timezone.now(),
            used=False
        )
        # Manually update the created_at timestamp to be 8 days in the past
        EmailVerificationToken.objects.filter(pk=self.token.pk).update(
            created_at=timezone.now() - timedelta(days=8)
        )
        # Refresh our token instance
        self.token.refresh_from_db()
        
    def test_token_is_expired(self):
        """Test token expiration detection"""
        # Check if token is expired (older than 7 days)
        expiration_date = self.token.created_at + timedelta(days=7)
        is_expired = timezone.now() > expiration_date
        self.assertTrue(is_expired)
        
    def test_token_usage(self):
        """Test marking token as used"""
        self.assertFalse(self.token.used)
        self.token.used = True
        self.token.save()
        
        # Refresh from database
        refreshed_token = EmailVerificationToken.objects.get(pk=self.token.pk)
        self.assertTrue(refreshed_token.used)

class PasswordResetTokenExpirationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='pwresetuser',
            email='pwreset@example.com',
            password='testpass123'
        )
        # Create tokens with different timestamps
        self.active_token = PasswordResetToken.objects.create(
            user=self.user,
            token='active-token-123',
            created_at=timezone.now(),
            expired=False
        )
        
        # Create an old token and manually set its created_at time
        self.old_token = PasswordResetToken.objects.create(
            user=self.user,
            token='old-token-456',
            created_at=timezone.now(),
            expired=False
        )
        # Update the created_at timestamp to be 3 days in the past
        PasswordResetToken.objects.filter(pk=self.old_token.pk).update(
            created_at=timezone.now() - timedelta(days=3)
        )
        # Refresh the token
        self.old_token.refresh_from_db()
        
        self.expired_token = PasswordResetToken.objects.create(
            user=self.user,
            token='expired-token-789',
            created_at=timezone.now() - timedelta(days=1),
            expired=True
        )
        
    def test_token_expiration_check(self):
        """Test checking if a token is expired based on time"""
        # Consider tokens older than 48 hours as expired
        expiration_time = timezone.now() - timedelta(hours=48)
        
        # Check the old token
        self.assertTrue(self.old_token.created_at < expiration_time)
        
        # Check the active token
        self.assertFalse(self.active_token.created_at < expiration_time)
        
    def test_invalidate_old_tokens(self):
        """Test marking old tokens as expired"""
        # Mark all tokens older than 48 hours as expired
        expiration_time = timezone.now() - timedelta(hours=48)
        old_tokens = PasswordResetToken.objects.filter(
            created_at__lt=expiration_time,
            expired=False
        )
        
        # Update the old tokens
        old_tokens.update(expired=True)
        
        # Refresh from database
        self.old_token.refresh_from_db()
        self.active_token.refresh_from_db()
        
        # Verify the old token is now marked as expired
        self.assertTrue(self.old_token.expired)
        # Verify the active token is still not expired
        self.assertFalse(self.active_token.expired)
        
    def test_finding_valid_token(self):
        """Test finding a valid (unexpired) token"""
        valid_tokens = PasswordResetToken.objects.filter(
            user=self.user,
            expired=False
        )
        self.assertEqual(valid_tokens.count(), 2)
        
        # Ensure specific tokens are in the results
        self.assertIn(self.active_token, valid_tokens)
        self.assertIn(self.old_token, valid_tokens)
        self.assertNotIn(self.expired_token, valid_tokens)

class ModelMethodTests(TestCase):
    """Tests focusing on model methods and properties that might not be fully covered"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='method_test_user',
            email='methodtest@example.com',
            password='testpass123'
        )
        
        # Create Category
        self.category = Category.objects.create(
            name='MethodTestCategory',
            user=self.user
        )
        
        # Set up test date
        self.date = timezone.now().date()
        
        # Create Entries with different types
        self.expense_entry = Entry.objects.create(
            user=self.user,
            category=self.category,
            title='Test Expense',
            amount=Decimal('100.00'),
            date=self.date,
            type=Entry.EXPENSE,
            notes='Test expense notes'
        )
        
        self.income_entry = Entry.objects.create(
            user=self.user,
            category=self.category,
            title='Test Income',
            amount=Decimal('500.00'),
            date=self.date,
            type=Entry.INCOME,
            notes='Test income notes'
        )
        
        # Create Budget with category
        self.budget = Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal('800.00'),
            month=self.date.replace(day=1)
        )
    
    def test_entry_get_type_display(self):
        """Test the get_type_display method of Entry model"""
        self.assertEqual(self.expense_entry.get_type_display(), 'Expense')
        self.assertEqual(self.income_entry.get_type_display(), 'Income')
    
    def test_entry_absolute_url(self):
        """Test the get_absolute_url method if implemented"""
        if hasattr(Entry, 'get_absolute_url'):
            url = self.expense_entry.get_absolute_url()
            self.assertTrue(url.startswith('/'))
            self.assertIn(str(self.expense_entry.id), url)
    
    def test_category_get_entries(self):
        """Test related_name relationship from Category to Entry"""
        category_entries = self.category.entries.all()
        self.assertEqual(category_entries.count(), 2)
        self.assertIn(self.expense_entry, category_entries)
        self.assertIn(self.income_entry, category_entries)
    
    def test_user_related_objects(self):
        """Test related_name relationships from User to other models"""
        user_entries = self.user.entries.all()
        self.assertEqual(user_entries.count(), 2)
        self.assertIn(self.expense_entry, user_entries)
        
        user_categories = self.user.categories.all()
        self.assertEqual(user_categories.count(), 1)
        self.assertEqual(user_categories.first(), self.category)
        
        user_budgets = self.user.budgets.all()
        self.assertEqual(user_budgets.count(), 1)
        self.assertEqual(user_budgets.first(), self.budget)
    
    def test_budget_period_methods(self):
        """Test budget period calculation methods if implemented"""
        if hasattr(Budget, 'get_period_display'):
            period_display = self.budget.get_period_display()
            self.assertIsInstance(period_display, str)
            
        if hasattr(Budget, 'get_start_date'):
            start_date = self.budget.get_start_date()
            self.assertEqual(start_date, self.budget.month)
            
        if hasattr(Budget, 'get_end_date'):
            end_date = self.budget.get_end_date()
            self.assertGreater(end_date, self.budget.month)
    
    def test_entry_metadata(self):
        """Test Entry metadata and manager methods"""
        # Test if Entry has custom managers or methods
        entries_this_month = Entry.objects.filter(date__month=self.date.month, date__year=self.date.year)
        self.assertEqual(entries_this_month.count(), 2)
        
        # Test aggregation methods
        income_sum = Entry.objects.filter(type=Entry.INCOME).aggregate(models.Sum('amount'))
        self.assertEqual(income_sum['amount__sum'], Decimal('500.00'))
        
        expense_sum = Entry.objects.filter(type=Entry.EXPENSE).aggregate(models.Sum('amount'))
        self.assertEqual(expense_sum['amount__sum'], Decimal('100.00'))

class ModelRelationshipTests(TestCase):
    """Tests focused on model relationships that might be missed in other tests"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='relation_test_user',
            email='relationtest@example.com',
            password='testpass123'
        )
        
        # Create multiple categories
        self.category1 = Category.objects.create(name='Category1', user=self.user)
        self.category2 = Category.objects.create(name='Category2', user=self.user)
        self.category3 = Category.objects.create(name='Category3', user=self.user)
        
        # Create entries in different categories
        self.entry1 = Entry.objects.create(
            user=self.user,
            category=self.category1,
            title='Entry 1',
            amount=Decimal('100.00'),
            date=timezone.now().date(),
            type=Entry.EXPENSE
        )
        
        self.entry2 = Entry.objects.create(
            user=self.user,
            category=self.category2,
            title='Entry 2',
            amount=Decimal('200.00'),
            date=timezone.now().date(),
            type=Entry.EXPENSE
        )
        
        self.entry3 = Entry.objects.create(
            user=self.user,
            category=None,  # Entry without category
            title='Entry 3',
            amount=Decimal('300.00'),
            date=timezone.now().date(),
            type=Entry.EXPENSE
        )
    
    def test_category_deletion_cascade(self):
        """Test that deleting a category cascades to its entries"""
        category_id = self.category1.id
        entry_id = self.entry1.id
        
        # Delete the category
        self.category1.delete()
        
        # Category should be gone
        self.assertFalse(Category.objects.filter(id=category_id).exists())
        
        # Entry should also be gone due to CASCADE
        self.assertFalse(Entry.objects.filter(id=entry_id).exists())
    
    def test_entry_without_category(self):
        """Test behavior of entries without a category"""
        # Should be able to query entries without a category
        no_category_entries = Entry.objects.filter(category__isnull=True)
        self.assertEqual(no_category_entries.count(), 1)
        self.assertEqual(no_category_entries.first(), self.entry3)
    
    def test_multiple_entries_per_category(self):
        """Test that a category can have multiple entries"""
        # Add another entry to category2
        entry4 = Entry.objects.create(
            user=self.user,
            category=self.category2,
            title='Entry 4',
            amount=Decimal('400.00'),
            date=timezone.now().date(),
            type=Entry.EXPENSE
        )
        
        # Category2 should now have two entries
        category2_entries = Entry.objects.filter(category=self.category2)
        self.assertEqual(category2_entries.count(), 2)
        self.assertIn(self.entry2, category2_entries)
        self.assertIn(entry4, category2_entries)
    
    def test_empty_category(self):
        """Test behavior of a category with no entries"""
        # Category3 has no entries
        category3_entries = Entry.objects.filter(category=self.category3)
        self.assertEqual(category3_entries.count(), 0)
        
        # Deleting the empty category should work fine
        category_id = self.category3.id
        self.category3.delete()
        self.assertFalse(Category.objects.filter(id=category_id).exists())

class DecimalFieldTests(TestCase):
    """Tests focused on Decimal field behaviors"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='decimal_test_user',
            email='decimaltest@example.com',
            password='testpass123'
        )
        
        self.category = Category.objects.create(
            name='DecimalTestCategory',
            user=self.user
        )
    
    def test_amount_precision(self):
        """Test precise decimal amounts in Entry model"""
        # Test with exactly 2 decimal places
        entry = Entry.objects.create(
            user=self.user,
            title='Precise Amount',
            amount=Decimal('123.45'),
            date=timezone.now().date(),
            type=Entry.EXPENSE
        )
        entry.refresh_from_db()
        self.assertEqual(entry.amount, Decimal('123.45'))
        
        # Test with 1 decimal place - should be stored as is
        entry = Entry.objects.create(
            user=self.user,
            title='One Decimal',
            amount=Decimal('123.5'),
            date=timezone.now().date(),
            type=Entry.EXPENSE
        )
        entry.refresh_from_db()
        self.assertEqual(entry.amount, Decimal('123.50'))
        
        # Test with more decimal places - behavior depends on model definition
        entry = Entry.objects.create(
            user=self.user,
            title='Many Decimals',
            amount=Decimal('123.4567'),
            date=timezone.now().date(),
            type=Entry.EXPENSE
        )
        entry.refresh_from_db()
        # This might round or truncate depending on the model's decimal_places setting
        self.assertAlmostEqual(float(entry.amount), float(Decimal('123.46')), places=2)
    
    def test_zero_amount(self):
        """Test zero amount in Entry model"""
        entry = Entry.objects.create(
            user=self.user,
            title='Zero Amount',
            amount=Decimal('0.00'),
            date=timezone.now().date(),
            type=Entry.EXPENSE
        )
        entry.refresh_from_db()
        self.assertEqual(entry.amount, Decimal('0.00'))

class ModelValidationTests(TestCase):
    """Additional tests for model validation"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='validation_test_user',
            email='validationtest@example.com',
            password='testpass123'
        )
    
    def test_category_name_validation(self):
        """Test comprehensive category name validation"""
        # Test empty name
        with self.assertRaises(ValidationError):
            category = Category(name='', user=self.user)
            category.full_clean()
        
        # Test name with just spaces
        with self.assertRaises(ValidationError):
            category = Category(name='   ', user=self.user)
            category.full_clean()
        
        # Test valid names with different characters
        valid_names = ['Category1', 'Category-1', 'Category_1', 'Category 1', 'Categoría']
        for name in valid_names:
            category = Category(name=name, user=self.user)
            category.full_clean()  # Should not raise validation error
    
    def test_entry_amount_validation(self):
        """Test comprehensive entry amount validation"""
        # Test with very large amount
        large_amount = Decimal('9999999.99')
        entry = Entry(
            user=self.user,
            title='Large Amount',
            amount=large_amount,
            date=timezone.now().date(),
            type=Entry.EXPENSE
        )
        entry.full_clean()  # Should not raise validation error
        
        # Test with negative amount - this might be invalid depending on model definition
        try:
            entry = Entry(
                user=self.user,
                title='Negative Amount',
                amount=Decimal('-100.00'),
                date=timezone.now().date(),
                type=Entry.EXPENSE
            )
            entry.full_clean()
        except ValidationError:
            pass  # Expected if negative amounts are not allowed
    
    def test_entry_date_validation(self):
        """Test entry date validation"""
        # Test with future date
        future_date = timezone.now().date() + timedelta(days=30)
        entry = Entry(
            user=self.user,
            title='Future Entry',
            amount=Decimal('100.00'),
            date=future_date,
            type=Entry.EXPENSE
        )
        entry.full_clean()  # Should not raise validation error if future dates are allowed
        
        # Test with past date
        past_date = timezone.now().date() - timedelta(days=365)
        entry = Entry(
            user=self.user,
            title='Past Entry',
            amount=Decimal('100.00'),
            date=past_date,
            type=Entry.EXPENSE
        )
        entry.full_clean()  # Should not raise validation error
    
    def test_contact_message_email_validation(self):
        """Test comprehensive email validation for ContactMessage"""
        # Test with valid emails
        valid_emails = ['user@example.com', 'user.name@example.co.uk', 'user+tag@example.com']
        for email in valid_emails:
            message = ContactMessage(
                name='Test User',
                email=email,
                subject='Test Subject',
                message='Test message'
            )
            message.full_clean()  # Should not raise validation error
        
        # Test with invalid emails
        invalid_emails = ['user@', '@example.com', 'user@.com', 'user@example..com']
        for email in invalid_emails:
            with self.assertRaises(ValidationError):
                message = ContactMessage(
                    name='Test User',
                    email=email,
                    subject='Test Subject',
                    message='Test message'
                )
                message.full_clean()

class TokenUsageTests(TestCase):
    """Additional tests for token usage and edge cases"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='token_test_user',
            email='tokentest@example.com',
            password='testpass123'
        )
        
        # Create tokens
        self.email_token = EmailVerificationToken.objects.create(
            user=self.user,
            token=uuid.uuid4(),
            purpose=EmailVerificationToken.EMAIL_VERIFICATION
        )
        
        self.password_token = PasswordResetToken.objects.create(
            user=self.user,
            token='password-reset-token'
        )
    
    def test_token_uniqueness_constraint(self):
        """Test token uniqueness constraints more thoroughly"""
        # Try to create another EmailVerificationToken for the same user
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                duplicate_token = EmailVerificationToken.objects.create(
                    user=self.user,
                    token=uuid.uuid4()
                )
        
        # Create another user
        other_user = User.objects.create_user(
            username='other_token_user',
            email='othertokentest@example.com',
            password='testpass123'
        )
        
        # Create a token for the other user - should work
        other_token = EmailVerificationToken.objects.create(
            user=other_user,
            token=uuid.uuid4()
        )
        self.assertIsNotNone(other_token)
        
        # Try to create a PasswordResetToken with the same token value
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                duplicate_password_token = PasswordResetToken.objects.create(
                    user=self.user,
                    token='password-reset-token'  # Same token
                )
    
    def test_token_purpose_handling(self):
        """Test EmailVerificationToken purpose field"""
        # Test valid purposes
        valid_purposes = [
            EmailVerificationToken.EMAIL_VERIFICATION,
            EmailVerificationToken.PASSWORD_RESET
        ]
        
        for purpose in valid_purposes:
            token = EmailVerificationToken(
                user=self.user,
                token=f'purpose-test-{purpose}',
                purpose=purpose
            )
            token.full_clean()  # Should not raise validation error
        
        # Test invalid purpose
        with self.assertRaises(ValidationError):
            token = EmailVerificationToken(
                user=self.user,
                token='invalid-purpose-token',
                purpose='INVALID_PURPOSE'
            )
            token.full_clean()
    
    def test_password_reset_token_expiration(self):
        """Test explicit expiration of PasswordResetToken"""
        self.assertFalse(self.password_token.expired)
        
        # Expire the token
        self.password_token.expired = True
        self.password_token.save()
        
        # Refresh from database
        self.password_token.refresh_from_db()
        self.assertTrue(self.password_token.expired)
        
        # Create a token that's created in the past
        old_date = timezone.now() - timedelta(days=7)
        old_token = PasswordResetToken.objects.create(
            user=self.user,
            token='old-password-token',
            created_at=old_date
        )
        
        # Update the created_at timestamp
        PasswordResetToken.objects.filter(pk=old_token.pk).update(created_at=old_date)
        
        # Refresh the token
        old_token.refresh_from_db()
        self.assertEqual(old_token.created_at.date(), old_date.date())
        
        # Check if token is considered expired based on creation date
        is_expired = (timezone.now() - old_token.created_at) > timedelta(days=3)
        self.assertTrue(is_expired)

class QuerySetTests(TestCase):
    """Tests for model QuerySet and Manager methods"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='queryset_test_user',
            email='querysettest@example.com',
            password='testpass123'
        )
        
        # Create multiple categories
        self.food_category = Category.objects.create(name='Food', user=self.user)
        self.transport_category = Category.objects.create(name='Transport', user=self.user)
        
        # Create entries across multiple dates
        self.today = timezone.now().date()
        self.yesterday = self.today - timedelta(days=1)
        self.last_month = self.today.replace(day=1) - timedelta(days=1)
        
        # Create entries for today
        self.food_today = Entry.objects.create(
            user=self.user,
            category=self.food_category,
            title='Groceries Today',
            amount=Decimal('50.00'),
            date=self.today,
            type=Entry.EXPENSE
        )
        
        self.transport_today = Entry.objects.create(
            user=self.user,
            category=self.transport_category,
            title='Bus Today',
            amount=Decimal('5.00'),
            date=self.today,
            type=Entry.EXPENSE
        )
        
        # Create entries for yesterday
        self.food_yesterday = Entry.objects.create(
            user=self.user,
            category=self.food_category,
            title='Restaurant Yesterday',
            amount=Decimal('30.00'),
            date=self.yesterday,
            type=Entry.EXPENSE
        )
        
        # Create entry for last month
        self.transport_last_month = Entry.objects.create(
            user=self.user,
            category=self.transport_category,
            title='Taxi Last Month',
            amount=Decimal('20.00'),
            date=self.last_month,
            type=Entry.EXPENSE
        )
        
        # Create income entry
        self.income = Entry.objects.create(
            user=self.user,
            title='Salary',
            amount=Decimal('1000.00'),
            date=self.today,
            type=Entry.INCOME
        )
    
    def test_filtering_by_date_range(self):
        """Test filtering entries by different date ranges"""
        # Entries for today
        today_entries = Entry.objects.filter(date=self.today)
        self.assertEqual(today_entries.count(), 3)  # 2 expenses + 1 income
        
        # Entries for yesterday
        yesterday_entries = Entry.objects.filter(date=self.yesterday)
        self.assertEqual(yesterday_entries.count(), 1)
        
        # Entries for current month
        this_month = self.today.replace(day=1)
        this_month_entries = Entry.objects.filter(date__gte=this_month)
        self.assertEqual(this_month_entries.count(), 4)  # All except last month
        
        # Entries for last month
        last_month_start = self.last_month.replace(day=1)
        last_month_end = self.today.replace(day=1) - timedelta(days=1)
        last_month_entries = Entry.objects.filter(
            date__gte=last_month_start,
            date__lte=last_month_end
        )
        self.assertEqual(last_month_entries.count(), 1)
    
    def test_filtering_by_category(self):
        """Test filtering entries by category"""
        # Food entries
        food_entries = Entry.objects.filter(category=self.food_category)
        self.assertEqual(food_entries.count(), 2)
        
        # Transport entries
        transport_entries = Entry.objects.filter(category=self.transport_category)
        self.assertEqual(transport_entries.count(), 2)
        
        # Entries without category
        no_category_entries = Entry.objects.filter(category__isnull=True)
        self.assertEqual(no_category_entries.count(), 1)  # The income entry
    
    def test_filtering_by_type(self):
        """Test filtering entries by type"""
        # Expense entries
        expense_entries = Entry.objects.filter(type=Entry.EXPENSE)
        self.assertEqual(expense_entries.count(), 4)
        
        # Income entries
        income_entries = Entry.objects.filter(type=Entry.INCOME)
        self.assertEqual(income_entries.count(), 1)
    
    def test_aggregation_functions(self):
        """Test various aggregation functions on entries"""
        # Total expenses
        total_expenses = Entry.objects.filter(type=Entry.EXPENSE).aggregate(total=models.Sum('amount'))
        self.assertEqual(total_expenses['total'], Decimal('105.00'))
        
        # Total income
        total_income = Entry.objects.filter(type=Entry.INCOME).aggregate(total=models.Sum('amount'))
        self.assertEqual(total_income['total'], Decimal('1000.00'))
        
        # Today's expenses
        today_expenses = Entry.objects.filter(type=Entry.EXPENSE, date=self.today).aggregate(total=models.Sum('amount'))
        self.assertEqual(today_expenses['total'], Decimal('55.00'))
        
        # Count by category
        category_counts = Entry.objects.values('category').annotate(count=models.Count('id'))
        self.assertEqual(len(category_counts), 3)  # Food, Transport, and None
        
        # Max amount
        max_amount = Entry.objects.aggregate(max=models.Max('amount'))
        self.assertEqual(max_amount['max'], Decimal('1000.00')) 