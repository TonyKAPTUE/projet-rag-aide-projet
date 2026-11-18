# Atelier Documentaire RAG — Assistant Technique pour Projets Étudiants

Application RAG (*Retrieval-Augmented Generation*) conçue pour accompagner les étudiants en ingénierie, électronique, systèmes embarqués et science des données dans l'exploitation directe des **datasheets constructeurs (PDF, Markdown, TXT)** et des **datasets expérimentaux (CSV, JSON, Excel)**.

L'interface adopte une esthétique éditoriale d'atelier de laboratoire (tons papier, typographie lisible, citations cliquables vers la page ou la ligne exacte, **sans aucun emoji**).

---

## Architecture Fonctionnelle

1. **Extraction Documentaire & Métrologique ([`backend/extractor.py`](backend/extractor.py))**
   - **Datasheets PDF** : découpage sémantique par page et par section technique numérotée, extraction automatique des tensions détectées (`V`), des adresses/registres hexadécimaux (`0x76`, `0xD0`, `0xF2`, `0xF4`), des fréquences et des plages thermiques.
   - **Datasets CSV / JSON / XLSX** : synthèse automatique du schéma et des statistiques numériques (`min`, `max`, `moyenne`) + transformation de chaque enregistrement en segment sémantique indexé avec sa référence de ligne exacte (`Ligne 6 (EXP-06)`).

2. **Vectorisation Sémantique Hybride ([`backend/vectorizer.py`](backend/vectorizer.py))**
   - **Vectorisation locale haute dimension** : combinaison de N-grams lexicaux techniques, de sous-mots (`char_wb` 3-5 N-grams), d'expansion de synonymes techniques FR/EN (brochage/pinout, alimentation/VDD, registres, bus I2C/SPI) et de surpondération des identifiants matériels exacts.
   - **Embeddings Denses Hugging Face (optionnel)** : bascule automatique sur `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` via l'API Hugging Face lorsqu'un jeton `HF_TOKEN` est renseigné.

3. **Génération Assistée par `Qwen/Qwen2.5-7B-Instruct` ([`backend/generator.py`](backend/generator.py))**
   - **Inférence Hugging Face Serverless** : appel direct à `Qwen/Qwen2.5-7B-Instruct` via `huggingface_hub.InferenceClient` avec un prompt système strict imposant un ton humain d'encadrant de travaux pratiques, des citations entre crochets `[Fichier — Page/Ligne]` et l'absence totale d'emojis.
   - **Synthèse Documentaire Locale de Secours** : en l'absence de `HF_TOKEN` ou hors-ligne, un moteur déterministe produit une synthèse structurée à partir des extraits de la datasheet et du dataset avec conseils pratiques de câblage et de programmation.

4. **Corpus de Démarrage Pré-installé ([`backend/sample_generator.py`](backend/sample_generator.py))**
   - `BME280_Datasheet_Technique_FR.pdf` : datasheet complète sur 3 pages du capteur environnemental Bosch BME280.
   - `BME280_Dataset_Essais_Calibration.csv` : 10 essais en laboratoire (`EXP-01` à `EXP-10`) mesurant la consommation (`µA`), l'auto-échauffement thermique et le bruit RMS barométrique.
   - `Comparatif_Composants_Capteurs_I2C.json` : comparatif technique `BME280`, `BMP280`, `SHT31-D` et `INA219`.

---

## Démarrage Rapide

```bash
# 1. Créer l'environnement virtuel et installer les dépendances
uv venv .venv
uv pip install --python .venv/bin/python -r requirements.txt

# 2. (Optionnel) Configurer votre jeton Hugging Face pour Qwen/Qwen2.5-7B-Instruct
export HF_TOKEN="hf_votre_jeton"

# 3. Lancer le serveur FastAPI
.venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Vous pouvez également renseigner ou modifier votre clé `HF_TOKEN` directement dans l'interface web via le bouton **Configuration Qwen2.5-7B** en haut à droite.

---

## Tests Automatisés

```bash
PYTHONPATH=. .venv/bin/python tests/test_rag_pipeline.py
```
