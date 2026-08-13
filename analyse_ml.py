import json
import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from main import EpisodeDB  # On importe notre structure de base de données

# --- 1. CONNEXION À LA BASE DE DONNÉES ---
engine = create_engine("sqlite:///./memtrace.db")
Session = sessionmaker(bind=engine)
session = Session()

print("Chargement des données depuis SQLite...")
episodes = session.query(EpisodeDB).all()

X = []
y = []
ids = []

# --- 2. EXTRACTION DES DESCRIPTEURS (Exigence EF-05) ---
for ep in episodes:
    events = json.loads(ep.events_json)

    # On extrait des descripteurs basiques pour notre preuve de concept :
    # F4 : Longueur de l'épisode (nombre d'événements)
    nb_events = len(events)
    # F5 simplifié : Durée totale de l'interaction
    duree_totale = ep.ts_end - ep.ts_start
    # F1 simplifié : Nombre d'appels d'outils
    nb_tools = sum(1 for e in events if e['type'] == 'tool_call')

    # Vecteur de caractéristiques (Features)
    feature_vector = [nb_events, duree_totale, nb_tools]
    X.append(feature_vector)

    # Cible (Target) : 1 si empoisonné, 0 si bénin
    y.append(1 if ep.label == "poisoned" else 0)
    ids.append(ep.id)

X = np.array(X)
y = np.array(y)

# --- 3. ENTRAÎNEMENT DU MODÈLE (Section 9.2) ---
print("Entraînement du modèle de Régression Logistique imposé...")
# Le paramètre random_state=42 garantit la reproductibilité absolue (ENF-04)
modele = LogisticRegression(random_state=42)
modele.fit(X, y)

# --- 4. CALCUL DES SCORES ET MÉTRIQUES (Section 9.3) ---
# On récupère la probabilité d'être empoisonné (colonne 1)
scores = modele.predict_proba(X)[:, 1]
auroc = roc_auc_score(y, scores)
print(f"Modèle entraîné avec succès ! Métrique AUROC obtenue : {auroc:.3f}")

# --- 5. SAUVEGARDE EN BASE DE DONNÉES (Exigence EF-06) ---
print("Sauvegarde des scores de suspicion dans la base de données...")
for ep_id, score in zip(ids, scores):
    ep = session.query(EpisodeDB).filter(EpisodeDB.id == ep_id).first()
    ep.score = float(score)

session.commit()
session.close()
print("Terminé ! Les données sont prêtes pour l'interface web.")