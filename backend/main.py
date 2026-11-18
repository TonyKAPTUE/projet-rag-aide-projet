"""
FastAPI Backend for the Student Engineering RAG Assistant (Datasheets & Datasets).
Provides endpoints for:
- Uploading and parsing component datasheets (PDF, MD, TXT) and datasets (CSV, JSON, XLSX)
- Loading pre-installed laboratory benchmark files (Bosch BME280 Datasheet PDF + Calibration Dataset CSV + I2C Sensors JSON)
- Inspecting extracted chunks, vector dimensions, and dataset statistics
- Querying the RAG pipeline with Qwen/Qwen2.5-7B-Instruct (Hugging Face) and exact page/row citations
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.extractor import extract_document
from backend.generator import DEFAULT_MODEL_ID, generate_rag_answer
from backend.sample_generator import ensure_sample_files
from backend.vectorizer import SemanticVectorStore


BASE_DIR = Path(__file__).resolve().parent.parent
SAMPLES_DIR = BASE_DIR / "data" / "samples"
UPLOADS_DIR = BASE_DIR / "data" / "uploads"
FRONTEND_DIR = BASE_DIR / "frontend"

UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="Atelier RAG — Assistant Technique Projets Étudiants",
    description=(
        "Extraction documentaire, vectorisation sémantique et génération assistée par Qwen2.5-7B-Instruct "
        "pour l'exploitation de datasheets (PDF) et datasets de composants."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global in-memory vector store & runtime configuration
vector_store = SemanticVectorStore()
runtime_config: dict[str, Any] = {
    "hf_token": os.environ.get("HF_TOKEN", ""),
    "model_id": os.environ.get("HF_MODEL_ID", DEFAULT_MODEL_ID),
}


def load_default_samples() -> list[dict[str, Any]]:
    """Generate and index the default BME280 datasheet and datasets on startup."""
    sample_paths = ensure_sample_files(SAMPLES_DIR)
    loaded_meta = []
    for path in sample_paths.values():
        raw_bytes = path.read_bytes()
        doc = extract_document(path.name, raw_bytes)
        vector_store.add_document(doc, hf_token=runtime_config["hf_token"])
        loaded_meta.append(doc.to_meta_dict())
    return loaded_meta


@app.on_event("startup")
def on_startup() -> None:
    load_default_samples()


class ConfigUpdateRequest(BaseModel):
    hf_token: str | None = Field(default=None, description="Jeton d'accès Hugging Face (hf_...)")
    model_id: str = Field(default=DEFAULT_MODEL_ID, description="Identifiant du modèle Hugging Face")


class ChatQueryRequest(BaseModel):
    question: str = Field(..., min_length=2, description="Question technique de l'étudiant")
    top_k: int = Field(default=4, ge=1, le=10, description="Nombre d'extraits à récupérer")
    temperature: float = Field(default=0.2, ge=0.0, le=1.0)
    doc_filter: list[str] | None = Field(default=None, description="Filtre optionnel par doc_id")
    history: list[dict[str, str]] | None = Field(default=None)


@app.get("/api/status")
def get_status() -> dict[str, Any]:
    """Return index statistics, active documents, and Qwen2.5-7B configuration status."""
    has_token = bool(runtime_config.get("hf_token", "").strip())
    summary = vector_store.status_summary()
    return {
        "status": "ok",
        "model_id": runtime_config["model_id"],
        "hf_token_configured": has_token,
        "inference_mode_label": (
            f"Hugging Face Inference API ({runtime_config['model_id']})"
            if has_token
            else f"Synthèse Documentaire Locale + Prêt pour {runtime_config['model_id']} (HF_TOKEN)"
        ),
        "corpus": summary,
    }


@app.post("/api/config")
def update_config(req: ConfigUpdateRequest) -> dict[str, Any]:
    """Configure Hugging Face API token and model ID at runtime."""
    if req.hf_token is not None:
        runtime_config["hf_token"] = req.hf_token.strip()
    if req.model_id.strip():
        runtime_config["model_id"] = req.model_id.strip()

    # Re-index with dense HF embeddings if token was added
    vector_store._rebuild_index(hf_token=runtime_config["hf_token"])
    return get_status()


@app.get("/api/documents")
def list_documents() -> dict[str, Any]:
    """List all indexed datasheets and datasets with their metadata and chunks."""
    return vector_store.status_summary()


@app.get("/api/documents/{doc_id}")
def get_document_details(doc_id: str) -> dict[str, Any]:
    """Return full chunk breakdown and extracted engineering telemetry for a specific document."""
    doc = vector_store.documents.get(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' introuvable.")
    return {
        "meta": doc.to_meta_dict(),
        "chunks": [c.to_dict() for c in doc.chunks],
    }


@app.delete("/api/documents/{doc_id}")
def delete_document(doc_id: str) -> dict[str, Any]:
    """Remove a document from the active semantic index."""
    removed = vector_store.remove_document(doc_id, hf_token=runtime_config["hf_token"])
    if not removed:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' introuvable.")
    return get_status()


@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...)) -> dict[str, Any]:
    """Ingest, parse, and vectorize a student-uploaded datasheet (PDF/MD/TXT) or dataset (CSV/JSON/XLSX)."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Nom de fichier manquant.")

    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="Le fichier envoyé est vide.")

    try:
        extracted = extract_document(file.filename, raw_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de l'extraction de '{file.filename}' : {str(exc)}",
        ) from exc

    # Save copy in uploads folder
    safe_path = UPLOADS_DIR / Path(file.filename).name
    safe_path.write_bytes(raw_bytes)

    vector_store.add_document(extracted, hf_token=runtime_config["hf_token"])
    return {
        "message": f"Document '{file.filename}' extrait et vectorisé avec succès ({len(extracted.chunks)} segments).",
        "document": extracted.to_meta_dict(),
        "corpus": vector_store.status_summary(),
    }


