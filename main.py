import json
from enum import Enum
from typing import List, Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, model_validator

# --- IMPORTS POUR LA BASE DE DONNÉES ---
from sqlalchemy import create_engine, Column, String, Float, Text, desc
from sqlalchemy.orm import declarative_base, sessionmaker

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
        if self.ts_end < self.ts_start:
            raise ValueError(f"INV-03 Violé: ts_end {self.ts_end} est inférieur à ts_start {self.ts_start}")

        if not self.events:
            return self

        if self.events[0].ts < self.ts_start:
            raise ValueError(
                f"INV-02 Violé: premier évènement {self.events[0].ts} est avant ts_start {self.ts_start}")
        if self.events[-1].ts > self.ts_end:
            raise ValueError(
                f"INV-02 Violé: dernier évènement {self.events[-1].ts} est après ts_end {self.ts_end}")

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
            donnees = json.loads(ligne)
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
                # On convertit les événements en JSON pour les stocker facilement
                events_json=json.dumps([e.model_dump() for e in episode.events])
            )
            # Ajoute si l'ID n'existe pas déjà (évite les doublons lors de tests multiples)
            if not db.query(EpisodeDB).filter(EpisodeDB.id == episode.id).first():
                db.add(db_episode)
                acceptes += 1
            else:
                rejetes += 1
                erreurs.append(f"Episode {episode.id} déjà existant.")

        except Exception as e:
            rejetes += 1
            erreurs.append(str(e))

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
async def interface_web(request: Request):
    """Génère l'interface HTML avec la liste des épisodes triée par score décroissant."""
    db = SessionLocal()

    # On récupère les épisodes triés par score décroissant (Exigence EF-10)
    # On limite à 100 pour garder une interface fluide
    episodes = db.query(EpisodeDB).order_by(desc(EpisodeDB.score)).limit(100).all()
    db.close()

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"episodes": episodes}
    )