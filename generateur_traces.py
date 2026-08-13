import json
import time
import uuid
import random


def generer_episode(est_empoisonne=False):
    """Génère un épisode synthétique respectant le schéma canonique de l'UMR."""
    episode_id = str(uuid.uuid4())
    ts_start = time.time()

    events = []
    current_ts = ts_start

    # Génération de 3 événements basiques pour simuler une interaction
    for seq in range(1, 4):
        # Le temps avance pour garantir un horodatage monotone (INV-02)
        current_ts += random.uniform(0.1, 2.5)

        event = {
            "seq": seq,  # Strictement croissant (INV-01)
            "ts": current_ts,
            "type": "user_msg" if seq == 1 else ("tool_call" if seq == 2 else "final_action"),
            "tool_id": "search_db" if seq == 2 else None,
            "args_hash": str(uuid.uuid4())[:8],  # Empreinte uniquement, pas de texte brut (INV-04)
            "mem_ids": [],
            "scores": [],
            "latency_ms": random.uniform(50, 300)
        }
        events.append(event)

    episode = {
        "id": episode_id,
        "agent_id": "agent_alpha",
        "scenario": "recherche_information",
        "ts_start": ts_start,
        "ts_end": current_ts,
        "label": "poisoned" if est_empoisonne else "benign",
        "attack_family": "prompt_injection" if est_empoisonne else None,
        "events": events
    }

    return episode


if __name__ == "__main__":
    NOMBRE_EPISODES = 800
    FICHIER_SORTIE = "AgentTraceBench-v0.jsonl"

    print(f"Génération de {NOMBRE_EPISODES} épisodes en cours...")

    with open(FICHIER_SORTIE, "w", encoding="utf-8") as f:
        for _ in range(NOMBRE_EPISODES):
            # On simule un taux d'empoisonnement d'environ 15%
            est_empoisonne = random.random() < 0.15
            trace = generer_episode(est_empoisonne)

            # JSONL : un objet JSON valide par ligne, sans indentation
            f.write(json.dumps(trace) + "\n")

    print(f"Terminé ! Le corpus a été sauvegardé dans {FICHIER_SORTIE}")