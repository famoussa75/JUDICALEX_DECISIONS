from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Account

@admin.register(Account)
class CustomUserAdmin(UserAdmin):
    model = Account
    list_display = (
        'username', 'email', 'first_name', 'last_name',
        'is_staff', 'adresse', 'profession',
        'telephone1', 'telephone2', 'nationalite', 'photo'
    )

    # Affichage en détail d’un utilisateur
    fieldsets = UserAdmin.fieldsets + (
        ('Informations supplémentaires', {
            'fields': ('adresse', 'profession', 'telephone1', 'telephone2', 'nationalite', 'photo'),
        }),
    )

    # Affichage du formulaire de création d’un nouvel utilisateur
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Informations supplémentaires', {
            'classes': ('wide',),
            'fields': ('adresse', 'profession', 'telephone1', 'telephone2', 'nationalite', 'photo'),
        }),
    )
