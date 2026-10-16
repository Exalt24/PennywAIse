from budget.models import Category


def make_category(**kwargs):
    """Return the user's category with this name, creating it if needed.

    A post_save signal gives every new user the default categories (Food,
    Transport, Entertainment, Utilities, Other), so a fixture that calls
    Category.objects.create for one of those names hits the unique
    (user, name) constraint. Tests that exercise that constraint on purpose
    keep calling create directly.
    """
    category, _ = Category.objects.get_or_create(**kwargs)
    return category
