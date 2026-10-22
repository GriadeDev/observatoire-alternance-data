import json

import anthropic
from dotenv import load_dotenv

load_dotenv()

MODELE = "claude-haiku-5-5"

PROMPT_SYSTEME = """Tu analyses des offres d'alternance pour un observatoire des métiers de la data et de l'IA en France.

Réponds uniquement avec un objet JSON valide, sans texte autour, sans balises markdown.

Format attendu :
{
  "est_poste_data": true ou false,
  "metier": une valeur parmi la liste ci-dessous,
  "technologies": liste de technologies,
  "type_contrat_reel": "alternance", "stage" ou "autre",
  "justification": une phrase courte
}

Règles pour "est_poste_data" :
- true si le cœur du poste consiste à manipuler, analyser, modéliser ou valoriser des données, ou à développer des solutions d'IA.
- false si la data n'est qu'un mot dans le titre ou le nom de l'entreprise (poste commercial, comptable, RH sans analyse de données...).

Valeurs possibles pour "metier" :
- "data_analyst" : analyse de données, reporting, KPI
- "bi" : conception de dashboards et de modèles décisionnels (Power BI, Tableau...)
- "data_engineer" : pipelines, ETL, bases de données, infrastructure data
- "data_scientist" : modèles statistiques ou de machine learning
- "ingenieur_ia" : développement de solutions d'IA (LLM, agents, RAG, vision...)
- "chef_projet_data_ia" : pilotage de projets data ou IA, peu de technique
- "autre" : si est_poste_data vaut false

Règles pour "technologies" :
- uniquement des outils, langages ou plateformes explicitement cités dans l'offre
- noms normalisés : "Power BI", "Python", "SQL", "Excel", "Tableau", "GCP", "Azure", "AWS", "dbt", "Spark", "Git", "Docker"...
- pas de compétences générales comme "analyse" ou "rigueur"
- liste vide si aucune technologie n'est citée

Cas particuliers :
- "type_contrat_reel" décrit le contrat proposé, même si le poste n'est pas un poste data.
- Si la description est vide ou trop courte, base-toi uniquement sur le titre et réponds quand même au format JSON, sans jamais écrire de phrase en dehors du JSON.
"""


def construire_message(offre):
    """Prépare le texte de l'offre à envoyer à Claude."""
    contrat = ", ".join(offre["type_contrat"])
    return (
        f"Titre : {offre['titre']}\n\n"
        f"Type de contrat annoncé : {contrat}\n\n"
        f"Description : {offre['description']}"
    )

client = anthropic.Anthropic()
def analyser_offre(offre):
    """Envoie à Claude l'offre et renvoie le dictionnaire obtenu"""
    reponse = client.messages.create(
        model=MODELE,
        max_tokens=4096,
        system=PROMPT_SYSTEME,
        messages=[{"role": "user", "content": construire_message(offre)}],
    )

    for bloc in reponse.content:
        if bloc.type == "text":
            try:
                return json.loads(bloc.text)
            except json.JSONDecodeError:
                print("Réponse non JSON :", bloc.text, reponse.stop_reason)
                return None

            
FICHIER_OFFRES = "data/processed/offres_data_2026-10-21.json"
FICHIER_SORTIE = "data/processed/offres_analysees_2026-10-21.json"

if __name__ == "__main__":
    with open(FICHIER_OFFRES, "r", encoding="utf-8") as f:
        offres = json.load(f)

    nombre_echecs = 0

    for i, offre in enumerate(offres, start=1):
        print(f"{i}/{len(offres)} {offre['titre']}")
        resultat = analyser_offre(offre)
        offre["analyse"] = resultat
        if resultat is None:
            nombre_echecs += 1

    with open(FICHIER_SORTIE, "w", encoding="utf-8") as f:
        json.dump(offres, f, ensure_ascii=False, indent=2)

    print("Analyses terminées")
    print("Échecs :", nombre_echecs)
    print("Fichier enregistré :", FICHIER_SORTIE)