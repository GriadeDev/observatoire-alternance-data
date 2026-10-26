import json
from collections import Counter, defaultdict

FICHIER_ANALYSE = "data/processed/offres_analysees_2026-10-21.json"

ALIAS_TECHNOLOGIES = {
    "GitHub": "Git",
    "Azure OpenAI": "OpenAI",
    "Django REST Framework": "Django",
    "S3": "AWS",
    "PowerPoint": "Pack Office",
    "Microsoft 365": "Pack Office",
    "Microsoft Teams": "Pack Office",
    "SharePoint": "Pack Office",
}

FUSION_METIERS = {
    "data_analyst": "data_analyst_bi",
    "bi": "data_analyst_bi",
}

SEUIL_OFFRES_METIER = 5   
SEUIL_MENTIONS = 2      


def harmoniser(technologies):
    """Remplace chaque technologie par son nom de référence et supprime les doublons."""
    return {ALIAS_TECHNOLOGIES.get(t, t) for t in technologies}


def top_filtre(compteur, limite):
    """Renvoie les technologies les plus citées, en ignorant celles sous le seuil de mentions."""
    return [(t, n) for t, n in compteur.most_common() if n >= SEUIL_MENTIONS][:limite]


if __name__ == "__main__":
    with open(FICHIER_ANALYSE, "r", encoding="utf-8") as f:
        offres = json.load(f)

    offres_data = []
    for offre in offres:
        if (
            offre["analyse"] is not None
            and offre["analyse"]["est_poste_data"]
            and offre["analyse"]["type_contrat_reel"] == "alternance"
        ):
            offres_data.append(offre)

    compteur_metiers = Counter()
    compteur_technologies = Counter()
    technos_par_metier = defaultdict(Counter)

    for offre in offres_data:
        metier_brut = offre["analyse"]["metier"]
        metier = FUSION_METIERS.get(metier_brut, metier_brut)
        technologies = harmoniser(offre["analyse"]["technologies"])
        compteur_metiers[metier] += 1
        compteur_technologies.update(technologies)
        technos_par_metier[metier].update(technologies)

    total = len(offres_data)
    print(f"Alternances data analysées : {total}")

    print("\n--- Métiers ---")
    for metier, nombre in compteur_metiers.most_common():
        pourcentage = nombre / total * 100
        print(f"{metier} : {nombre} offres ({pourcentage:.0f} %)")

    print(f"\n--- Top 15 des technologies (citées au moins {SEUIL_MENTIONS} fois) ---")
    for technologie, nombre in top_filtre(compteur_technologies, 15):
        pourcentage = nombre / total * 100
        print(f"{technologie} : {nombre} offres ({pourcentage:.0f} %)")

    print("\n--- Top 5 des technologies par métier ---")
    for metier, nombre_offres in compteur_metiers.most_common():
        print(f"\n{metier} ({nombre_offres} offres)")

        if nombre_offres < SEUIL_OFFRES_METIER:
            print("  Échantillon trop faible pour en tirer des conclusions")
            continue

        top = top_filtre(technos_par_metier[metier], 5)
        if not top:
            print(f"  Aucune technologie citée au moins {SEUIL_MENTIONS} fois")
            continue

        for technologie, nombre in top:
            pourcentage = nombre / nombre_offres * 100
            print(f"  {technologie} : {nombre} offres ({pourcentage:.0f} %)")

    print("\n--- Toutes les technologies (ordre alphabétique) ---")
    for technologie in sorted(compteur_technologies):
        print(technologie)