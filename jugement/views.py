from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.conf import settings
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.utils.text import slugify

from .forms import JugementForm
from .models import Jugement

import fitz  # PyMuPDF
import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image, ImageEnhance
import logging
import re
import unicodedata
import datetime
import os
import zipfile
import shutil

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
    old_date = instance.dateJugement if is_update else None

    if request.method == 'POST':
        form = JugementForm(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            jugement = form.save(commit=False)
            jugement.idAccount = request.user
            if not jugement.dateJugement and old_date:
                jugement.dateJugement = old_date

            fichier_pdf = request.FILES.get('decision')
            if fichier_pdf:
                if fichier_pdf.size > 20 * 1024 * 1024:
                    messages.error(request, "Le fichier est trop volumineux (max 20MB)")
                    return render(request, 'jugement/add_jugement.html', {'form': form, 'is_update': is_update})
                try:
                    texte = extraction_text(fichier_pdf)
                    fichier_pdf.seek(0)
                    jugement.jugement_text = texte
                except Exception as e:
                    logger.error(f"Erreur lors de l'extraction du texte: {str(e)}")
                    messages.warning(request, "Erreur lors de l'extraction du texte. Le jugement a été enregistré sans le texte intégral.")
                    jugement.jugement_text = f"[ERREUR D'EXTRACTION] {str(e)}"

            jugement.save()
            form.save_m2m()
            messages.success(request, "Jugement modifié avec succès." if is_update else "Jugement enregistré avec succès.")
            return redirect('liste_jugement')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = JugementForm(instance=instance)

    return render(request, 'jugement/add_jugement.html', {'form': form, 'is_update': is_update})

# ----------------------------------------------------
# EXTRACTION TEXTE
# ----------------------------------------------------
def extraction_text(fichier):
    try:
        pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        fichier.seek(0)
        pdf_bytes = fichier.read()
        texte_complet = ""
        try:
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

        poppler_path = getattr(settings, 'POPPLER_PATH', None)
        images = convert_from_bytes(pdf_bytes, dpi=350, poppler_path=poppler_path, thread_count=2, fmt='jpeg')
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
    jugements_list = Jugement.objects.select_related('idAccount').order_by('-idJugement')
    paginator = Paginator(jugements_list, 7)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'jugement/list_jugement.html', {'page_obj': page_obj})

# ----------------------------------------------------
# TRAITER SÉLECTION
# ----------------------------------------------------
@login_required
def traiter_selection(request):
    if request.method == "POST":
        ids = request.POST.getlist("jugements_selectionnes")
        if not ids:
            messages.warning(request, "Aucun jugement sélectionné.")
            return redirect("recherche_jugement")

        jugements = Jugement.objects.filter(idJugement__in=ids)
        user_folder = os.path.join(settings.MEDIA_ROOT, f"selection_utilisateur_{request.user.id}")
        if os.path.exists(user_folder):
            shutil.rmtree(user_folder)
        os.makedirs(user_folder, exist_ok=True)

        fichiers_copier = []
        for j in jugements:
            if j.decision and os.path.exists(j.decision.path):
                dest_file = os.path.join(user_folder, f"{slugify(j.numJugement)}_{os.path.basename(j.decision.name)}")
                shutil.copy(j.decision.path, dest_file)
                fichiers_copier.append(dest_file)

        if not fichiers_copier:
            messages.warning(request, "Aucun fichier PDF disponible pour les jugements sélectionnés.")
            return redirect("recherche_jugement")

        zip_filename = os.path.join(settings.MEDIA_ROOT, f"selection_utilisateur_{request.user.id}.zip")
        with zipfile.ZipFile(zip_filename, 'w') as zipf:
            for file_path in fichiers_copier:
                zipf.write(file_path, arcname=os.path.basename(file_path))

        with open(zip_filename, 'rb') as f:
            response = HttpResponse(f.read(), content_type='application/zip')
            response['Content-Disposition'] = 'attachment; filename="selection_jugements.zip"'
            return response

