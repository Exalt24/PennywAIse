
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()

def purge_unactivated_users():
    """
    Delete any users who never activated their account within 48 hours.
    """
    cutoff = timezone.now() - timezone.timedelta(hours=48)
    qs = User.objects.filter(is_active=False, date_joined__lt=cutoff)
    count = qs.count()
    qs.delete()
    return f"Purged {count} unactivated users."