from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from .models import Jugement

class AvocatAdmin(ImportExportModelAdmin):
    pass
@admin.register(Jugement)
class AvocatAdmin(ImportExportModelAdmin):
    pass