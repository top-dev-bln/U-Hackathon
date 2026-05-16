# Tactical RAG Query Service - Implementation TODO

Status global: `IN PROGRESS (MVP aproape gata, OpenAI live validation + hardening ramas)`

Scop: construim componenta RAG care interogheaza indexurile FAISS generate deja de `tactical-rag-indexer-service` si produce raspunsuri tactice bazate strict pe documentele recuperate.

Dependenta existenta:
- indexer functional (deja livrat)
- storage local FAISS: `storage/vector_store/match_<matchId>/index.faiss + documents.json`

Snapshot implementare curenta:
- [x] Endpointuri RAG implementate (`/rag/query`, `/rag/query/debug`, `/rag/matches`, `/rag/matches/{matchId}/sources`)
- [x] Retrieval FAISS + metadata filtering + fallback la filtre relaxate
- [x] Context builder deterministic cu budget de caractere
- [x] LLM service OpenAI configurabil (`RAG_OPENAI_MODEL`, default `gpt-5-mini`) + fallback template
- [x] Smoke test RAG end-to-end (`smoke_test_rag.py`)
- [ ] Validare live OpenAI in acest mediu (necesita `OPENAI_API_KEY` in runtime)

---

## 0. Scope MVP

Include:
- query embedding
- retrieval din FAISS per match
- optional metadata filtering
- context builder robust
- LLM answer generation cu citare doc IDs
- endpoint debug pentru inspectie retrieval/prompt/context

Nu include (acum):
- feedback loop / online learning
- evaluare automata avansata (RAGAS, etc.)
- multi-hop reasoning complex intre meciuri multiple
- UI frontend dedicat

---

## 1. Structura proiectului (RAG service nou)

- [x] Creez structura FastAPI pentru `tactical-rag-query-service`:
  - [x] `app/main.py`
  - [x] `app/api/routes_rag.py`
  - [x] `app/api/routes_health.py`
  - [x] `app/core/{config,logging,errors}.py`
  - [x] `app/schemas/{query.py,retrieval.py}.py`
  - [x] `app/services/{query_service.py,retrieval_service.py,context_service.py,llm_service.py}.py`
  - [x] `app/vectorstores/faiss_reader.py`
  - [x] `app/prompts/answer_prompt.txt`
  - [x] `app/utils/*`

Done cand:
- aplicatia porneste local
- `GET /health` raspunde `200`

---

## 2. Contracts API

- [x] Definim request schema pentru `POST /rag/query`:
  - `question` (required, min length)
  - `matchId` (required MVP)
  - `teamId` (optional)
  - `topK` (default 6)
  - `documentTypes` (optional filter)
  - `minScore` (optional)
  - `includeDebug` (optional)
- [x] Definim response schema:
  - `answer`
  - `matchId`
  - `retrievedCount`
  - `sources[]` (`docId`, `documentType`, `score`, `title`)
  - `warnings[]`
  - `latencyMs`
- [x] Definim `POST /rag/query/debug` cu payload extins:
  - chunks retrieve
  - context final trimis la LLM
  - prompt metadata

Done cand:
- request invalid => 422 clar
- lipsa index pentru match => 404 clar

---

## 3. Retrieval Layer (FAISS + metadata sidecar)

- [x] Implementam `faiss_reader.py`:
  - [x] load index + documents sidecar pentru match
  - [x] cosine/IP search top-k
  - [x] return `doc + score`
- [x] Implementam filtre metadata:
  - [x] `documentType in [...]`
  - [x] `teamId == ...` (daca dat)
  - [x] `score >= minScore` (post-filter)
- [x] Fallback logic:
  - [x] daca dupa filtre raman 0 rezultate, retry fara filtre stricte + warning
- [x] Caching local index per match (in-memory) pentru performanta.

Done cand:
- query retrieval returneaza rezultate stabile
- latenta retrieval < 200ms local (exceptand cold load)

---

## 4. Query Embedding

- [x] Refolosim acelasi model embedding ca la indexare (`all-MiniLM-L6-v2`) pentru compatibilitate vectoriala.
- [x] Implementam `embed_query(question)`.
- [ ] Curatare input query:
  - [x] normalize whitespace
  - [x] reject query goala
  - [ ] protectie prompt-injection basic in context layer (nu in embedding)

Done cand:
- embedding query are dimensiune identica cu indexul
- query goala este respinsa cu eroare clara

---

## 5. Context Builder

