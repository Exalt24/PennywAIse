from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from ..models import ContactMessage
from ..admin import ContactMessageAdmin
from django.contrib.admin.sites import AdminSite
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.test.client import RequestFactory

User = get_user_model()

class MockRequest:
    def __init__(self):
        self.session = {}
        self._messages = FallbackStorage(None)

class ContactMessageAdminTest(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpassword123'
        )
        self.client = Client()
        self.client.login(username='admin', email='admin@example.com', password='adminpassword123')
        
        # Create test messages
        self.message1 = ContactMessage.objects.create(
            name='User One',
            email='user1@example.com',
            subject='Subject One',
            message='Message from User One',
            is_read=False
        )
        self.message2 = ContactMessage.objects.create(
            name='User Two',
            email='user2@example.com',
            subject='Subject Two',
            message='Message from User Two',
            is_read=False
        )
        
        # Set up admin site
        self.site = AdminSite()
        self.admin = ContactMessageAdmin(ContactMessage, self.site)
        
    def test_mark_as_read_action(self):
        """Test the admin action to mark messages as read"""
        # Create a mock request
        request = RequestFactory().get('/')
        middleware = SessionMiddleware(lambda req: None)
        middleware.process_request(request)
        request.session.save()
        request.user = self.admin_user
        
        # Execute the action
        queryset = ContactMessage.objects.filter(pk__in=[self.message1.pk, self.message2.pk])
        self.admin.mark_as_read(request, queryset)
        
        # Refresh from database
        self.message1.refresh_from_db()
        self.message2.refresh_from_db()
        
        # Check that messages are marked as read
        self.assertTrue(self.message1.is_read)
        self.assertTrue(self.message2.is_read)
        
    def test_mark_as_unread_action(self):
        """Test the admin action to mark messages as unread"""
        # Mark messages as read first
        self.message1.is_read = True
        self.message1.save()
        self.message2.is_read = True
        self.message2.save()
        
        # Create a mock request
        request = RequestFactory().get('/')
        middleware = SessionMiddleware(lambda req: None)
        middleware.process_request(request)
        request.session.save()
        request.user = self.admin_user
        
        # Execute the action
        queryset = ContactMessage.objects.filter(pk__in=[self.message1.pk, self.message2.pk])
        self.admin.mark_as_unread(request, queryset)
        
        # Refresh from database
        self.message1.refresh_from_db()
        self.message2.refresh_from_db()
        
        # Check that messages are marked as unread
        self.assertFalse(self.message1.is_read)
        self.assertFalse(self.message2.is_read)
        
    def test_admin_list_display(self):
        """Test that the admin list displays the correct fields"""
        response = self.client.get(reverse('admin:budget_contactmessage_changelist'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'User One')
        self.assertContains(response, 'user1@example.com')
        self.assertContains(response, 'Subject One')
        
    def test_admin_search(self):
        """Test that the admin search works correctly"""
        response = self.client.get(
            reverse('admin:budget_contactmessage_changelist') + '?q=One'
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'User One')
        self.assertNotContains(response, 'User Two')  # Shouldn't be in search results 