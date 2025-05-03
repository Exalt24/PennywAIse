from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Creates test accounts'

    def handle(self, *args, **options):
        """
        Creates a single test user with default categories (via your post-save signals).
        """
        username = 'testuser'
        email = 'test@example.com'
        password = 'password123'

        # If it already exists, warn and exit
        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING('Test user already exists'))
            return

        # Otherwise, try to create it
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )
            self.stdout.write(self.style.SUCCESS(f'Created test user: {user.username}'))
            self.stdout.write(self.style.SUCCESS('Default categories created via signal'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Error creating test user: {e}'))
