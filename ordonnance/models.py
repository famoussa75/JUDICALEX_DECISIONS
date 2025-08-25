from django.db import models
from account.models import Account


class Ordonnance(models.Model):
    idOrdonnance = models.AutoField(primary_key=True)
    numOrdonnance = models.CharField(max_length=100,  null=True, blank=True)
    numRg = models.CharField(max_length=100, null=True, blank=True)
    dateOrdonnance = models.DateField()
    president = models.CharField(max_length=100)
    greffier = models.CharField(max_length=100)
    demanderesses = models.CharField(max_length=255)  
    defenderesses = models.CharField(max_length=255) 
    avocatsDemanderesses = models.TextField()
    avocatsDefenderesses = models.TextField()
    objet = models.TextField()
    fichier = models.FileField(upload_to='ordonnances/')
    ordonnance_text = models.TextField(blank=True, null=True) 
    idAccount = models.ForeignKey(Account, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True,null=True)
    updated_at = models.DateTimeField(auto_now=True,null=True)

    def __str__(self):
        return f"Ordonnance N° {self.numOrdonnance}"