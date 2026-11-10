"""Alertes d'offres d'emploi en développement pour la région de Québec.

Vérifie les nouvelles offres et envoie une notification sur le téléphone (ntfy)
pour chaque offre qui correspond au profil. Les offres déjà vues sont gardées
dans seen.json pour ne jamais être envoyées deux fois.

Variables d'environnement :
  NTFY_TOPIC        sujet ntfy secret (obligatoire, sauf en mode --dry-run)
  ADZUNA_APP_ID     facultatif : active la source Adzuna
  ADZUNA_APP_KEY    facultatif : active la source Adzuna

Usage :
  python job_alerts.py            # vérifie et envoie les notifications
  python job_alerts.py --dry-run  # affiche les offres trouvées sans rien envoyer
"""
import json
import os
import re
import sys
import unicodedata
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

SEEN_FILE = Path(__file__).with_name("seen.json")
MAX_SEEN = 5000  # on oublie les plus vieilles offres au-delà de ce nombre

# --- Profil ------------------------------------------------------------------

# Le titre doit contenir au moins un de ces mots pour être retenu.
TITLE_KEYWORDS = [
    "developpeu", "developer", "programmeu", "programmer", "full stack", "full-stack",
    "fullstack", "back-end", "backend", "front-end", "frontend", "logiciel", "software",
    "web", ".net", "c#", "java", "react", "angular", "applications", "analyste-programmeu",
    "integrateu", "devops", "application",
]
# Titres exclus même s'ils contiennent un mot ci-dessus.
TITLE_EXCLUDE = [
    "designer graphique", "technicien reseau", "network", "lan ", "cuisinier",
]
# Hors région (« plus loin si vraiment pertinent ») : l'offre doit être un vrai
# poste de développement (titre) ou mentionner une technologie de ton profil.
CORE_DEV_TITLES = [
    "developpeu", "developer", "programmeu", "programmer", "full stack", "full-stack",
    "fullstack", "back-end", "backend", "front-end", "frontend", "logiciel", "software",
]
STRONG_MATCH = [
    "full stack", "full-stack", "fullstack", ".net", "c#", "asp.net", "java", "spring",
    "react", "angular", "laravel", "php", "kotlin", "python", "fastapi", "azure",
    "junior", "debutant", "entry level", "stagiaire", "intermediaire",
]
REMOTE_WORDS = ["teletravail", "remote", "a distance", "hybride", "hybrid"]

# Municipalités à environ 1 h de route de Québec (sans accents, en minuscules).
LOCAL_PLACES = [
    "quebec", "levis", "saint-augustin", "st-augustin", "ancienne-lorette", "wendake",
    "stoneham", "lac-beauport", "sainte-brigitte-de-laval", "boischatel", "chateau-richer",
    "beaupre", "ile d'orleans", "saint-lambert-de-lauzon", "saint-henri", "beaumont",
    "montmagny", "saint-raymond", "donnacona", "pont-rouge", "portneuf", "neuville",
    "shannon", "sainte-catherine-de-la-jacques-cartier", "val-belair", "charlesbourg",
    "beauport", "sainte-foy", "sillery", "cap-rouge", "loretteville", "sainte-marie",
    "saint-apollinaire", "saint-agapit", "lotbiniere", "sainte-claire",
    "saint-anselme", "vallee-jonction", "beauceville", "saint-georges", "thetford",
    "saint-nicolas", "charny", "pintendre", "breakeyville", "saint-jean-chrysostome",
]

# Codes CNP 2021 du Guichet-Emplois : informatique et développement.
JOBBANK_NOC = ["21211", "21230", "21231", "21232", "21233", "21234", "22222"]


def norm(text):
    """Minuscules, sans accents, espaces simples."""
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", text).lower()


def has_any(text, words):
    return any(w in text for w in words)


def classify(job):
    """Retourne 'local', 'teletravail', 'loin' ou None si l'offre ne convient pas."""
    title = norm(job["title"])
    if not has_any(title, TITLE_KEYWORDS) or has_any(title, TITLE_EXCLUDE):
        return None
    location = norm(job["location"])
    # « Montréal, Québec » : seule la ville (avant la virgule) compte pour la région.
    city = location.split(",")[0]
    full = f"{title} {norm(job.get('description', ''))}"
    if has_any(city, LOCAL_PLACES):
        return "local"
    if has_any(full, REMOTE_WORDS):
        return "teletravail"
    in_quebec = "(qc)" in location or "quebec" in location
    if in_quebec and (has_any(title, CORE_DEV_TITLES) or has_any(full, STRONG_MATCH)):
        return "loin"
    return None


# --- Sources -----------------------------------------------------------------

