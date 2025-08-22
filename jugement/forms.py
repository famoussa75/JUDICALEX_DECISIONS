from django import forms
from .models import Jugement

class JugementForm(forms.ModelForm):
 
    class Meta:
        model = Jugement
        exclude = ['idAccount', 'jugement_text']
        labels = {
            'numJugement': "Numéro du Jugement",
            'numRg': "Numéro RG",
            'dateJugement': "Date du Jugement",
            'president': "Président",
            'jugeConsulaire1': "Juge Consulaire 1",
            'jugeConsulaire2': "Juge Consulaire 2",
            'greffier': "Greffier",
            'demanderesses': "Demanderesse",
            'defenderesses': "Défenderesses",
            'avocatsDemanderesses': "Avocats Demanderesses",
            'avocatsDefenderesses': "Avocats Défenderesses",
            'objet': "Objet du Jugement",
            'decision': "Dispositif :",
            'jugement_text': "Texte intégral du jugement",
        }
        widgets = {
            'numJugement': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Exemple : 001'}),
            'numRg': forms.TextInput(attrs={'class': 'form-control'}),
            'dateJugement': forms.DateInput(
                attrs={'class': 'form-control', 'type': 'date'},
                format='%Y-%m-%d'
            ),
            'president': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom complet'}),
            'jugeConsulaire1': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom complet'}),
            'jugeConsulaire2': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom complet'}),
            'greffier': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom complet'}),
            'demanderesses': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'defenderesses': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'avocatsDemanderesses': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'avocatsDefenderesses': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'objet': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'decision': forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf'}),
            'jugement_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 6, 'readonly': 'readonly'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Important pour pré-remplir dateJugement à l’édition
        if self.instance and self.instance.pk and self.instance.dateJugement:
            self.initial['dateJugement'] = self.instance.dateJugement.strftime('%Y-%m-%d')
