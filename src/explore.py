import ijson
import re
import html
import json
import unicodedata
from collections import Counter

path = "data/raw/offres_2026-10-21.json"
motif_titre = (
    r"\b("
    r"data|donn[ée]es|big data|"
    r"bi|business intelligence|power bi|dataviz|"
    r"statisti\w*|analytics|"
    r"etl|data engineer|mlops|"
    r"machine learning|deep learning|ml|"
    r"ia|ai|intelligence artificielle|llm|nlp"
    r")\b"
)

nombre_total = 0
nombre_recruteurs = 0
nombre_vraies_offres = 0
nombre_titre_ok = 0
nombre_rome_ok = 0
nombre_prefiltre = 0
offres_propres = []
compteur_rome = Counter()
codes_data = ["M1405", "M1419", "M1423", "M1414", "M1811", "M1824", "M1851", "M1872", "M1868", "M1894", "M1889", "M1873"]


def nettoyer_html(texte):
    """Retire les balises HTML et les espaces en trop."""
    if not texte:
        return ""
    texte = re.sub(r"<[^>]+>", " ", texte)
    texte = html.unescape(texte)
    texte = re.sub(r"\s+", " ", texte).strip()
    return texte

def transformer_offre(offre):
    """Transforme une offre brute en dictionnaire propre et plat."""
    return {
        "id": offre["identifier"]["id"],
        "source": offre["identifier"]["partner_label"],
        "titre": html.unescape(offre["offer"]["title"]),
        "url": offre["apply"]["url"],
        "description": nettoyer_html(offre["offer"]["description"]),
        "codes_rome": offre["offer"]["rome_codes"],
        "entreprise": offre["workplace"]["name"],
        "adresse": offre["workplace"]["location"]["address"],
        "type_contrat": offre["contract"]["type"],
        "date_publication": offre["offer"]["publication"]["creation"],
    }

def normaliser(texte):
    """Ramène un texte à une forme simple pour comparer sans se soucier de la forme."""
    texte = (texte or "").lower()
    texte = texte.replace("œ", "oe").replace("æ", "ae")
    texte = unicodedata.normalize("NFKD", texte)
    texte = "".join(c for c in texte if not unicodedata.combining(c))
    texte = re.sub(r"[^\w\s]", " ", texte)
    return re.sub(r"\s+", " ", texte).strip()


def empreinte(texte, taille=5):
    """Découpe un texte en morceaux de 5 mots qui se chevauchent."""
    mots = normaliser(texte).split()
    return {" ".join(mots[i:i + taille]) for i in range(len(mots) - taille + 1)}


def similarite(empreinte_a, empreinte_b):
    """Part de la plus petite description qu'on retrouve dans l'autre (entre 0 et 1)."""
    if not empreinte_a or not empreinte_b:
        return 0.0
    commun = len(empreinte_a & empreinte_b)
    return commun / min(len(empreinte_a), len(empreinte_b))


def est_doublon(offre_a, offre_b, seuil=0.8):
    """Deux offres sont des doublons si leurs descriptions se recouvrent à plus de 80 %."""
    if len(offre_a["_empreinte"]) >= 30 and len(offre_b["_empreinte"]) >= 30:
        return similarite(offre_a["_empreinte"], offre_b["_empreinte"]) >= seuil
    # Descriptions trop courtes pour comparer : on compare le titre et l'entreprise
    return (
        normaliser(offre_a["titre"]) == normaliser(offre_b["titre"])
        and normaliser(offre_a["entreprise"]) == normaliser(offre_b["entreprise"])
    )


def dedupliquer(offres):
    """Garde la première version de chaque offre et note où les doublons ont été publiés."""
    for offre in offres:
        offre["_empreinte"] = empreinte(offre["description"])

    uniques = []
    for offre in offres:
        original = next((u for u in uniques if est_doublon(offre, u)), None)
        if original is None:
            offre["doublons"] = []
            uniques.append(offre)
        else:
            original["doublons"].append({"source": offre["source"], "url": offre["url"]})

    for offre in offres:
        del offre["_empreinte"]
    return uniques


with open(path, "rb") as f:
    for offre in ijson.items(f, "item"):
        nombre_total += 1
        if offre["identifier"]["partner_label"] == "recruteurs_lba":
            nombre_recruteurs += 1
            continue
        nombre_vraies_offres += 1
        titre = html.unescape(offre["offer"]["title"])
        codes = offre["offer"]["rome_codes"]

        titre_ok = re.search(motif_titre, titre.lower()) is not None
        rome_ok = any(code in codes_data for code in codes)

        if titre_ok:
            nombre_titre_ok += 1
        if rome_ok:
            nombre_rome_ok += 1
        if titre_ok or rome_ok:
            nombre_prefiltre += 1
            compteur_rome.update(codes)
            offres_propres.append(transformer_offre(offre))

nombre_avant = len(offres_propres)
offres_propres = dedupliquer(offres_propres)

with open("data/processed/offres_data_2026-10-21.json", "w", encoding="utf-8") as f:
    json.dump(offres_propres, f, ensure_ascii=False, indent=2)

print("Total :", nombre_total)
print("Recruteurs :", nombre_recruteurs)
print("Vraies offres :", nombre_vraies_offres)
print("Offres data (titre) :", nombre_titre_ok)
print("Offres data (rome) :", nombre_rome_ok)
print("Offres prefiltre :", nombre_prefiltre)
print("Offres avant dédoublonnage :", nombre_avant)
print("Offres uniques :", len(offres_propres))
for offre in offres_propres:
    if offre["doublons"]:
        print(f"  {offre['titre']} ({offre['source']}) a {len(offre['doublons'])} doublon(s)")