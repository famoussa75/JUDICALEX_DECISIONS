from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.conf import settings
from django.db.models import F, Value
from django.db.models.functions import Length, Replace
from django.core.paginator import Paginator
from django.http import Http404
from django.views.static import serve
import os

from .forms import OrdonnanceForm
from .models import Ordonnance

import fitz  # PyMuPDF
import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image, ImageEnhance
import logging

logger = logging.getLogger(__name__)

# ----------------------------------------------------
# AJOUT D'ORDONNANCE
# ----------------------------------------------------
@login_required
def add_ordonnance(request):
    return _save_or_update_ordonnance(request)

# ----------------------------------------------------
# MODIFICATION D'ORDONNANCE
# ----------------------------------------------------
@login_required
def edit_ordonnance(request, id):
    ordonnance = get_object_or_404(Ordonnance, idOrdonnance=id)
    return _save_or_update_ordonnance(request, instance=ordonnance)

# ----------------------------------------------------
# FACTORISATION AJOUT/MODIF
# ----------------------------------------------------
def _save_or_update_ordonnance(request, instance=None):
    is_update = instance is not None
    old_date = instance.dateOrdonnance if is_update else None

    if request.method == 'POST':
        form = OrdonnanceForm(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            ordonnance = form.save(commit=False)

            # Attribution de l'utilisateur connecté
            if hasattr(request.user, 'account'):
                ordonnance.idAccount = request.user.account
            else:
                ordonnance.idAccount = request.user

            # Si la date est vide, garder l'ancienne
            if not ordonnance.dateOrdonnance and old_date:
                ordonnance.dateOrdonnance = old_date

            # Gestion du PDF
            fichier_pdf = request.FILES.get('fichier')
            if fichier_pdf:
                try:
                    texte = extraction_text(fichier_pdf)
                    fichier_pdf.seek(0)
                    ordonnance.ordonnance_text = texte
                except Exception as e:
                    logger.error(f"Erreur extraction OCR : {str(e)}")
                    messages.warning(
                        request,
                        "Erreur lors de l'extraction du texte. L'ordonnance a été enregistrée sans le texte intégral."
                    )
                    ordonnance.ordonnance_text = f"[ERREUR D'EXTRACTION] {str(e)}"

            ordonnance.save()
            form.save_m2m()

            messages.success(request, "Ordonnance modifiée avec succès." if is_update else "Ordonnance enregistrée avec succès.")
            return redirect('liste_ordonnance')

        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")

    else:
        form = OrdonnanceForm(instance=instance)

    return render(request, 'ordonnance/add_ordonnance.html', {
        'form': form,
        'is_update': is_update
    })

# ----------------------------------------------------
# EXTRACTION TEXTE PDF + OCR
# ----------------------------------------------------
def extraction_text(fichier):
    """Extrait le texte d'un PDF (textuel ou scanné) avec OCR"""
    try:
        pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

        fichier.seek(0)
        pdf_bytes = fichier.read()

        # Vérification taille fichier (5MB max)
        if len(pdf_bytes) > 5 * 1024 * 1024:
            raise Exception("Fichier trop volumineux (max 5MB)")

        texte_complet = ""
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            for page in doc:
                texte_page = page.get_text()
                if texte_page:
                    texte_complet += texte_page + "\n"
            doc.close()
            if len(texte_complet.strip()) > 100:
                return texte_complet.strip()
        except Exception as e:
            logger.warning(f"Erreur extraction directe : {e}")

        # Conversion en images si pas assez de texte
        poppler_path = getattr(settings, 'POPPLER_PATH', None)
        images = convert_from_bytes(pdf_bytes, dpi=350, poppler_path=poppler_path)

        texte_ocr = []
        for i, img in enumerate(images):
            try:
                img = img.convert('L')
                img = ImageEnhance.Contrast(img).enhance(1.5)
                img = ImageEnhance.Sharpness(img).enhance(1.2)
                img = img.point(lambda x: 0 if x < 140 else 255)

                if img.width > 2000:
                    ratio = 2000 / img.width
                    new_height = int(img.height * ratio)
                    img = img.resize((2000, new_height), Image.LANCZOS)

                config = '--psm 6 -c preserve_interword_spaces=1'
                text = pytesseract.image_to_string(img, lang='fra+eng', config=config)
                texte_ocr.append(text)
                logger.info(f"OCR - Page {i+1} traitée")
            except Exception as e:
                logger.error(f"Erreur OCR page {i+1}: {str(e)}")
                texte_ocr.append(f"[ERREUR PAGE {i+1}]")

        return "\n".join(texte_ocr).strip()

    except Exception as e:
        logger.exception("Erreur grave lors de l'extraction OCR")
        raise Exception(f"Échec de l'extraction OCR: {str(e)}")

# ----------------------------------------------------
# LISTE DES ORDONNANCES
# ----------------------------------------------------
@login_required
def list_ordonnance(request):
    # On garde seulement select_related pour idAccount (ForeignKey)
    ordonnances_list = Ordonnance.objects.select_related('idAccount').order_by('-dateOrdonnance')

    # Pagination : 7 ordonnances par page
    paginator = Paginator(ordonnances_list, 7)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'ordonnance/list_ordonnance.html', {'page_obj': page_obj})

# ----------------------------------------------------
# RECHERCHE
# ----------------------------------------------------
def recherche_ordonnance(request):
    query = request.GET.get('q', '').strip()
    resultats = []
    total_resultats = 0

    if query:
        # Annoter avec le calcul d'occurrences
        ordonnances = Ordonnance.objects.annotate(
            text_length=Length('ordonnance_text'),
            text_length_without_query=Length(
                Replace('ordonnance_text', Value(query), Value(''))
            ),
        ).annotate(
            occurences=(F('text_length') - F('text_length_without_query')) / (len(query) if len(query) > 0 else 1)
        ).filter(
            ordonnance_text__icontains=query
        ).order_by('-occurences', '-dateOrdonnance')

        # Exclure ceux qui ont 0 occurrences
        resultats = [o for o in ordonnances if o.occurences > 0]

        # Nombre total réel
        total_resultats = len(resultats)

    return render(request, 'ordonnance/recherche_ordonnance.html', {
        'query': query,
        'resultats': resultats,
        'total_resultats': total_resultats
    })

# ----------------------------------------------------
# DÉTAIL
# ----------------------------------------------------
def detail_ordonnance(request, id):
    ordonnance = get_object_or_404(Ordonnance, idOrdonnance=id)
    return render(request, 'ordonnance/detail.html', {'ordonnance': ordonnance})

# ----------------------------------------------------
# GESTION DES FICHIERS INTROUVABLES
# ----------------------------------------------------
def fichier_introuvable_ordonnance(request, path):
    return render(request, "ordonnance/errors/fichier_introuvable.html", {"path": path})