# ----------------------------------------------------
# Helpers de normalisation
# ----------------------------------------------------
PUNCT_MAP = {"\u2019": "'", "\u2018": "'", "\u201C": '"', "\u201D": '"', "\u00A0": ' '}
def _normalize_punct(s: str) -> str:
    if not s: return ""
    for k, v in PUNCT_MAP.items(): s = s.replace(k, v)
    return " ".join(s.split())
def _strip_accents(s: str) -> str:
    if not s: return ""
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
def norm_for_match(s: str) -> str:
    s = _normalize_punct(s)
    s = _strip_accents(s)
    return s.lower()
def count_non_overlapping(haystack: str, needle: str) -> int:
    if not needle: return 0
    return haystack.count(needle)

# ----------------------------------------------------
# RECHERCHE
# ----------------------------------------------------
def recherche_jugement(request):
    query = (request.GET.get('q') or '').strip()
    resultats = []
    total_resultats = 0
    if query:
        q_norm_apost = _normalize_punct(query)
        q_alt = q_norm_apost.replace("'", "’") if "'" in q_norm_apost else q_norm_apost.replace("’", "'")
        mots_bruts = [m for m in re.findall(r"[A-Za-zÀ-ÿ0-9']+", q_norm_apost) if len(m) > 1]
        phrase_cond = (Q(jugement_text__icontains=query) | Q(jugement_text__icontains=q_norm_apost) | Q(jugement_text__icontains=q_alt))
        mots_cond = Q()
        for w in mots_bruts:
            w_alt = w.replace("’", "'") if "’" in w else w.replace("'", "’")
            mots_cond |= Q(jugement_text__icontains=w) | Q(jugement_text__icontains=w_alt)
        combined = phrase_cond | mots_cond
        qs = Jugement.objects.filter(combined).order_by('-dateJugement')
        norm_phrase_1 = norm_for_match(q_norm_apost)
        norm_phrase_2 = norm_for_match(q_alt) if q_alt != q_norm_apost else norm_phrase_1
        mots_norm = [norm_for_match(w) for w in mots_bruts]
        tmp = []
        for j in qs:
            txt = j.jugement_text or ""
            tnorm = norm_for_match(txt)
            phrase_count = count_non_overlapping(tnorm, norm_phrase_1)
            if norm_phrase_2 != norm_phrase_1:
                phrase_count = max(phrase_count, count_non_overlapping(tnorm, norm_phrase_2))
            words_count = sum(count_non_overlapping(tnorm, w) for w in mots_norm)
            score = phrase_count * 10 + words_count
            if phrase_count > 0 or words_count > 0:
                j.occurences = score
                tmp.append(j)
        tmp.sort(key=lambda x: (getattr(x, 'occurences', 0), x.dateJugement or datetime.date.min), reverse=True)
        resultats = tmp
        total_resultats = len(resultats)
    return render(request, 'jugement/recherche_jugement.html', {'query': query, 'resultats': resultats, 'total_resultats': total_resultats})

# ----------------------------------------------------
# DETAIL
# ----------------------------------------------------
def detail_jugement(request, id):
    jugement = get_object_or_404(Jugement, idJugement=id)
    return render(request, 'jugement/detail.html', {'jugement': jugement})

def fichier_introuvable_jugement(request, path):
    return render(request, "jugement/errors/fichier_introuvable.html", {"path": path})

from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.http import FileResponse
import os

@login_required
def voir_pdf_jugement(request, id):
    jugement = get_object_or_404(Jugement, idJugement=id)
    
    # Si le fichier n'existe pas, rediriger vers page d'erreur
    if not jugement.decision or not os.path.exists(jugement.decision.path):
        return render(request, "jugement/errors/fichier_introuvable.html", {
            "path": jugement.decision.name if jugement.decision else "Fichier manquant"
        })
    
    # Sinon, renvoyer le PDF
    return FileResponse(open(jugement.decision.path, 'rb'), content_type='application/pdf')
