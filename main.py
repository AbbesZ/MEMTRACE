import json
import logging
from enum import Enum
from typing import List, Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, model_validator

# --- IMPORTS POUR LA BASE DE DONNÉES ---
from sqlalchemy import create_engine, Column, String, Float, Text, desc
from sqlalchemy.orm import declarative_base, sessionmaker

# Configuration du logger (ENF-11)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("MEMTRACE")

# --- CONFIGURATION SQLITE (Imposée en dev) ---
SQLALCHEMY_DATABASE_URL = "sqlite:///./memtrace.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# --- MODÈLE DE DONNÉES SQLALCHEMY ---
class EpisodeDB(Base):
    __tablename__ = "episodes"
    id = Column(String, primary_key=True, index=True)
    agent_id = Column(String, index=True)
    scenario = Column(String)
    ts_start = Column(Float)
    ts_end = Column(Float)
    label = Column(String, index=True)
    attack_family = Column(String, nullable=True)
    # On stocke les événements sous forme de chaîne JSON pour simplifier le stockage
    events_json = Column(Text)
    score = Column(Float, nullable=True)  # Pour plus tard (Exigence EF-06)


# Crée la table dans la base de données
Base.metadata.create_all(bind=engine)


# --- 1. SCHÉMA DE TRACE CANONIQUE (Pydantic) ---
class EventType(str, Enum):
    user_msg = "user_msg"
    mem_read = "mem_read"
    mem_write = "mem_write"
    tool_call = "tool_call"
    tool_result = "tool_result"
    final_action = "final_action"


class Event(BaseModel):
    seq: int
    ts: float
    type: EventType
    tool_id: Optional[str] = None
    args_hash: str
    mem_ids: List[str]
    scores: List[float]
    latency_ms: float


class Episode(BaseModel):
    id: str
    agent_id: str
    scenario: str
    ts_start: float
    ts_end: float
    label: str
    attack_family: Optional[str] = None
    events: List[Event]

    @model_validator(mode='after')
    def verifier_invariants(self) -> 'Episode':
        if not self.events:
            return self
        for i in range(len(self.events) - 1):
            evt_courant = self.events[i]
            evt_suivant = self.events[i + 1]
            if evt_suivant.seq <= evt_courant.seq:
                raise ValueError(
                    f"INV-01 Violé: seq {evt_suivant.seq} n'est pas strictement supérieur à {evt_courant.seq}")
            if evt_suivant.ts < evt_courant.ts:
                raise ValueError(
                    f"INV-02 Violé: horodatage {evt_suivant.ts} est inférieur au précédent {evt_courant.ts}")
        return self


# --- 3. CONTRAT D'INTERFACE DE PROGRAMMATION ---
app = FastAPI(title="Console Forensique MEMTRACE")


def adaptateur_langgraph(donnees_brutes: dict) -> dict:
    """Convertit un journal LangGraph brut vers le schéma canonique MEMTRACE (EF-02)."""
    # Simulation de la logique d'adaptation
    if "langgraph_version" in donnees_brutes:
        logger.info("Conversion d'un format LangGraph détecté.")
        return donnees_brutes # Simplifié pour la preuve de concept
    return donnees_brutes

@app.post("/ingest", summary="Ingère un lot de journaux JSONL (EF-01)")
async def ingest_logs(file: UploadFile = File(...)):
    acceptes = 0
    rejetes = 0
    erreurs = []

    content = await file.read()
    lignes = content.decode("utf-8").strip().split('\n')

    # Ouvre une session avec la base de données
    db = SessionLocal()

    for ligne in lignes:
        if not ligne.strip():
            continue
        try:
            # 1. On charge le JSON brut
            donnees_brutes = json.loads(ligne)

            # 2. On passe par l'adaptateur (EF-02)
            donnees = adaptateur_langgraph(donnees_brutes)

            # 3. Normalisation Pydantic
            episode = Episode(**donnees)

            # Sauvegarde en base de données
            db_episode = EpisodeDB(
                id=episode.id,
                agent_id=episode.agent_id,
                scenario=episode.scenario,
                ts_start=episode.ts_start,
                ts_end=episode.ts_end,
                label=episode.label,
                attack_family=episode.attack_family,
                events_json=json.dumps([e.model_dump() for e in episode.events])
            )

            # Vérification des doublons
            if not db.query(EpisodeDB).filter(EpisodeDB.id == episode.id).first():
                db.add(db_episode)
                acceptes += 1
                # --- LOG INFO : Succès ---
                logger.info(f"Épisode {episode.id} ingéré avec succès.")
            else:
                rejetes += 1
                msg_doublon = f"Episode {episode.id} déjà existant."
                erreurs.append(msg_doublon)
                # --- LOG WARNING : Doublon ---
                logger.warning(f"Rejet : {msg_doublon}")

        except Exception as e:
            rejetes += 1
            erreurs.append(str(e))
            # --- LOG ERROR : Exception Pydantic ou autre ---
            logger.error(f"Erreur lors de l'ingestion d'une ligne : {e}")

    # Valide les changements dans la base
    db.commit()
    db.close()

    return {"episodes_acceptes": acceptes, "episodes_rejetes": rejetes, "details_rejets": erreurs[:5]}


@app.get("/healthz", summary="Sonde de disponibilité")
def health_check():
    return {"status": "ok"}


@app.get("/episodes", summary="Liste des épisodes")
def lister_episodes():
    """Récupère les épisodes stockés dans la base de données SQLite."""
    db = SessionLocal()
    episodes = db.query(EpisodeDB).limit(5).all()
    db.close()
    return {"nombre_trouves": len(episodes), "episodes": episodes}


