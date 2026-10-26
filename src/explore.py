import glob
import html
import json
import os
import re
import unicodedata

import ijson

DOSSIER_RAW = "data/raw"
FICHIER_SORTIE = "data/processed/offres_data.json"

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

codes_data = ["M1405", "M1419", "M1423", "M1414", "M1811", "M1824",
              "M1851", "M1872", "M1868", "M1894", "M1889", "M1873"]


def nettoyer_html(texte):
    """Retire les balises HTML et les espaces en trop."""
    if not texte:
        return ""
    texte = re.sub(r"<[^>]+>", " ", texte)
    texte = html.unescape(texte)
    return re.sub(r"\s+", " ", texte).strip()


def transformer_offre(offre, date_collecte):
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
        "date_collecte": date_collecte,
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
    return len(empreinte_a & empreinte_b) / min(len(empreinte_a), len(empreinte_b))


def est_doublon(offre_a, offre_b, seuil=0.8):
    """Deux offres sont des doublons si même id, ou si leurs descriptions se recouvrent à plus de 80 %."""
    if offre_a["id"] == offre_b["id"]:
        return True
    if len(offre_a["_empreinte"]) >= 30 and len(offre_b["_empreinte"]) >= 30:
        return similarite(offre_a["_empreinte"], offre_b["_empreinte"]) >= seuil
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
            ids_connus = {original["id"]} | {d["id"] for d in original["doublons"]}
            if offre["id"] not in ids_connus:
                original["doublons"].append(
                    {"id": offre["id"], "source": offre["source"], "url": offre["url"]}
                )

    for offre in offres:
        del offre["_empreinte"]
    return uniques


def traiter_fichier(chemin):
    """Lit un export brut et renvoie ses offres data pré-filtrées."""
    date_collecte = re.search(r"\d{4}-\d{2}-\d{2}", chemin).group()
    nombre_vraies_offres = 0
    offres_filtrees = []

    try:
        with open(chemin, "rb") as f:
            for offre in ijson.items(f, "item"):
                if offre["identifier"]["partner_label"] == "recruteurs_lba":
                    continue
                nombre_vraies_offres += 1
                titre = html.unescape(offre["offer"]["title"])
                titre_ok = re.search(motif_titre, titre.lower()) is not None
                rome_ok = any(code in codes_data for code in offre["offer"]["rome_codes"])
                if titre_ok or rome_ok:
                    offres_filtrees.append(transformer_offre(offre, date_collecte))
    except ijson.common.IncompleteJSONError:
        print(f"ATTENTION : {chemin} est incomplet, il est ignoré.")
        return []

    print(f"{date_collecte} : {nombre_vraies_offres} vraies offres, {len(offres_filtrees)} pré-filtrées")
    return offres_filtrees


if __name__ == "__main__":
    fichiers = sorted(glob.glob(os.path.join(DOSSIER_RAW, "offres_*.json")))

    toutes_les_offres = []
    for chemin in fichiers:
        toutes_les_offres.extend(traiter_fichier(chemin))

    offres_uniques = dedupliquer(toutes_les_offres)

    with open(FICHIER_SORTIE, "w", encoding="utf-8") as f:
        json.dump(offres_uniques, f, ensure_ascii=False, indent=2)

    print(f"\nOffres pré-filtrées, tous exports confondus : {len(toutes_les_offres)}")
    print(f"Offres uniques après dédoublonnage : {len(offres_uniques)}")
    for offre in offres_uniques:
        if offre["doublons"]:
            print(f"  {offre['titre']} ({offre['source']}) a {len(offre['doublons'])} doublon(s)")
    print("Doublons détectés :", sum(len(o["doublons"]) for o in offres_uniques))