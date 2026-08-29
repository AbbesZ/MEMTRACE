import pytest


def test_pipeline_ml_execution():
    """
    Exécute le pipeline ML pour vérifier que l'extraction des descripteurs F1-F5
    et l'entraînement scikit-learn se déroulent sans erreur.
    """
    # En important le script, Python va l'exécuter de bout en bout
    import analyse_ml

    assert True