@app.post("/api/documents/load-samples")
def reload_sample_corpus() -> dict[str, Any]:
    """Restore or reload the default BME280 PDF datasheet and calibration CSV/JSON datasets."""
    loaded = load_default_samples()
    return {
        "message": f"{len(loaded)} documents de référence chargés et vectorisés.",
        "loaded_documents": loaded,
        "corpus": vector_store.status_summary(),
    }


@app.post("/api/chat")
def query_rag_assistant(req: ChatQueryRequest) -> dict[str, Any]:
    """
    Execute the 3-stage RAG pipeline:
    1. Semantic & Lexical Hybrid Retrieval over indexed datasheets/datasets
    2. Prompt construction with strict page/row citation tags
    3. Generation with Qwen/Qwen2.5-7B-Instruct (or local grounded fallback)
    """
    if not vector_store.chunks:
        raise HTTPException(
            status_code=400,
            detail="Aucun document n'est actuellement indexé. Importez une datasheet (PDF) ou un dataset (CSV/JSON) avant de poser une question.",
        )

    passages = vector_store.search(
        query=req.question,
        top_k=req.top_k,
        doc_filter=req.doc_filter,
        hf_token=runtime_config["hf_token"],
    )

    result = generate_rag_answer(
        question=req.question,
        passages=passages,
        hf_token=runtime_config["hf_token"],
        model_id=runtime_config["model_id"],
        temperature=req.temperature,
        history=req.history,
    )

    return {
        "question": req.question,
        "answer": result.answer,
        "model_used": result.model_used,
        "inference_mode": result.inference_mode,
        "latency_ms": result.latency_ms,
        "notice": result.notice,
        "citations": result.citations,
        "pipeline_trace": {
            "etape_1_extraction": f"{len(vector_store.documents)} documents ({len(vector_store.chunks)} segments indexés)",
            "etape_2_vectorisation": vector_store.embedding_backend_name,
            "etape_3_recuperation": f"Top-{len(passages)} segments extraits (score max : {passages[0].similarity_score:.2f})" if passages else "0 segment",
            "etape_4_generation": result.model_used,
        },
    }


# Serve static frontend assets
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/")
def serve_index() -> FileResponse:
    index_path = FRONTEND_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Interface frontend non trouvée.")
    return FileResponse(str(index_path))
