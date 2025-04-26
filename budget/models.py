from django.db import models
from django.conf import settings

class Category(models.Model):
    name = models.CharField(max_length=50)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

class Entry(models.Model):
    INCOME = 'IN'
    EXPENSE = 'EX'
    TYPE_CHOICES = [(INCOME, 'Income'), (EXPENSE, 'Expense')]

    user     = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL)
    title    = models.CharField(max_length=100)
    amount   = models.DecimalField(max_digits=10, decimal_places=2)
    date     = models.DateField()
    type     = models.CharField(max_length=2, choices=TYPE_CHOICES)
    notes    = models.TextField(blank=True)
