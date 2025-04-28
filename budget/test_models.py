from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from .models import Category, Entry

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
        """Test that different users can have categories with the same name"""
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpass123'
        )
        
        # Create category with same name for different user
        other_category = Category.objects.create(
            name='Food',
            user=other_user
        )
        
        # Both categories should exist
        self.assertEqual(Category.objects.filter(name='Food').count(), 2)
        
        # But they're associated with different users
        self.assertEqual(Category.objects.filter(user=self.user, name='Food').count(), 1)
        self.assertEqual(Category.objects.filter(user=other_user, name='Food').count(), 1)

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
        # Delete the category
        self.category.delete()
        
        # Refresh entry from db and check its category is None
        self.entry.refresh_from_db()
        self.assertIsNone(self.entry.category)
        
    def test_entry_deleted_when_user_deleted(self):
        """Test that entries are deleted when the user is deleted"""
        # Record the entry ID
        entry_id = self.entry.id
        
        # Delete the user
        self.user.delete()
        
        # Check that entry no longer exists
        self.assertEqual(Entry.objects.filter(id=entry_id).count(), 0) 