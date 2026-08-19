import json
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import EpisodeDB


def extraire_features(events, ts_start, ts_end):
    nb_events = len(events)
    duree_totale = ts_end - ts_start
    nb_tools = sum(1 for e in events if e.get('type') == 'tool_call')
    nb_mem_writes = sum(1 for e in events if e.get('type') == 'mem_write')
    nb_mem_reads = sum(1 for e in events if e.get('type') == 'mem_read')
    total_scores = sum(sum(e.get('scores', [])) for e in events)
    latency_moy = float(np.mean([e.get('latency_ms', 0.0) for e in events])) if events else 0.0
    return [nb_events, duree_totale, nb_tools, nb_mem_writes, nb_mem_reads, total_scores, latency_moy]


def train_and_score_model():
    engine = create_engine("sqlite:///./memtrace.db")
    Session = sessionmaker(bind=engine)
    session = Session()

    episodes = session.query(EpisodeDB).all()
    if not episodes:
        raise ValueError("Aucun épisode trouvé pour entraîner le modèle.")

    X = []
    y = []
    ids = []

    for ep in episodes:
        events = json.loads(ep.events_json)
        X.append(extraire_features(events, ep.ts_start, ep.ts_end))
        y.append(1 if ep.label == "poisoned" else 0)
        ids.append(ep.id)

    X = np.array(X, dtype=float)
    y = np.array(y, dtype=int)

    X_train, X_test, y_train, y_test, ids_train, ids_test = train_test_split(
        X, y, ids, test_size=0.2, random_state=42, stratify=y
    )

    modele = LogisticRegression(random_state=42, max_iter=1000)
    modele.fit(X_train, y_train)

    scores_test = modele.predict_proba(X_test)[:, 1]
    auroc = roc_auc_score(y_test, scores_test)
    scores_all = modele.predict_proba(X)[:, 1]

    for ep_id, score in zip(ids, scores_all):
        ep = session.query(EpisodeDB).filter(EpisodeDB.id == ep_id).first()
        ep.score = float(score)

    session.commit()
    session.close()

    return {
        "nombre_episodes": len(ids),
        "nombre_train": len(X_train),
        "nombre_test": len(X_test),
        "auroc": float(auroc),
        "score_min": float(np.min(scores_all)),
        "score_max": float(np.max(scores_all))
    }


if __name__ == "__main__":
    print("Chargement des données depuis SQLite...")
    result = train_and_score_model()
    print("Modèle entraîné avec succès !")
    print(result)
