from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from ..models import Category, Entry, ContactMessage

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