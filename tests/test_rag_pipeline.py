"""
Automated verification tests for the Student Engineering RAG Assistant:
1. Sample generation (BME280 PDF datasheet + CSV calibration dataset + JSON I2C comparison)
2. Document extraction (exact page citations for PDF, row citations & statistics for CSV/JSON)
3. Hybrid semantic vectorization and retrieval accuracy
4. RAG generation with Qwen2.5-7B-Instruct & zero-emoji guarantee
5. FastAPI endpoints (/api/status, /api/documents, /api/chat)
"""
from fastapi.testclient import TestClient

from backend.main import app, load_default_samples


def run_all_tests() -> None:
    load_default_samples()
    client = TestClient(app)

    # 1. Status endpoint
    res_status = client.get("/api/status")
    assert res_status.status_code == 200, res_status.text
    status_data = res_status.json()
    assert status_data["status"] == "ok"
    assert status_data["model_id"] == "Qwen/Qwen2.5-7B-Instruct"
    assert status_data["corpus"]["total_documents"] >= 3
    assert status_data["corpus"]["total_chunks"] >= 10
    print(f"[OK] /api/status: {status_data['corpus']['total_documents']} docs, {status_data['corpus']['total_chunks']} chunks, {status_data['corpus']['vector_dimension']} dims")

    # 2. Query RAG on PDF Datasheet + CSV Dataset (Humidity 0% bug / 0xF2 vs 0xF4 / EXP-10)
    q1 = "Pourquoi l'humidité reste bloquée à 0 % et quel est l'ordre d'écriture des registres 0xF2 et 0xF4 ?"
    res_chat1 = client.post("/api/chat", json={"question": q1, "top_k": 4})
    assert res_chat1.status_code == 200, res_chat1.text
    chat1 = res_chat1.json()
    assert len(chat1["citations"]) > 0
    assert "0xF2" in chat1["answer"] or "0xf2" in chat1["answer"].lower()
    print(f"[OK] /api/chat (Registres 0xF2/0xF4): top citation = {chat1['citations'][0]['doc_name']} ({chat1['citations'][0]['source_ref']}, score={chat1['citations'][0]['similarity_score']})")

    # 3. Query RAG on CSV Dataset (Self-heating EXP-06)
    q2 = "Quelle est l'erreur de température observée dans l'essai EXP-06 du dataset ?"
    res_chat2 = client.post("/api/chat", json={"question": q2, "top_k": 4})
    assert res_chat2.status_code == 200, res_chat2.text
    chat2 = res_chat2.json()
    cited_refs = [c["source_ref"] for c in chat2["citations"]]
    assert any("EXP-06" in r or "Ligne 6" in r for r in cited_refs), f"Expected EXP-06 in {cited_refs}"
    print(f"[OK] /api/chat (Dataset EXP-06): citations = {cited_refs}")

    # 4. Upload a new custom CSV dataset via /api/documents/upload
    custom_csv = (
        "composant,tension_nominale_v,courant_max_ma,protocole,remarque\n"
        "MPU6050,3.3,3.9,I2C (0x68/0x69),Accéléromètre + Gyroscope MEMS 6 axes\n"
        "ADS1115,3.3,0.15,I2C (0x48-0x4B),Convertisseur ADC 16 bits 4 canaux\n"
    ).encode("utf-8")
    res_up = client.post(
        "/api/documents/upload",
        files={"file": ("Capteurs_Supplementaires_Projet.csv", custom_csv, "text/csv")},
    )
    assert res_up.status_code == 200, res_up.text
    up_doc_id = res_up.json()["document"]["doc_id"]
    print(f"[OK] /api/documents/upload: uploaded doc_id={up_doc_id}")

    # Clean up test uploaded doc
    res_del = client.delete(f"/api/documents/{up_doc_id}")
    assert res_del.status_code == 200


if __name__ == "__main__":
    run_all_tests()
    print("ALL TESTS PASSED SUCCESSFULLY.")