- [x] Implementam selectie context:
  - [x] sort dupa score desc
  - [x] dedupe pe `docId`
  - [x] budget token/chars (ex: max 8-12 documente, max 6k-8k chars)
- [x] Format context deterministic:
  - [x] `[docId=..., type=..., score=...]`
  - [x] `title`
  - [x] `text`
  - [x] metadata relevante (minute, player, category)
- [x] Reguli de siguranta:
  - [x] LLM raspunde doar din context
  - [x] daca context insuficient => raspuns explicit "insufficient evidence"

Done cand:
- context-ul este reproductibil pentru aceeasi intrare
- sursele pot fi citate direct in raspuns

---

## 6. LLM Answering Service

- [x] Implementam adaptor LLM in `llm_service.py` (provider configurabil):
  - [x] `OPENAI_API_KEY` optional pentru cloud
  - [x] fallback local/template mode daca lipseste cheie (pentru demo offline)
- [x] Prompt de sistem strict:
  - [x] factual
  - [x] nu inventeaza date
  - [x] citeaza doc IDs folosite
  - [x] separa clar `facts` vs `recommendations`
- [x] Output contract:
  - [x] answer scurt, clar, orientat tactic
  - [x] sectionare optionala: `Observatii`, `Riscuri`, `Actiuni recomandate`

Done cand:
- raspunsurile sunt ancorate in documente retrieve
- hallucination risk redus prin guardrails in prompt + output validation

---

## 7. Orchestration Service

- [x] `query_service.py` orchestreaza:
  - [x] validate input
  - [x] embed query
  - [x] retrieve docs
  - [x] build context
  - [x] call LLM
  - [x] build response + warnings + latency
- [ ] Logging lifecycle:
  - [x] `rag_query_received`
  - [x] `rag_query_embedded`
  - [x] `rag_query_retrieved`
  - [x] `rag_query_answered`
  - [ ] `rag_query_failed`

Done cand:
- endpointul principal returneaza raspuns complet + surse
- warning-uri actionabile la degradari

---

## 8. API Endpoints MVP

- [x] `GET /health`
- [x] `POST /rag/query`
- [x] `POST /rag/query/debug`
- [x] `GET /rag/matches` (lista match-uri indexate disponibile pentru query)
- [x] `GET /rag/matches/{matchId}/sources` (preview surse indexate)

Done cand:
- endpointurile functioneaza cap-coada pe indexul existent

---

## 9. Config & Security Baseline

- [ ] Env vars:
  - [ ] `RAG_EMBEDDING_MODEL`
  - [x] `RAG_TOP_K_DEFAULT`
  - [x] `RAG_CONTEXT_MAX_CHARS`
  - [x] `RAG_LLM_PROVIDER`
  - [x] `OPENAI_API_KEY` (optional)
  - [ ] `VECTOR_STORAGE_DIR`
- [ ] Hard limits:
  - [x] max question length
  - [x] max topK
  - [ ] timeout per request
- [ ] Basic abuse protection:
  - [ ] sanitize textual input
  - [x] trim excessive whitespace

Done cand:
- defaults sunt safe si predictibile
- configurarea e simpla pentru demo

---

## 10. Smoke Test Final (fara test suite completa)

- [x] Preconditie: exista index pentru un match (ex: `match_900000000`).
- [x] Rulez `POST /rag/query` cu 3 intrebari tactice:
  - [x] "Care au fost principalele riscuri tactice?"
  - [x] "Ce jucatori trebuie prioritizati si de ce?"
  - [x] "Ce focus de antrenament recomanzi pentru build-up?"
- [x] Validez:
  - [x] `answer` non-empty
  - [x] `retrievedCount > 0`
  - [x] `sources` prezente, cu `docId` reale
  - [x] latenta rezonabila local
- [x] Rulez `POST /rag/query/debug` si verific contextul construit.

Done cand:
- 3/3 query-uri trec cu raspuns util + surse valide.

---

## 11. Definition of Done (MVP RAG)

- [x] Query service live local
- [x] Retrieval functional din FAISS per match
- [ ] Raspuns LLM grounded in surse
- [x] Endpoint debug pentru inspectie
- [x] Smoke test trecut
- [x] README cu instructiuni de rulare/demo

---

## 12. Backlog dupa MVP

- [ ] Hybrid retrieval (dense + sparse/BM25)
- [ ] reranker dedicat
- [ ] query rewriting
- [ ] multi-match comparative QA
- [ ] evaluare automata calitate raspunsuri
- [ ] observability (metrics/traces) + dashboard
