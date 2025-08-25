"""
URL configuration for jusgementConfig project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from django.views.static import serve
import os

from jugement.views import fichier_introuvable_jugement
from ordonnance.views import fichier_introuvable_ordonnance

def serve_media_or_custom_404(request, path, document_root):
    """
    Vue personnalisée pour servir les fichiers média s'ils existent,
    ou rediriger vers une page d'erreur personnalisée s'ils n'existent pas.
    """
    file_path = os.path.join(document_root, path)
    
    # Vérifier si le fichier existe physiquement
    if os.path.exists(file_path):
        # Servir le fichier normalement
        return serve(request, path, document_root=document_root)
    else:
        # Rediriger vers la vue d'erreur appropriée
        if path.startswith('decisions/'):
            return fichier_introuvable_jugement(request, path)
        elif path.startswith('ordonnances/'):
            return fichier_introuvable_ordonnance(request, path)
        else:
            # Pour les autres types de fichiers, utiliser la 404 par défaut
            from django.http import Http404
            raise Http404("Fichier non trouvé")

urlpatterns = [
    path('', lambda request: redirect('login')),
    path('accunt/', include('account.urls')),
    path('admin/', admin.site.urls),
    path('dasbord/', include('layout.urls')),
    path('jugement/', include('jugement.urls')),
    path('ordonnance/', include('ordonnance.urls')),
]

if settings.DEBUG:
    # Remplacer le service statique standard par notre gestion personnalisée
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', 
                lambda request, path: serve_media_or_custom_404(request, path, settings.MEDIA_ROOT)),
    ]
else:
    # En production, servir les fichiers statiques normalement
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)