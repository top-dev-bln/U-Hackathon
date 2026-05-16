# Tactical RAG Indexer - Implementation TODO (Hackathon MVP)

Status global: `DONE (MVP + smoke test)`

Scop: livram un microserviciu `tactical-rag-indexer-service` care transforma outputuri JSON in documente tactice + embeddings + persistenta vectoriala (FAISS), cu calitate de productie pentru demo.

Inputuri model existente in root (folosite ca referinta contract):
- `input_tactical_fusion.json`
- `input_tactical_intelligence.json`
- `input_decision_quality.json`
- `input_player_profile.json`
- `input_pressing.json`
- `input_passing_newtork.json`

Conditii agreate:
- Fara suita completa de teste automate in aceasta etapa.
- Facem doar smoke test end-to-end la final.

## 1. Foundation & Structure
- [x] Creez structura proiectului FastAPI (`app/api`, `app/core`, `app/schemas`, `app/services`, `app/builders`, `app/vectorstores`, `app/utils`).
- [x] Configurez `requirements.txt` minim: `fastapi`, `uvicorn`, `pydantic`, `sentence-transformers`, `faiss-cpu`, `numpy`, `python-slugify`, `orjson`.
- [x] Configurez `core/config.py` (env vars: `VECTOR_STORE`, `STORAGE_DIR`, `EMBEDDING_MODEL`, `MAX_PHASE_DOCUMENTS`, `MAX_PLAYER_DOCUMENTS`).
- [x] Configurez logging structurat in `core/logging.py`.

Done când:
- Aplicatia porneste local cu `uvicorn app.main:app --reload`.
- Endpoint `GET /health` raspunde `200`.

## 2. Contracts (Pydantic Schemas)
- [x] Definim schema request pentru `POST /index/match` (`matchId`, `teamId`, `teamName`, `source`, `outputs`, `options`).
- [x] Definim schema canonica `RagDocument`.
- [x] Definim schema de response pentru indexing (`documentsCreated`, `embeddingsCreated`, `warnings`, `documentTypes`, `documentPreview`).
- [x] Implementam validari pentru campuri obligatorii + fallback la outputuri optionale lipsa.

Done când:
- Payload invalid returneaza 422 clar.
- Output lipsa este warning, nu crash.

## 3. Document Builders (Deterministic)
- [x] `fusion_builder.py`: `match_summary`, `tactical_insight`, `player_priority`, `training_focus`, `frontend_summary`.
- [x] `tactical_baseline_builder.py`: `baseline_summary`, `baseline_weakness_signal`, `metric_comparison_summary`, `tactical_profile_document`, `anomaly_document`.
- [x] `decision_quality_builder.py`: `decision_quality_summary`, `player_decision_profile`, `improvable_phase`, `missed_opportunity`, `decision_by_type_summary`, `decision_timeline_summary`.
- [x] `player_profile_builder.py`: `player_movement_profile`, `player_heatmap_summary`, `player_role_interpretation`.
- [x] `pressing_builder.py`: `pressing_summary`, `pressing_player_profile`, `pressing_timeline_summary`.
- [x] `passing_network_builder.py`: `passing_network_summary`, `passing_hubs_summary`, `passing_connections_summary`, `isolated_players_summary`, `flank_usage_summary`.
- [x] `document_builder_service.py` agrega toate builder-ele + deduplicate `docId`.
- [x] Strategie `docId` determinist: `match_{matchId}_{source}_{type}_{slug}`.

Done când:
- Toate documentele au `docId`, `matchId`, `sourceService`, `documentType`, `text`, `metadata`.
- Niciun document cu `text` gol.
- Fara duplicate `docId`.

## 4. Embeddings Service
- [x] Implementam `embedding_service.py` cu `sentence-transformers/all-MiniLM-L6-v2`.
- [x] Format de embedding text: `Title + Type + Category + Players + Text`.
- [x] Validam consistenta dimensiunii embedding pentru batch.
- [x] Rejection pentru text gol sau whitespace-only.

Done când:
- `embed_documents` returneaza embedding pentru fiecare document valid.
- Erorile sunt explicite si logate.

## 5. Vector Store Service (FAISS First)
- [x] Implementam `vectorstores/faiss_store.py`:
  - `save_match_index`
  - `load_match_index`
  - `list_indexes`
  - `delete_match_index`
- [x] Persistam sidecar `documents.json` in acelasi folder.
- [x] Structura storage: `storage/vector_store/match_{matchId}/index.faiss` + `documents.json`.
- [x] Support pentru `options.rebuild` (overwrite controlat).

Done când:
- Indexul se salveaza si se reincarca dupa restart.
- Documentele si metadata sunt recuperabile din sidecar.

## 6. API Layer & Orchestration
- [x] `POST /documents/build` (debug/preview documente).
- [x] `POST /index/match` (pipeline complet build -> embed -> persist).
- [x] `GET /index/matches` (lista match-uri indexate).
- [x] `GET /index/matches/{matchId}/documents` (preview documente indexate).
- [x] `services/indexing_service.py` orchestreaza flow + warnings + timpi executie.

Done când:
- Endpointul principal returneaza contractul agreat cu count-uri corecte.
- Lipsa `passingNetwork` / `playerProfiles` produce warning in response.

## 7. Hardening pentru Demo (Senior Quality)
- [x] Error handling unificat (`core/errors.py`) cu coduri clare.
- [x] Logging lifecycle: `received_index_request`, `documents_built`, `embeddings_created`, `vector_index_saved`, `index_request_failed`.
- [x] Fara logare raw JSON complet in prod mode.
- [x] README tehnic scurt: pornire, env vars, endpointuri, exemplu request.

Done când:
- In caz de eroare embedding/vector store, status nu raporteaza fals `indexed`.
- Raspunsurile API sunt coerente si actionabile.

## 8. Smoke Test Final (fara test suite)
- [x] Pornim serviciul local.
- [x] Construim bundle real din inputurile din root.
- [x] Apelam `POST /index/match`.
- [x] Verificam:
  - status `indexed`
  - `documentsCreated > 0`
  - `embeddingsCreated == documentsCreated`
  - exista `storage/vector_store/match_{matchId}/index.faiss`
  - exista `documents.json`
- [x] Apelam `GET /index/matches/{matchId}/documents` si validam preview text.

Done când:
- Smoke test complet trece cap-coada fara interventii manuale.

## 9. Backlog (dupa demo)
- [ ] Chroma adapter.
- [ ] Teste unitare/integration.
- [ ] RAG query service separat (retrieval + LLM answering).

---

## Working Mode (tracking rapid)
Regula executie:
1. Lucram strict pe faze (1 -> 8).
2. Nu trecem la faza urmatoare pana nu bifam `Done când` pe faza curenta.
3. Actualizam checklist-ul in acelasi fisier la fiecare milestone.
