# MEMTRACE - Console Forensique 🔍

[![CI MEMTRACE](https://github.com/AbbesZ/MEMTRACE/actions/workflows/ci.yml/badge.svg)](https://github.com/AbbesZ/MEMTRACE/actions/workflows/ci.yml)


MEMTRACE est un prototype de détection forensique post-hoc, en boîte noire, de traces d'agents IA. Il vise l'étude de l'empoisonnement de mémoire et de contexte associé à la catégorie OWASP ASI06.

Le projet sépare volontairement deux actifs :

- un corpus JSONL synthétique, versionné et régénérable ;
- une console web qui valide, stocke, score et consulte les épisodes.

Le prototype n'agit pas sur l'agent observé et ne réalise ni blocage en ligne ni filtrage temps réel.

## Fonctionnement

```text
générateur de traces -> corpus JSONL -> POST /ingest -> validation Pydantic
                                                                    -> SQLite
                                                                    -> scoring scikit-learn
                                                                    -> console /ui et détail d'épisode
```

Chaque épisode contient des événements normalisés. Les champs de contenu textuel brut ne font pas partie du schéma ; les arguments d'outils sont représentés par une empreinte (`args_hash`). Les invariants contrôlés à l'ingestion sont notamment :

- `seq` strictement croissant ;
- horodatages monotones ;
- `ts_end >= ts_start` ;
- événements compris dans l'intervalle de l'épisode.

## Technologies

- Python 3.12
- FastAPI, Pydantic et Uvicorn
- SQLAlchemy avec SQLite en développement
- NumPy et scikit-learn (`LogisticRegression`)
- Jinja2 et HTML/CSS pour l'interface
- Pytest, Flake8, Docker et GitHub Actions

## Démarrage avec Docker

Prérequis : Docker Desktop installé et démarré.

```bash
git clone https://github.com/AbbesZ/MEMTRACE.git
cd MEMTRACE
docker compose up --build
```

La console est ensuite disponible à l'adresse [http://127.0.0.1:8000/ui](http://127.0.0.1:8000/ui). L'API interactive FastAPI est disponible à [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

Pour arrêter le service :

```text
Ctrl+C
```

## Installation locale

Avec Python 3.12 :

```powershell
py -m venv .venv
.venv\Scripts\activate
py -m pip install -r requirements.txt
```

Sous Linux ou macOS, remplacer l'activation Windows par `source .venv/bin/activate` et utiliser `python` à la place de `py`.

## Démonstration complète

1. Générer ou régénérer le corpus synthétique :

    ```powershell
    py generateur_traces.py
    ```

2. Démarrer l'API :

    ```powershell
    py -m uvicorn main:app --reload
    ```

3. Dans un autre terminal, ingérer le corpus :

    ```powershell
    curl.exe -X POST -F "file=@AgentTraceBench-v0.jsonl" http://127.0.0.1:8000/ingest
    ```

    L'ingestion valide chaque ligne, ignore les doublons et lance le scoring si au moins un nouvel épisode est accepté.

4. Ouvrir la console à [http://127.0.0.1:8000/ui](http://127.0.0.1:8000/ui), puis cliquer sur l'identifiant d'un épisode pour consulter ses événements.

Le scoring peut aussi être relancé manuellement :

```powershell
py analyse_ml.py
```

ou via l'API :

```powershell
curl.exe -X POST http://127.0.0.1:8000/retrain
```

## API principale

| Méthode | Route | Fonction |
|---|---|---|
| `GET` | `/healthz` | Vérifie la disponibilité du service. |
| `POST` | `/ingest` | Ingère un fichier JSONL et retourne les acceptés/rejetés. |
| `GET` | `/episodes` | Retourne les épisodes présents en base. |
| `GET` | `/episodes/{episode_id}` | Affiche le détail HTML d'un épisode. |
| `POST` | `/retrain` | Recalcule les scores et retourne les métriques. |
| `GET` | `/ui` | Affiche la console de consultation. |

Le contrat OpenAPI est généré par FastAPI dans `/docs` et `/openapi.json`.

## Descripteurs actuels

Le module [analyse_ml.py](analyse_ml.py) calcule actuellement un vecteur stable comprenant :

- nombre d'événements ;
- durée de l'épisode ;
- nombre d'appels d'outils ;
- nombre d'écritures et de lectures mémoire ;
- somme des scores de récupération ;
- latence moyenne.

Le modèle est entraîné avec une graine fixe (`random_state=42`) et une séparation stratifiée entraînement/test. L'AUROC affichée est calculée sur le jeu de test, mais le modèle reste un démonstrateur : il n'est pas sérialisé dans un fichier de modèle et le protocole scientifique complet du cahier des charges n'est pas encore implémenté.

## Tests et CI

Tests locaux :

```powershell
py -m pytest tests/ -v
```

Contrôle Flake8 critique :

```powershell
py -m flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
```

La CI définie dans [.github/workflows/ci.yml](.github/workflows/ci.yml) installe Python 3.12, exécute les contrôles de style, lance les tests et construit l'image Docker.

## Architecture du dépôt

| Élément | Rôle |
|---|---|
| [main.py](main.py) | Modèles Pydantic/SQLAlchemy, validation, API et routes web. |
| [analyse_ml.py](analyse_ml.py) | Extraction des features, entraînement, AUROC et sauvegarde des scores. |
| [generateur_traces.py](generateur_traces.py) | Génération du corpus synthétique JSONL. |
| [templates/index.html](templates/index.html) | Tableau de la console. |
| [templates/episode_detail.html](templates/episode_detail.html) | Vue détaillée des événements d'un épisode. |
| [tests/test_securite.py](tests/test_securite.py) | Tests d'étanchéité textuelle, d'invariants et de route web. |
| [checklist_conformite.md](checklist_conformite.md) | État de conformité au cahier des charges. |
| [Dockerfile](Dockerfile) et [docker-compose.yml](docker-compose.yml) | Déploiement conteneurisé. |
| `memtrace.db` | Base SQLite générée à l'exécution, ignorée par Git. |

## Limites connues

MEMTRACE est un prototype de recherche. Le corpus actuel est synthétique et limité en scénarios et familles d'attaque. L'application ne fournit pas encore d'adaptateur LangGraph, de filtres avancés, de frise temporelle avec liens écriture/relecture, d'export CSV/JSON, de marquage analyste persistant ou de modèle sérialisé. Ces écarts sont suivis dans [checklist_conformite.md](checklist_conformite.md).

Les résultats ML doivent donc être interprétés comme une validation technique du pipeline, et non comme une mesure de performance opérationnelle sur des données de production.

## Sécurité et périmètre

Le projet doit être utilisé uniquement avec des agents auto-hébergés et des données synthétiques ou publiques autorisées. Il est conçu pour l'analyse post-hoc et ne doit pas être connecté à un système de production ou utilisé pour cibler un service tiers.