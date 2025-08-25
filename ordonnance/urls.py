from django.urls import path
from . import views

urlpatterns = [
    path('add_ordonnance/', views.add_ordonnance, name='nouveau_ordonnance'),
    path('edit_ordonnance/<int:id>/', views.edit_ordonnance, name='edit_ordonnance'),  
    path('list_ordonnance/', views.list_ordonnance, name='liste_ordonnance'),
    path('recherche_ordonnance/', views.recherche_ordonnance, name='recherche_ordonnance'),
    path('ordonnance/<int:id>/', views.detail_ordonnance, name='detail_ordonnance'),

]

