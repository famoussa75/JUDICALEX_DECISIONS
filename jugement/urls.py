from django.urls import path
from . import views

urlpatterns = [
    path('add_jugement/', views.add_jugement, name='nouveau_jugement'),
    path('edit_jugement/<int:id>/', views.edit_jugement, name='edit_jugement'),
    path('list_jugement/', views.list_jugement, name='liste_jugement'),
    path('recherche-jugement/', views.recherche_jugement, name='recherche_jugement'),
    path('jugement/<int:id>/', views.detail_jugement, name='detail_jugement'),
    path('selection/', views.traiter_selection, name='traiter_selection'),
    path('jugement/<int:id>/pdf/', views.voir_pdf_jugement, name='voir_pdf_jugement'),

]