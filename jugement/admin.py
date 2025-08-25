# admin.py
from django.contrib import admin
from .models import Jugement

@admin.register(Jugement)
class JugementAdmin(admin.ModelAdmin):
    list_display = (
        'idJugement', 
        'numJugement', 
        'dateJugement', 
        'president', 
        'greffier', 
        'demanderesses', 
        'defenderesses', 
        'idAccount'
    )
    ordering = ('idJugement',)  # Tri croissant par IdJugement
    search_fields = ('numJugement', 'president', 'greffier', 'demanderesses', 'defenderesses')
    list_filter = ('dateJugement', 'president', 'greffier')