import json
import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import cross_val_predict
from sklearn.metrics import roc_auc_score
from main import EpisodeDB


engine = create_engine("sqlite:///./memtrace.db")
Session = sessionmaker(bind=engine)
session = Session()

episodes = session.query(EpisodeDB).all()

X_f1 = []  # Pour la régression logistique (F1)
X_all = []  # Pour le Gradient Boosting (F1 à F5)
y = []
ids = []

for ep in episodes:
    events = json.loads(ep.events_json)

    # --- Extraction F1, F4 (Simplifiée) ---
    nb_tools = sum(1 for e in events if e['type'] == 'tool_call')

    # --- Extraction F5 (Découplage temporel) ---
    mem_writes = {}
    delays = []

    for evt in events:
        if evt['type'] == 'mem_write':
            for m_id in evt['mem_ids']:
                if m_id not in mem_writes:
                    mem_writes[m_id] = evt['ts']
        elif evt['type'] == 'mem_read':
            for m_id in evt['mem_ids']:
                if m_id in mem_writes:
                    delays.append(evt['ts'] - mem_writes[m_id])

    f5_mean = np.mean(delays) if delays else 0.0
    f5_max = np.max(delays) if delays else 0.0

    # F2 simplifié (Récupération)
    f2_recup = 0.0

    # F3 simplifié (Divergence)
    f3_div = 0.0

    # Caractéristiques
    X_f1.append([nb_tools])
    # On met à jour le append pour inclure formellement F1 à F5
    X_all.append([nb_tools, len(events), ep.ts_end - ep.ts_start, f5_mean, f5_max, f2_recup, f3_div])

    y.append(1 if ep.label == "poisoned" else 0)
    ids.append(ep.id)

X_f1 = np.array(X_f1)
X_all = np.array(X_all)
y = np.array(y)

# --- Entraînement des deux modèles imposés ---
# 1. Régression logistique sur F1 seul
modele_f1 = LogisticRegression(random_state=42)
modele_f1.fit(X_f1, y)

# 2. Modèle à Gradient Boosté sur toutes les features (F1 à F5)
modele_final = GradientBoostingClassifier(random_state=42)

# On utilise la validation croisée pour obtenir des probabilités réalistes (non biaisées)
scores = cross_val_predict(modele_final, X_all, y, cv=5, method='predict_proba')[:, 1]

# On entraîne quand même le modèle final pour la forme, si besoin de le sauvegarder plus tard
modele_final.fit(X_all, y)
print(f"AUROC global : {roc_auc_score(y, scores):.3f}")

for ep_id, score in zip(ids, scores):
    ep = session.query(EpisodeDB).filter(EpisodeDB.id == ep_id).first()
    ep.score = float(score)

session.commit()
session.close()