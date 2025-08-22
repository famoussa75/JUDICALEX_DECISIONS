from django.db import models
from account.models import Account

class Jugement(models.Model):
    idJugement = models.AutoField(primary_key=True)
    numJugement = models.CharField(max_length=100,null=True)
    numRg = models.CharField(max_length=100, null=True, blank=True)
    dateJugement = models.DateField()
    president = models.CharField(max_length=100)
    jugeConsulaire1 = models.CharField(max_length=255, null=True )
    jugeConsulaire2 = models.CharField(max_length=255, null=True )
    greffier = models.CharField(max_length=100)
    demanderesses = models.CharField(max_length=255)  
    defenderesses = models.CharField(max_length=255)
    avocatsDemanderesses = models.TextField()
    avocatsDefenderesses = models.TextField()
    objet = models.TextField()
    decision = models.FileField(upload_to='decisions/')
    jugement_text = models.TextField(blank=True, null=True) 
    idAccount = models.ForeignKey(Account, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True,null=True)
    updated_at = models.DateTimeField(auto_now=True,null=True)


    def __str__(self):
        return f"Jugement N° {self.numJugement}"
