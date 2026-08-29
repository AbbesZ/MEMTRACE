import pytest
import runpy
from main import SessionLocal, EpisodeDB


def test_pipeline_ml_execution():
    """
    Vérifie que le pipeline ML s'exécute sans erreur avec couverture totale.
    """
    db = SessionLocal()

    # 1. On vide la base pour partir sur un environnement propre
    db.query(EpisodeDB).delete()

    # 2. On injecte 5 exemples de chaque classe (requis pour cv=5)
    for i in range(5):
        db.add(EpisodeDB(id=f"mock_b_{i}", agent_id="a", scenario="s", ts_start=1.0, ts_end=2.0, label="benign",
                         attack_family="", events_json="[]"))
        db.add(EpisodeDB(id=f"mock_p_{i}", agent_id="a", scenario="s", ts_start=1.0, ts_end=2.0, label="poisoned",
                         attack_family="", events_json="[]"))

    db.commit()
    db.close()

    # 3. Exécute le script ML dans le même processus (pytest-cov va tout voir !)
    runpy.run_path("analyse_ml.py")

    assert True