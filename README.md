# MEMTRACE - Console Forensique 🔍

Ce projet a été réalisé dans le cadre de mon stage de 4ème année d'ingénierie en informatique à CY Tech, au sein de l'Unité Mixte de Recherche (UMR) au Maroc. 

Il s'agit d'une application de détection forensique *post-hoc* (en boîte noire) ciblant les attaques d'empoisonnement de mémoire et de contexte sur les agents IA, une vulnérabilité critique répertoriée sous la référence **OWASP ASI06**.

## 🛠️ Technologies Utilisées
* **Backend API :** Python 3.12, FastAPI, Pydantic
* **Machine Learning :** Scikit-Learn, Numpy (Régression Logistique)
* **Base de données :** SQLite, SQLAlchemy
* **Interface Web :** HTML/CSS, HTMX, Jinja2
* **Déploiement :** Docker, Docker Compose

## 🚀 Démarrage Rapide (Déploiement Conteneurisé)

Ce projet a été conçu pour être déployé en une commande unique sur une machine vierge, conformément aux exigences de reproductibilité scientifique.

**Prérequis :** Avoir [Docker Desktop](https://www.docker.com/products/docker-desktop/) installé et en cours d'exécution sur votre machine.

1. Clonez ce dépôt sur votre machine locale :
   ```bash
   git clone https://github.com/AbbesZ/MEMTRACE.git
   cd MEMTRACE
2. Lancez la construction et l'exécution du conteneur :
    ```bash
    docker compose up --build
   
3. Accédez à la console d'investigation depuis votre navigateur : http://127.0.0.1:8000/ui

(Pour arrêter le serveur, effectuez simplement Ctrl+C dans le terminal).

## 📂 Architecture du Projet

- main.py : Cœur de l'application. Contient l'API FastAPI pour l'ingestion des traces JSONL, la vérification stricte des invariants d'horodatage, et les routes web.


- analyse_ml.py : Script d'extraction des descripteurs et d'entraînement du modèle de Machine Learning permettant d'attribuer un score de suspicion (métrique AUROC).


- generateur_traces.py : Outil de génération du corpus synthétique (AgentTraceBench-v0.jsonl) simulant des historiques d'agents IA sains et empoisonnés.


- templates/index.html : Interface utilisateur allégée utilisant HTMX pour l'affichage du tableau de bord.


- memtrace.db : Base de données SQLite stockant les épisodes ingérés et scorés (générée automatiquement à l'exécution).


- Dockerfile & docker-compose.yml : Configuration de l'environnement isolé.