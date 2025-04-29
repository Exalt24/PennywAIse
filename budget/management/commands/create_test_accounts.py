from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Creates test accounts'

    def handle(self, *args, **kwargs):
        # Create test user
        if not User.objects.filter(username='testuser').exists():
            user = User.objects.create_user(
                username='testuser',
                email='test@example.com',
                password='password123'
            )
            self.stdout.write(self.style.SUCCESS(f'Created test user: {user.username}'))
            self.stdout.write(self.style.SUCCESS(f'Default categories created via signal'))
        else:
            self.stdout.write(self.style.WARNING('Test user already exists'))