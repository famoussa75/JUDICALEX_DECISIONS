from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.conf import settings
from django.db.models import F, Value
from django.db.models.functions import Length, Replace
from django.core.paginator import Paginator

from .forms import JugementForm
from .models import Jugement

import fitz  # PyMuPDF
import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image, ImageEnhance
import logging

logger = logging.getLogger(__name__)

# ----------------------------------------------------
# AJOUT D’UN JUGEMENT
# ----------------------------------------------------
@login_required
def add_jugement(request):
    return _save_or_update_jugement(request)


# ----------------------------------------------------
# MODIFICATION D’UN JUGEMENT
# ----------------------------------------------------
@login_required
def edit_jugement(request, id):
    jugement = get_object_or_404(Jugement, idJugement=id)
    return _save_or_update_jugement(request, instance=jugement)


# ----------------------------------------------------
# FACTORISATION AJOUT/MODIF
# ----------------------------------------------------
def _save_or_update_jugement(request, instance=None):
    is_update = instance is not None
    old_date = instance.dateJugement if is_update else None  # Sauvegarde de l'ancienne date

    if request.method == 'POST':
        form = JugementForm(request.POST, request.FILES, instance=instance)

        if form.is_valid():
            jugement = form.save(commit=False)
            jugement.idAccount = request.user

            # Si la date n’est pas modifiée, on garde l’ancienne
            if not jugement.dateJugement and old_date:
                jugement.dateJugement = old_date

            fichier_pdf = request.FILES.get('decision')
            if fichier_pdf:
                if fichier_pdf.size > 20 * 1024 * 1024:  # Limite 20 Mo
                    messages.error(request, "Le fichier est trop volumineux (max 20MB)")
                    return render(request, 'jugement/add_jugement.html', {
                        'form': form,
                        'is_update': is_update
                    })

                try:
                    texte = extraction_text(fichier_pdf)
                    fichier_pdf.seek(0)
                    jugement.jugement_text = texte
                except Exception as e:
                    logger.error(f"Erreur lors de l'extraction du texte: {str(e)}")
                    messages.warning(
                        request,
                        "Erreur lors de l'extraction du texte. "
                        "Le jugement a été enregistré sans le texte intégral."
                    )
                    jugement.jugement_text = f"[ERREUR D'EXTRACTION] {str(e)}"

            jugement.save()
            form.save_m2m()

            messages.success(
                request,
                "Jugement modifié avec succès." if is_update else "Jugement enregistré avec succès."
            )
            return redirect('liste_jugement')

        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = JugementForm(instance=instance)

    return render(request, 'jugement/add_jugement.html', {
        'form': form,
        'is_update': is_update
    })


# ----------------------------------------------------
# EXTRACTION TEXTE
# ----------------------------------------------------
def extraction_text(fichier):
    """Extrait le texte d'un PDF (textuel ou scanné) avec OCR"""
    try:
        pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

        fichier.seek(0)
        pdf_bytes = fichier.read()

        texte_complet = ""
        try:
            # Extraction directe (PDF textuel)
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                texte_page = page.get_text()
                if texte_page:
                    texte_complet += texte_page + "\n"
            doc.close()
            if len(texte_complet.strip()) > 100:
                return texte_complet.strip()
        except Exception as e:
            logger.warning(f"Erreur extraction directe: {e}")

        # Extraction via OCR (PDF scanné)
        poppler_path = getattr(settings, 'POPPLER_PATH', None)
        images = convert_from_bytes(
            pdf_bytes,
            dpi=350,
            poppler_path=poppler_path,
            thread_count=2,
            fmt='jpeg'
        )

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
                logger.info(f"Page {i+1} traitée avec OCR")
            except Exception as e:
                logger.error(f"Erreur OCR page {i+1}: {str(e)}")
                texte_ocr.append(f"[ERREUR PAGE {i+1}]")

        return "\n".join(texte_ocr).strip()

    except Exception as e:
        logger.exception("Erreur grave lors de l'extraction OCR")
        raise Exception(f"Échec de l'extraction OCR: {str(e)}")


# ----------------------------------------------------
# LISTE
# ----------------------------------------------------

@login_required
def list_jugement(request):
    # On garde seulement select_related pour idAccount (qui est une ForeignKey)
    jugements_list = Jugement.objects.select_related('idAccount').order_by('-dateJugement')

    # Pagination : 7 jugements par page
    paginator = Paginator(jugements_list, 7)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'jugement/list_jugement.html', {'page_obj': page_obj})


# ----------------------------------------------------
# RECHERCHE
# ----------------------------------------------------
from django.shortcuts import render
from django.db.models import F, Value
from django.db.models.functions import Length, Replace
from .models import Jugement

def recherche_jugement(request):
    query = request.GET.get('q', '').strip()
    resultats = []
    total_resultats = 0

    if query:
        # Annoter avec le calcul d'occurrences
        jugements = Jugement.objects.annotate(
            text_length=Length('jugement_text'),
            text_length_without_query=Length(
                Replace('jugement_text', Value(query), Value(''))
            ),
        ).annotate(
            occurences=(F('text_length') - F('text_length_without_query')) / (len(query) if len(query) > 0 else 1)
        ).filter(
            jugement_text__icontains=query
        ).order_by('-occurences', '-dateJugement')

        # Exclure ceux qui ont 0 occurrences
        resultats = [j for j in jugements if j.occurences > 0]

        # Nombre total réel
        total_resultats = len(resultats)

    return render(request, 'jugement/recherche_jugement.html', {
        'query': query,
        'resultats': resultats,
        'total_resultats': total_resultats
    })



# ----------------------------------------------------
# DÉTAIL
# ----------------------------------------------------
def detail_jugement(request, id):
    jugement = get_object_or_404(Jugement, idJugement=id)
    return render(request, 'jugement/detail.html', {'jugement': jugement})

from django.shortcuts import render

def fichier_introuvable_jugement(request, path):
    return render(request, "jugement/errors/fichier_introuvable.html", {"path": path})


