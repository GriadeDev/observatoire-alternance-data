import os
from datetime import datetime

import requests
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv("LBA_API_TOKEN")

BASE_URL = "https://api.apprentissage.beta.gouv.fr/api"
EXPORT_URL = f"{BASE_URL}/job/v1/export"


def get_export_info():
    """Appelle la route d'export avec la clé et renvoie le JSON (url + lastUpdate)."""
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    response = requests.get(EXPORT_URL, headers=headers)
    response.raise_for_status()
    return response.json()


def download_export(url):
    """Télécharge le fichier d'offres depuis l'url et l'enregistre dans data/raw. Renvoie le chemin du fichier."""
    filename = f"data/raw/offres_{datetime.now().strftime('%Y-%m-%d')}.json"
    response = requests.get(url, stream=True)
    response.raise_for_status()
    with open(filename, "wb") as f:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            f.write(chunk)
    return filename


if __name__ == "__main__":
    info = get_export_info()
    print("Dernière mise à jour :", info["lastUpdate"])
    path = download_export(info["url"])
    print("Fichier enregistré :", path)