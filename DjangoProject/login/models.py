from random import choices
from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    ROLE_CHOICES = [('customer','Customer'),
                    ('merchant','Merchant'),]
    role = models.CharField(choices=ROLE_CHOICES, max_length=20, default='customer')
    address = models.CharField(max_length=100, default='',blank=True, null=True)

    def __str__(self):
        return self.username