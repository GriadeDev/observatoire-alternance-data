import ijson
import re
import html
from collections import Counter

path = "data/raw/offres_2026-10-21.json"
motif_titre = r"\b(data|power bi|machine learning|intelligence artificielle|analytics)\b"

nombre_total = 0
nombre_recruteurs = 0
nombre_vraies_offres = 0
nombre_titre_ok = 0
nombre_rome_ok = 0
nombre_prefiltre = 0
compteur_rome = Counter()
codes_data = ["M1405", "M1419", "M1423", "M1414", "M1811", "M1824", "M1851", "M1872", "M1868", "M1894", "M1889", "M1873"]
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

print("Total :", nombre_total)
print("Recruteurs :", nombre_recruteurs)
print("Vraies offres :", nombre_vraies_offres)
print("Offres data (titre) :", nombre_titre_ok)
print("Offres prefiltre :", nombre_prefiltre)
print("Offres data (rome) :", nombre_rome_ok)
print(compteur_rome.most_common(15))