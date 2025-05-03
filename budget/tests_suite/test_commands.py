from django.test import TestCase
from django.core.management import call_command
from django.contrib.auth import get_user_model
from io import StringIO
from django.core.management.base import CommandError
from unittest.mock import patch, MagicMock

User = get_user_model()

class CommandTests(TestCase):
    def test_create_test_accounts_command(self):
        """Test the create_test_accounts command creates a user properly"""
        # Make sure test user doesn't exist yet
        User.objects.filter(username='testuser').delete()
        
        # Call the command with captured output
        out = StringIO()
        call_command('create_test_accounts', stdout=out)
        
        # Check output indicates success
        self.assertIn('Created test user: testuser', out.getvalue())
        self.assertIn('Default categories created via signal', out.getvalue())
        
        # Check user exists now
        self.assertTrue(User.objects.filter(username='testuser').exists())
        user = User.objects.get(username='testuser')
        self.assertEqual(user.email, 'test@example.com')
        
        # Test calling it a second time (for the already exists branch)
        out = StringIO()
        call_command('create_test_accounts', stdout=out)
        self.assertIn('Test user already exists', out.getvalue())
        
    @patch('budget.management.commands.create_test_accounts.User.objects.create_user')
    def test_create_test_accounts_error_handling(self, mock_create_user):
        """Test error handling in create_test_accounts command"""
        # Make sure test user doesn't exist
        User.objects.filter(username='testuser').delete()
        
        # Set up mock to raise exception
        mock_create_user.side_effect = Exception("Test error")
        
        # Call the command with captured output
        out = StringIO()
        err = StringIO()
        
        # Should not raise an uncaught exception
        call_command('create_test_accounts', stdout=out, stderr=err)
        
        # Check error output
        self.assertIn('Error creating test user', err.getvalue()) 