from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Category

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_default_categories(sender, instance, created, **kwargs):
    if not created:
        return

    # list whatever defaults you want
    default_names = [
        "Food",
        "Transport",
        "Entertainment",
        "Utilities",
        "Other",
    ]

    for name in default_names:
        Category.objects.create(user=instance, name=name)
