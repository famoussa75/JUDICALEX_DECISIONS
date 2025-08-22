from django.contrib.auth.models import AbstractUser
from django.db import models

class Account(AbstractUser):  # hérite de AbstractUser
    adresse = models.CharField(max_length=255)
    profession = models.CharField(max_length=100)
    telephone1 = models.CharField(max_length=20)
    telephone2 = models.CharField(max_length=20, blank=True, null=True)
    nationalite = models.CharField(max_length=50)
    photo = models.ImageField(upload_to='photos/', blank=True, null=True)

    def __str__(self):
        return f"{self.username} - {self.profession}"