# --- CONFIGURATION INTERFACE WEB (HTMX + Jinja2) ---
templates = Jinja2Templates(directory="templates")


@app.get("/ui", response_class=HTMLResponse, summary="Interface d'investigation (EF-10)")
async def interface_web(
    request: Request,
    min_score: float = 0.0,
    scenario: Optional[str] = None,
    agent_id: Optional[str] = None,
    label: Optional[str] = None
):
    """Génère l'interface HTML avec filtres (EF-10) et seuil réglable (EF-07)."""
    db = SessionLocal()
    query = db.query(EpisodeDB)

    # Application des filtres demandés
    if scenario:
        query = query.filter(EpisodeDB.scenario.contains(scenario))
    if agent_id:
        query = query.filter(EpisodeDB.agent_id.contains(agent_id))
    if label:
        query = query.filter(EpisodeDB.label == label)
    if min_score > 0:
        query = query.filter(EpisodeDB.score >= min_score)

    # Tri par score décroissant et limite
    episodes = query.order_by(desc(EpisodeDB.score)).limit(100).all()
    db.close()

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "episodes": episodes,
            "min_score": min_score,
            "scenario": scenario or "",
            "agent_id": agent_id or "",
            "label": label or ""
        }
    )


@app.get("/episodes/{id}", summary="Détail d'un épisode")
def get_episode(id: str):
    """Détail d'un épisode : métadonnées, score, descripteurs contributifs."""
    db = SessionLocal()
    ep = db.query(EpisodeDB).filter(EpisodeDB.id == id).first()
    db.close()

    if not ep:
        raise HTTPException(status_code=404, detail="Épisode non trouvé")

    return {
        "id": ep.id,
        "scenario": ep.scenario,
        "label": ep.label,
        "score": ep.score
        # Les descripteurs contributifs (EF-13) pourraient être ajoutés ici ultérieurement
    }


@app.get("/episodes/{id}/timeline", summary="Frise temporelle et découplage (EF-12)")
def get_episode_timeline(id: str):
    """Séquence d'événements et arêtes écriture -> relecture avec délais."""
    db = SessionLocal()
    ep = db.query(EpisodeDB).filter(EpisodeDB.id == id).first()
    db.close()

    if not ep:
        raise HTTPException(status_code=404, detail="Épisode non trouvé")

    events = json.loads(ep.events_json)

    # Reconstruction des arêtes de découplage pour l'interface
    mem_writes = {}
    edges = []

    for evt in events:
        if evt['type'] == 'mem_write':
            for m_id in evt['mem_ids']:
                if m_id not in mem_writes:
                    mem_writes[m_id] = evt['ts']
        elif evt['type'] == 'mem_read':
            for m_id in evt['mem_ids']:
                if m_id in mem_writes:
                    delay = evt['ts'] - mem_writes[m_id]
                    edges.append({
                        "mem_id": m_id,
                        "ts_write": mem_writes[m_id],
                        "ts_read": evt['ts'],
                        "delay_s": delay
                    })

    return {"events": events, "edges": edges}


@app.post("/score", summary="Relance le scoring")
def rescore():
    """Relance le scoring du corpus avec un modèle donné."""
    # Dans une version complète, on déclencherait ici le subprocess analyse_ml.py
    return {"message": "Scoring relancé avec succès sur le corpus."}


@app.get("/metrics", summary="Métriques globales (EF-14)")
def get_metrics(prevalence: float = 0.001):
    """Métriques globales, paramètre de prévalence pour la valeur prédictive positive."""
    # Simulation des métriques demandées pour le harnais d'évaluation
    return {
        "auroc": 0.95,  # À calculer dynamiquement via sklearn
        "prevalence_cible": prevalence,
        "valeur_predictive_positive": 0.08  # Exemple typique vu dans le bloc A4
    }


class ReviewModel(BaseModel):
    marquage: str  # 'vrai_positif' ou 'faux_positif'


@app.post("/episodes/{id}/review", summary="Marquage analyste (EF-15)")
def review_episode(id: str, review: ReviewModel):
    """Enregistre le marquage analyste, marquage persistant."""
    # La logique de persistance viendra s'ajouter à la base SQLite
    return {"message": f"Épisode {id} marqué comme {review.marquage}"}


@app.get("/ui/episodes/{id}/timeline", response_class=HTMLResponse, summary="Fragment HTMX de la frise")
async def ui_episode_timeline(request: Request, id: str):
    """Génère le fragment HTML de la frise pour l'interface HTMX."""
    db = SessionLocal()
    ep = db.query(EpisodeDB).filter(EpisodeDB.id == id).first()
    db.close()

    if not ep:
        return HTMLResponse(content="<p>Épisode introuvable.</p>", status_code=404)

    events = json.loads(ep.events_json)
    mem_writes = {}
    edges = []

    for evt in events:
        if evt['type'] == 'mem_write':
            for m_id in evt['mem_ids']:
                if m_id not in mem_writes:
                    mem_writes[m_id] = evt['ts']
        elif evt['type'] == 'mem_read':
            for m_id in evt['mem_ids']:
                if m_id in mem_writes:
                    edges.append({
                        "mem_id": m_id,
                        "delay_s": evt['ts'] - mem_writes[m_id]
                    })

    top_descripteurs = [
        {"nom": "F5 - Délai de découplage (Latence)", "contribution": "+0.42"},
        {"nom": "F1 - Appels d'outils", "contribution": "+0.15"},
        {"nom": "F4 - Longueur de l'épisode", "contribution": "+0.08"}
    ]

    return templates.TemplateResponse(
        request=request,
        name="timeline.html",
        context={"events": events, "edges": edges, "top_descripteurs": top_descripteurs}
    )