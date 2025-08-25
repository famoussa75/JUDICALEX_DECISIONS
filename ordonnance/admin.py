from django.contrib import admin

# Register your models here.
from .models import Ordonnance
from import_export.admin import ImportExportModelAdmin
@admin.register(Ordonnance)
class OrdonnanceAdmin(ImportExportModelAdmin):  
    list_display = ('idOrdonnance', 'numOrdonnance', 'dateOrdonnance', 'president', 'greffier', 'demanderesses', 'defenderesses', 'idAccount')
    search_fields = ('numOrdonnance', 'numRg', 'president', 'greffier', 'demanderesses', 'defenderesses')
    list_filter = ('dateOrdonnance', 'president', 'greffier')
    ordering = ('-dateOrdonnance',)