def fetch(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "alertes-emploi/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def jobbank():
    """Flux Atom public du Guichet-Emplois, trié par date."""
    params = [("fn21", c) for c in JOBBANK_NOC] + [("sort", "D"), ("rows", "100")]
    url = "https://www.jobbank.gc.ca/jobsearch/feed/jobSearchRSSfeed?" + urllib.parse.urlencode(params)
    ns = {"a": "http://www.w3.org/2005/Atom"}
    root = ET.fromstring(fetch(url))
    for entry in root.findall("a:entry", ns):
        summary = entry.findtext("a:summary", "", ns)
        field = lambda name: (re.search(name + r":</strong>\s*([^<]+)", summary) or [None, ""])[1].strip()
        yield {
            "id": "jobbank:" + entry.findtext("a:id", "", ns),
            "title": entry.findtext("a:title", "", ns).strip(),
            "company": field("Employer"),
            "location": field("Location"),
            "url": entry.find("a:link", ns).get("href"),
            "description": summary,
        }


def adzuna():
    """API Adzuna (facultative) : offres des derniers jours au Québec."""
    app_id, app_key = os.environ.get("ADZUNA_APP_ID"), os.environ.get("ADZUNA_APP_KEY")
    if not (app_id and app_key):
        return
    params = {
        "app_id": app_id, "app_key": app_key, "results_per_page": 50,
        "what_or": "développeur developpeur programmeur developer full-stack .net java react",
        "where": "Québec", "max_days_old": 3, "sort_by": "date",
        "content-type": "application/json",
    }
    url = "https://api.adzuna.com/v1/api/jobs/ca/search/1?" + urllib.parse.urlencode(params)
    for r in json.loads(fetch(url)).get("results", []):
        yield {
            "id": f"adzuna:{r['id']}",
            "title": r.get("title", ""),
            "company": r.get("company", {}).get("display_name", ""),
            "location": r.get("location", {}).get("display_name", ""),
            "url": r.get("redirect_url", ""),
            "description": r.get("description", ""),
        }


SOURCES = [("Guichet-Emplois", jobbank), ("Adzuna", adzuna)]


# --- Notifications -----------------------------------------------------------

LABELS = {
    "local": ("📍 Région de Québec", 4, "round_pushpin"),
    "teletravail": ("🏠 Télétravail", 4, "house"),
    "loin": ("🚗 Ailleurs au Québec", 3, "car"),
}


def notify(topic, job, kind):
    label, priority, tag = LABELS[kind]
    body = {
        "topic": topic,
        "title": job["title"][:120],
        "message": f"{job['company'] or 'Employeur non précisé'} · {job['location']}\n{label} · {job['source']}",
        "click": job["url"],
        "priority": priority,
        "tags": [tag],
        "actions": [{"action": "view", "label": "Voir l’offre", "url": job["url"]}],
    }
    req = urllib.request.Request(
        "https://ntfy.sh/", data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    urllib.request.urlopen(req, timeout=30).read()


def main():
    dry_run = "--dry-run" in sys.argv
    topic = os.environ.get("NTFY_TOPIC")
    if not dry_run and not topic:
        sys.exit("NTFY_TOPIC manquant.")

    first_run = not SEEN_FILE.exists()
    seen = json.loads(SEEN_FILE.read_text("utf-8")) if not first_run else []
    seen_set = set(seen)

    matches, errors = [], []
    for name, source in SOURCES:
        try:
            for job in source():
                if job["id"] in seen_set:
                    continue
                seen.append(job["id"])
                seen_set.add(job["id"])
                kind = classify(job)
                if kind:
                    matches.append((dict(job, source=name), kind))
        except Exception as exc:  # une source en panne ne bloque pas les autres
            errors.append(f"{name} : {exc}")

    for e in errors:
        print("Erreur", e, file=sys.stderr)

    if dry_run:
        for job, kind in matches:
            print(f"[{kind}] {job['title']} | {job['company']} | {job['location']} | {job['url']}")
        print(f"{len(matches)} offre(s) correspondante(s).")
        return

    if first_run:
        # Premier lancement : on mémorise les offres existantes sans inonder le téléphone.
        notify(topic, {
            "title": "Alertes emploi activées ✅", "company": f"{len(matches)} offre(s) déjà en ligne mémorisée(s)",
            "location": "tu seras avertie des prochaines", "url": "https://www.jobbank.gc.ca", "source": "configuration",
        }, "local")
    else:
        for job, kind in matches:
            notify(topic, job, kind)
        print(f"{len(matches)} notification(s) envoyée(s).")

    SEEN_FILE.write_text(json.dumps(seen[-MAX_SEEN:], ensure_ascii=False, indent=0), "utf-8")


if __name__ == "__main__":
    main()
