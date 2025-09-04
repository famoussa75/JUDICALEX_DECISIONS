from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Ordonnance

class OrdonnanceForm(forms.ModelForm):

    class Meta:
        model = Ordonnance
        exclude = ['idAccount', 'ordonnance_text', 'created_at', 'updated_at']
        labels = {
            'numOrdonnance': "Numéro de l'ordonnance",
            'numRg': "Numéro RG",
            'dateOrdonnance': "Date de l'ordonnance",
            'president': "Président",
            'greffier': "Greffier",
            'demanderesses': "Demanderesses",
            'defenderesses': "Défenderesses",
            'avocatsDemanderesses': "Avocats Demanderesses",
            'avocatsDefenderesses': "Avocats Défenderesses",
            'objet': "Objet de l'ordonnance",
            'fichier': "Fichier PDF",
        }
        widgets = {
            'numOrdonnance': forms.TextInput(attrs={'class': 'form-control'}),
            'numRg': forms.TextInput(attrs={'class': 'form-control'}),
            'dateOrdonnance': forms.DateInput(
                attrs={'class': 'form-control', 'type': 'date'},
                format='%Y-%m-%d'
            ),
            'president': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom complet'}),
            'greffier': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom complet'}),
            'demanderesses': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'defenderesses': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'avocatsDemanderesses': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'avocatsDefenderesses': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'objet': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'fichier': forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Pré-remplir dateOrdonnance à l’édition
        if self.instance and self.instance.pk and self.instance.dateOrdonnance:
            self.initial['dateOrdonnance'] = self.instance.dateOrdonnance.strftime('%Y-%m-%d')

        # Limite de date maximale à aujourd'hui
        self.fields['dateOrdonnance'].widget.attrs['max'] = timezone.localdate().isoformat()

    def clean_dateOrdonnance(self):
        date = self.cleaned_data['dateOrdonnance']
        if date > timezone.localdate():
            raise ValidationError("La date ne peut pas être dans le futur")
        return date

    def clean_fichier(self):
        fichier = self.cleaned_data.get('fichier')
        if fichier:
            if fichier.size > 5 * 1024 * 1024:
                raise ValidationError("Le fichier ne peut pas dépasser 5 Mo")
            if not fichier.name.lower().endswith('.pdf'):
                raise ValidationError("Seuls les fichiers PDF sont acceptés")
        return fichier

  