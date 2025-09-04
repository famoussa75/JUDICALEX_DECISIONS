from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.conf import settings
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import FileResponse, HttpResponse
from django.utils.text import slugify

from .forms import OrdonnanceForm
from .models import Ordonnance

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
# AJOUT D’ORDONNANCE
# ----------------------------------------------------
@login_required
def add_ordonnance(request):
    return _save_or_update_ordonnance(request)

# ----------------------------------------------------
# MODIFICATION D’ORDONNANCE
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
            ordonnance.idAccount = getattr(request.user, 'account', request.user)

            # Si la date est vide, garder l'ancienne
            if not ordonnance.dateOrdonnance and old_date:
                ordonnance.dateOrdonnance = old_date

            # Gestion du PDF
            fichier_pdf = request.FILES.get('fichier')
            if fichier_pdf:
                if fichier_pdf.size > 5 * 1024 * 1024:
                    messages.error(request, "Le fichier est trop volumineux (max 5MB).")
                    return render(request, 'ordonnance/add_ordonnance.html', {'form': form, 'is_update': is_update})
                try:
                    texte = extraction_text(fichier_pdf)
                    fichier_pdf.seek(0)
                    ordonnance.ordonnance_text = texte
                except Exception as e:
                    logger.error(f"Erreur OCR : {str(e)}")
                    messages.warning(request,
                        "Erreur lors de l'extraction du texte. L'ordonnance a été enregistrée sans le texte intégral.")
                    ordonnance.ordonnance_text = f"[ERREUR D'EXTRACTION] {str(e)}"

            ordonnance.save()
            form.save_m2m()
            messages.success(request,
                "Ordonnance modifiée avec succès." if is_update else "Ordonnance enregistrée avec succès.")
            return redirect('liste_ordonnance')

        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = OrdonnanceForm(instance=instance)

    return render(request, 'ordonnance/add_ordonnance.html', {'form': form, 'is_update': is_update})

# ----------------------------------------------------
# EXTRACTION TEXTE PDF + OCR
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
            logger.warning(f"Erreur extraction directe : {e}")

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
    ordonnances_list = Ordonnance.objects.select_related('idAccount').order_by('-idOrdonnance')
    paginator = Paginator(ordonnances_list, 7)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'ordonnance/list_ordonnance.html', {'page_obj': page_obj})

# ----------------------------------------------------
# RECHERCHE ORDONNANCE
# ----------------------------------------------------
def recherche_ordonnance(request):
    query = (request.GET.get('q') or '').strip()
    resultats = []
    total_resultats = 0
    if query:
        q_norm_apost = _normalize_punct(query)
        q_alt = q_norm_apost.replace("'", "’") if "'" in q_norm_apost else q_norm_apost.replace("’", "'")
        mots_bruts = [m for m in re.findall(r"[A-Za-zÀ-ÿ0-9']+", q_norm_apost) if len(m) > 1]
        phrase_cond = (Q(ordonnance_text__icontains=query) |
                       Q(ordonnance_text__icontains=q_norm_apost) |
                       Q(ordonnance_text__icontains=q_alt))
        mots_cond = Q()
        for w in mots_bruts:
            w_alt = w.replace("’", "'") if "’" in w else w.replace("'", "’")
            mots_cond |= Q(ordonnance_text__icontains=w) | Q(ordonnance_text__icontains=w_alt)
        combined = phrase_cond | mots_cond
        qs = Ordonnance.objects.filter(combined).order_by('-dateOrdonnance')

        norm_phrase_1 = norm_for_match(q_norm_apost)
        norm_phrase_2 = norm_for_match(q_alt) if q_alt != q_norm_apost else norm_phrase_1
        mots_norm = [norm_for_match(w) for w in mots_bruts]
        tmp = []
        for o in qs:
            txt = o.ordonnance_text or ""
            tnorm = norm_for_match(txt)
            phrase_count = count_non_overlapping(tnorm, norm_phrase_1)
            if norm_phrase_2 != norm_phrase_1:
                phrase_count = max(phrase_count, count_non_overlapping(tnorm, norm_phrase_2))
            words_count = sum(count_non_overlapping(tnorm, w) for w in mots_norm)
            score = phrase_count * 10 + words_count
            if phrase_count > 0 or words_count > 0:
                o.occurences = score
                tmp.append(o)
        tmp.sort(key=lambda x: (getattr(x, 'occurences', 0), x.dateOrdonnance or datetime.date.min), reverse=True)
        resultats = tmp
        total_resultats = len(resultats)

    return render(request, 'ordonnance/recherche_ordonnance.html', {
        'query': query,
        'resultats': resultats,
        'total_resultats': total_resultats
    })

# ----------------------------------------------------
# DÉTAIL ORDONNANCE
# ----------------------------------------------------
def detail_ordonnance(request, id):
    ordonnance = get_object_or_404(Ordonnance, idOrdonnance=id)
    return render(request, 'ordonnance/detail.html', {'ordonnance': ordonnance})

# ----------------------------------------------------
# GESTION DES FICHIERS INTROUVABLES
# ----------------------------------------------------
def fichier_introuvable_ordonnance(request, path):
    return render(request, "ordonnance/errors/fichier_introuvable.html", {"path": path})

# ----------------------------------------------------
# VISUALISER PDF ORDONNANCE
# ----------------------------------------------------
@login_required
def voir_pdf_ordonnance(request, id):
    ordonnance = get_object_or_404(Ordonnance, idOrdonnance=id)
    if not ordonnance.fichier or not os.path.exists(ordonnance.fichier.path):
        return render(request, "ordonnance/errors/fichier_introuvable.html", {
            "path": ordonnance.fichier.name if ordonnance.fichier else "Fichier manquant"
        })
    return FileResponse(open(ordonnance.fichier.path, 'rb'), content_type='application/pdf')

# ----------------------------------------------------
# SÉLECTION ET EXPORT ZIP
# ----------------------------------------------------
@login_required
def traiter_selection_ordonnance(request):
    if request.method == "POST":
        ids = request.POST.getlist("ordonnances_selectionnes")
        if not ids:
            messages.warning(request, "Aucune ordonnance sélectionnée.")
            return redirect("recherche_ordonnance")

        ordonnances = Ordonnance.objects.filter(idOrdonnance__in=ids)
        user_folder = os.path.join(settings.MEDIA_ROOT, f"selection_utilisateur_{request.user.id}")
        if os.path.exists(user_folder):
            shutil.rmtree(user_folder)
        os.makedirs(user_folder, exist_ok=True)

        fichiers_copier = []
        for o in ordonnances:
            if o.fichier and os.path.exists(o.fichier.path):
                dest_file = os.path.join(user_folder, f"{slugify(o.idOrdonnance)}_{os.path.basename(o.fichier.name)}")
                shutil.copy(o.fichier.path, dest_file)
                fichiers_copier.append(dest_file)

        if not fichiers_copier:
            messages.warning(request, "Aucun fichier PDF disponible pour les ordonnances sélectionnées.")
            return redirect("recherche_ordonnance")

        zip_filename = os.path.join(settings.MEDIA_ROOT, f"selection_utilisateur_{request.user.id}.zip")
        with zipfile.ZipFile(zip_filename, 'w') as zipf:
            for file_path in fichiers_copier:
                zipf.write(file_path, arcname=os.path.basename(file_path))

        with open(zip_filename, 'rb') as f:
            response = HttpResponse(f.read(), content_type='application/zip')
            response['Content-Disposition'] = 'attachment; filename="selection_ordonnances.zip"'
            return response

# ----------------------------------------------------
# HELPERS RECHERCHE
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
