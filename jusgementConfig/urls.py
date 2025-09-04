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
    Servir les fichiers média s'ils existent,
    sinon rediriger vers une page d'erreur personnalisée.
    """
    file_path = os.path.join(document_root, path)
    if os.path.exists(file_path):
        return serve(request, path, document_root=document_root)
    else:
        if path.startswith('decisions/'):
            return fichier_introuvable_jugement(request, path)
        elif path.startswith('ordonnances/'):
            return fichier_introuvable_ordonnance(request, path)
        else:
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
    urlpatterns += [
        re_path(
            r'^media/(?P<path>.*)$',
            lambda request, path: serve_media_or_custom_404(request, path, settings.MEDIA_ROOT)
        ),
    ]
else:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
