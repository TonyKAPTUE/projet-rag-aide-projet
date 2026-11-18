"""
Document Extraction Pipeline for Engineering Datasheets (PDF, Markdown, TXT)
and Component Datasets (CSV, JSON, XLSX).
Produces structured, citation-ready chunks with exact page numbers or row ranges.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

import pandas as pd
from pypdf import PdfReader


@dataclass
class DocumentChunk:
    chunk_id: str
    doc_id: str
    doc_name: str
    doc_type: str  # "datasheet" or "dataset"
    source_ref: str  # e.g. "Page 2" or "Ligne 6 (EXP-06)" or "Synthèse Statistique"
    section_title: str
    content: str
    page_or_row: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ExtractedDocument:
    doc_id: str
    filename: str
    doc_type: str  # "datasheet" | "dataset"
    file_format: str  # "PDF", "CSV", "JSON", "XLSX", "TXT"
    total_units: int  # number of pages or dataset rows
    unit_label: str  # "pages" or "lignes"
    summary_stats: dict[str, Any]
    chunks: list[DocumentChunk]

    def to_meta_dict(self) -> dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "filename": self.filename,
            "doc_type": self.doc_type,
            "file_format": self.file_format,
            "total_units": self.total_units,
            "unit_label": self.unit_label,
            "chunk_count": len(self.chunks),
            "summary_stats": self.summary_stats,
        }


def _compute_doc_id(filename: str, raw_bytes: bytes) -> str:
    digest = hashlib.sha1(raw_bytes[:65536] + filename.encode("utf-8")).hexdigest()[:10]
    clean_stem = re.sub(r"[^a-zA-Z0-9_-]", "_", Path(filename).stem)[:24].lower()
    return f"{clean_stem}_{digest}"


def _detect_section_heading(text_block: str, fallback: str) -> str:
    """Detect technical headings such as '2. Caractéristiques Électriques' or uppercase headers."""
    for line in text_block.splitlines():
        clean = line.strip()
        if not clean:
            continue
        if re.match(r"^(\d+[\.\)]\s+[A-ZÀ-Ÿ].{3,75})$", clean):
            return clean
        if re.match(r"^(#{1,3}\s+.{3,75})$", clean):
            return clean.lstrip("#").strip()
        if len(clean) < 75 and ("BOSCH" in clean or "Registre" in clean or "Brochage" in clean or "Pinout" in clean):
            return clean
    return fallback


def _extract_datasheet_key_parameters(full_text: str) -> dict[str, Any]:
    """Extract quick engineering telemetry from datasheet text for the document summary card."""
    voltages = sorted(set(re.findall(r"\b\d+(?:\.\d+)?\s*V\b", full_text)))[:6]
    i2c_addrs = sorted(set(re.findall(r"\b0x[0-9A-Fa-f]{2}\b", full_text)))[:10]
    frequencies = sorted(set(re.findall(r"\b\d+(?:\.\d+)?\s*(?:Hz|kHz|MHz)\b", full_text)))[:5]
    temperatures = sorted(set(re.findall(r"[-+]?\d+(?:\.\d+)?\s*°C", full_text)))[:6]
    return {
        "tensions_detectees": voltages,
        "registres_ou_adresses_hex": i2c_addrs,
        "frequences_detectees": frequencies,
        "plages_thermiques": temperatures,
    }


def extract_pdf_datasheet(filename: str, raw_bytes: bytes, chunk_size: int = 850, overlap: int = 160) -> ExtractedDocument:
    """Extract text page-by-page from a PDF datasheet, preserving exact page citations and section titles."""
    doc_id = _compute_doc_id(filename, raw_bytes)
    reader = PdfReader(io.BytesIO(raw_bytes))
    num_pages = len(reader.pages)
    chunks: list[DocumentChunk] = []
    all_text_parts: list[str] = []

    for page_idx, page in enumerate(reader.pages):
        page_num = page_idx + 1
        raw_page_text = page.extract_text() or ""
        # Normalize whitespace while keeping line structure
        lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in raw_page_text.splitlines()]
        clean_lines = [ln for ln in lines if ln]
        page_text = "\n".join(clean_lines)
        if not page_text.strip():
            continue

        all_text_parts.append(page_text)

        # Split page into semantic paragraphs/sections by numbered headings or double lines
        sections = re.split(r"\n(?=\d+\.\s+[A-ZÀ-Ÿ])", page_text)
        sub_idx = 0
        for sec in sections:
            sec = sec.strip()
            if not sec:
                continue
            sec_title = _detect_section_heading(sec, f"Page {page_num} - Section technique")
            if len(sec) <= chunk_size:
                sub_idx += 1
                chunks.append(
                    DocumentChunk(
                        chunk_id=f"{doc_id}_p{page_num}_s{sub_idx}",
                        doc_id=doc_id,
                        doc_name=filename,
                        doc_type="datasheet",
                        source_ref=f"Page {page_num}",
                        section_title=sec_title,
                        content=sec,
                        page_or_row=page_num,
                        metadata={"page": page_num, "section": sec_title},
                    )
                )
            else:
                # Sliding window over lines in large sections
                start = 0
                while start < len(sec):
                    end = min(start + chunk_size, len(sec))
                    if end < len(sec):
                        newline_pos = sec.rfind("\n", start + chunk_size // 2, end)
                        if newline_pos != -1:
                            end = newline_pos
                    piece = sec[start:end].strip()
                    if piece:
                        sub_idx += 1
                        chunks.append(
                            DocumentChunk(
                                chunk_id=f"{doc_id}_p{page_num}_s{sub_idx}",
                                doc_id=doc_id,
                                doc_name=filename,
                                doc_type="datasheet",
                                source_ref=f"Page {page_num}",
                                section_title=sec_title,
                                content=piece,
                                page_or_row=page_num,
                                metadata={"page": page_num, "section": sec_title},
                            )
                        )
                    if end >= len(sec):
                        break
                    start = max(start + 1, end - overlap)

    full_text = "\n\n".join(all_text_parts)
    summary_stats = _extract_datasheet_key_parameters(full_text)
    summary_stats["total_caracteres"] = len(full_text)

    return ExtractedDocument(
        doc_id=doc_id,
        filename=filename,
        doc_type="datasheet",
        file_format="PDF",
        total_units=num_pages,
        unit_label="pages",
        summary_stats=summary_stats,
        chunks=chunks,
    )


def extract_text_datasheet(filename: str, raw_bytes: bytes) -> ExtractedDocument:
    """Extract chunks from Markdown or plain text technical documentation."""
    doc_id = _compute_doc_id(filename, raw_bytes)
    text = raw_bytes.decode("utf-8", errors="replace")
    blocks = re.split(r"\n(?=#{1,3}\s+|\d+\.\s+[A-ZÀ-Ÿ])", text)
    chunks: list[DocumentChunk] = []

    for idx, block in enumerate(blocks, start=1):
        clean = block.strip()
        if not clean:
            continue
        sec_title = _detect_section_heading(clean, f"Section {idx}")
        chunks.append(
            DocumentChunk(
                chunk_id=f"{doc_id}_sec{idx}",
                doc_id=doc_id,
                doc_name=filename,
                doc_type="datasheet",
                source_ref=f"Section {idx}",
                section_title=sec_title,
                content=clean[:1200],
                page_or_row=idx,
                metadata={"section": sec_title},
            )
        )

    summary_stats = _extract_datasheet_key_parameters(text)
    return ExtractedDocument(
        doc_id=doc_id,
        filename=filename,
        doc_type="datasheet",
        file_format=Path(filename).suffix.lstrip(".").upper() or "TXT",
        total_units=len(chunks),
        unit_label="sections",
        summary_stats=summary_stats,
        chunks=chunks,
    )


def extract_tabular_dataset(filename: str, raw_bytes: bytes) -> ExtractedDocument:
    """
    Extract schema, statistical synthesis, and row-level semantic records from CSV, JSON, or Excel datasets.
    """
    doc_id = _compute_doc_id(filename, raw_bytes)
    ext = Path(filename).suffix.lower()

    if ext == ".csv":
        df = pd.read_csv(io.BytesIO(raw_bytes))
        fmt = "CSV"
    elif ext in (".xlsx", ".xls"):
        df = pd.read_excel(io.BytesIO(raw_bytes))
        fmt = "XLSX"
    elif ext == ".json":
        parsed = json.loads(raw_bytes.decode("utf-8", errors="replace"))
        if isinstance(parsed, list):
            df = pd.DataFrame(parsed)
        elif isinstance(parsed, dict):
            # Find first list key or wrap single record
            list_key = next((k for k, v in parsed.items() if isinstance(v, list)), None)
            df = pd.DataFrame(parsed[list_key]) if list_key else pd.DataFrame([parsed])
        else:
            df = pd.DataFrame([{"valeur": str(parsed)}])
        fmt = "JSON"
    else:
        raise ValueError(f"Format de dataset non supporté : {ext}")

    num_rows, num_cols = df.shape
    columns = list(df.columns)
    numeric_cols = list(df.select_dtypes(include="number").columns)

    # Build statistical summary chunk
    stats_lines = [
        f"Synthèse du Dataset : {filename} ({num_rows} entrées, {num_cols} colonnes).",
        f"Colonnes disponibles : {', '.join(str(c) for c in columns)}.",
    ]
    numeric_summary: dict[str, dict[str, float]] = {}
    for col in numeric_cols:
        series = df[col].dropna()
        if len(series) > 0:
            c_min = round(float(series.min()), 4)
            c_max = round(float(series.max()), 4)
            c_mean = round(float(series.mean()), 4)
            numeric_summary[str(col)] = {"min": c_min, "max": c_max, "moyenne": c_mean}
            stats_lines.append(f"- Variable numérique '{col}' : min = {c_min}, max = {c_max}, moyenne = {c_mean}.")

    chunks: list[DocumentChunk] = [
        DocumentChunk(
            chunk_id=f"{doc_id}_schema",
            doc_id=doc_id,
            doc_name=filename,
            doc_type="dataset",
            source_ref="Schéma & Statistiques",
            section_title=f"Vue d'ensemble et statistiques ({filename})",
            content="\n".join(stats_lines),
            page_or_row=0,
            metadata={"columns": columns, "row_count": num_rows},
        )
    ]

    # Identify a primary key/label column if present
    id_col = next(
        (c for c in columns if any(k in str(c).lower() for k in ("id", "ref", "composant", "essai", "name", "mode"))),
        columns[0] if columns else None,
    )

    # Convert rows into rich semantic passages (single row if <= 40 rows, else grouped by 3 rows)
    batch_size = 1 if num_rows <= 40 else 3
    for start_idx in range(0, min(num_rows, 300), batch_size):
        end_idx = min(start_idx + batch_size, num_rows)
        sub_df = df.iloc[start_idx:end_idx]
        row_passages = []
        row_labels = []

        for r_idx, (_, row) in enumerate(sub_df.iterrows(), start=start_idx + 1):
            label_val = str(row[id_col]) if id_col is not None and pd.notna(row[id_col]) else f"Entrée {r_idx}"
            row_labels.append(label_val)
            kv_pairs = []
            for col in columns:
                val = row[col]
                if pd.notna(val) and str(val).strip() != "":
                    kv_pairs.append(f"{col}: {val}")
            row_passages.append(f"Entrée Ligne {r_idx} ({label_val}) -> " + " | ".join(kv_pairs))

        if batch_size == 1:
            source_ref = f"Ligne {start_idx + 1} ({row_labels[0]})"
            sec_title = f"Enregistrement Dataset : {row_labels[0]}"
        else:
            source_ref = f"Lignes {start_idx + 1} à {end_idx}"
            sec_title = f"Enregistrements Dataset ({', '.join(row_labels)})"

        chunks.append(
            DocumentChunk(
                chunk_id=f"{doc_id}_r{start_idx + 1}",
                doc_id=doc_id,
                doc_name=filename,
                doc_type="dataset",
                source_ref=source_ref,
                section_title=sec_title,
                content="\n".join(row_passages),
                page_or_row=start_idx + 1,
                metadata={"row_start": start_idx + 1, "row_end": end_idx},
            )
        )

    preview_rows = df.head(6).fillna("N/A").to_dict(orient="records")
    summary_stats = {
        "colonnes": [str(c) for c in columns],
        "nombre_lignes": num_rows,
        "statistiques_numeriques": numeric_summary,
        "apercu_lignes": preview_rows,
    }

    return ExtractedDocument(
        doc_id=doc_id,
        filename=filename,
        doc_type="dataset",
        file_format=fmt,
        total_units=num_rows,
        unit_label="lignes",
        summary_stats=summary_stats,
        chunks=chunks,
    )


def extract_document(filename: str, raw_bytes: bytes) -> ExtractedDocument:
    """Universal dispatcher for datasheets (PDF, MD, TXT) and datasets (CSV, JSON, XLSX)."""
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        return extract_pdf_datasheet(filename, raw_bytes)
    if ext in (".csv", ".json", ".xlsx", ".xls"):
        return extract_tabular_dataset(filename, raw_bytes)
    if ext in (".md", ".txt", ".c", ".h", ".py"):
        return extract_text_datasheet(filename, raw_bytes)
    raise ValueError(
        f"Format de fichier '{ext}' non pris en charge. "
        "Formats acceptés : PDF, CSV, JSON, XLSX, MD, TXT."
    )
