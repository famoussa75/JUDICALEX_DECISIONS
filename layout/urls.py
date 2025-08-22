
from django.urls import path
from . import views

urlpatterns = [
    path('base/', views.layout, name='layout_base'),
    path('', views.dasboard, name='dashbord'),
    
]