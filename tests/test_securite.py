import pytest
from main import Episode


def test_etancheite_textuelle_enf07():
    """
    Vérification de l'exigence ENF-07 et de l'invariant INV-04 :
    Aucun champ textuel brut ne doit survivre à la normalisation.
    """
    texte_secret_compromettant = "TEXTE_BRUT_SENSIBLE_QUI_NE_DOIT_PAS_FUITER_12345"

    # 1. On simule un journal brut entrant contenant un texte illicite
    journal_brut_piege = {
        "id": "episode_sec_001",
        "agent_id": "agent_test",
        "scenario": "injection_prompt",
        "ts_start": 1700000000.0,
        "ts_end": 1700000010.0,
        "label": "benign",
        "attack_family": None,
        "events": [
            {
                "seq": 1,
                "ts": 1700000001.0,
                "type": "user_msg",
                # Le piège : un champ non autorisé contenant du texte
                "contenu_brut": texte_secret_compromettant,
                "tool_id": None,
                "args_hash": "hash_factice",
                "mem_ids": [],
                "scores": [],
                "latency_ms": 15.0
            }
        ]
    }

    # 2. On passe le dictionnaire brut dans la classe de normalisation
    episode_valide = Episode(**journal_brut_piege)

    # 3. On extrait les données telles qu'elles seront envoyées à l'extracteur ML
    donnees_nettoyees = episode_valide.model_dump()
    sortie_chaine = str(donnees_nettoyees)

    # 4. ASSERTION CRITIQUE
    assert texte_secret_compromettant not in sortie_chaine, (
        "ÉCHEC CRITIQUE (Exigence ENF-07) : Le texte brut a traversé la normalisation Pydantic !"
    )