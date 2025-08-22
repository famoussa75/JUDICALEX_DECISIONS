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
from jugement.views import fichier_introuvable_jugement
from ordonnance.views import fichier_introuvable_ordonnance

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
        re_path(r'^media/decisions/(?P<path>.*)$', fichier_introuvable_jugement),
        re_path(r'^media/ordonnances/(?P<path>.*)$', fichier_introuvable_ordonnance),
    ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

