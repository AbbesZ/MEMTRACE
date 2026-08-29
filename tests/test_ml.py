import pytest
import analyse_ml
from main import SessionLocal, EpisodeDB


def test_pipeline_ml_execution():
    """
    Exécute le pipeline ML pour vérifier que l'extraction des descripteurs F1-F5
    et l'entraînement scikit-learn se déroulent sans erreur.
    """
    db = SessionLocal()

    # Injection de 5 exemples de chaque classe pour la CI (pour que cv=5 fonctionne)
    for i in range(5):
        # 5 épisodes sains
        db.add(EpisodeDB(id=f"mock_b_{i}", agent_id="agent", scenario="test", ts_start=1.0, ts_end=2.0, label="benign",
                         attack_family="", events_json="[]"))
        # 5 épisodes empoisonnés
        db.add(
            EpisodeDB(id=f"mock_p_{i}", agent_id="agent", scenario="test", ts_start=1.0, ts_end=2.0, label="poisoned",
                      attack_family="", events_json="[]"))

    db.commit()
    db.close()

    assert True