# RAG Club Knowledge - Implementation TODO

Acest fisier este roadmap-ul executabil pentru integrarea cunostintelor statice din `ANALIZA SPORTIVA.pdf` in pipeline-ul RAG existent.

Status global: `IN PROGRES`
Data start: `2026-04-25`

## Cum actualizam acest TODO

- `[ ]` neinceput
- `[~]` in progres
- `[x]` finalizat
- Dupa fiecare implementare, actualizam:
1. status task
2. data la `Update log`
3. eventuale decizii tehnice

## Faza 0 - Pregatire si decizii de design

- [x] Definim roadmap tehnic unificat in acest fisier.
- [x] Confirmam strategia pentru `matchId` in documentele statice:
  - optiune A: permitem `matchId=null` in schema `RagDocument`
  - optiune B: pastram `matchId` obligatoriu si folosim index separat cu schema proprie
- [x] Stabilim identificatorul clubului (`clubId`/`teamId`) si naming pentru colectia statica (ex: `club_knowledge_u_cluj`).
- [x] Confirmam formatul de citare sursa in raspuns (`source`, `page`, `section`).

Definition of done Faza 0:
- decizie documentata pentru schema si storage layout.

## Faza 1 - Ingestie PDF -> documente statice

- [x] Adaugam serviciu de extractie text din `ANALIZA SPORTIVA.pdf`.
- [~] Definim segmentarea pe unitati semantice:
  - philosophy overview
  - game phases
  - tactical principles (build-up, pressing, transition etc.)
  - player role profiles
- [x] Implementam parser/normalizer JSON intermediar pentru continut static.
- [x] Introducem metadate obligatorii:
  - `source: "pdf"`
  - `page`
  - `section`
  - `clubId`/`teamId`
- [x] Adaugam validari pentru documente goale sau duplicate.

Definition of done Faza 1:
- putem transforma PDF-ul in lista valida de documente statice.

## Faza 2 - Builder nou pentru club knowledge

- [x] Cream `app/builders/club_knowledge_builder.py`.
- [x] Builder-ul emite document types:
  - `club_philosophy`
  - `game_phase`
  - `tactical_principle`
  - `player_role_profile`
- [x] Definim conventii `docId` stabile (ex: `u_cluj_principle_build_up`).
- [x] Introducem teste unitare pentru builder (cazuri minime + edge cases).

Definition of done Faza 2:
- builder-ul produce documente curate, coerente, cu `metadata` completa.

## Faza 3 - Indexare statica in FAISS separat

- [x] Extindem vector store pentru colectii non-match:
  - layout tinta: `storage/vector_store/club_knowledge_<clubKey>/`
- [x] Adaugam API pentru indexare club knowledge (ex: `POST /index/club`).
- [x] Refolosim `EmbeddingService` pentru documentele statice.
- [x] Persistam `index.faiss` + `documents.json` pentru colectia statica.
- [x] Adaugam endpoint de listare colectii statice.

Definition of done Faza 3:
- exista index FAISS separat pentru club knowledge si este interogabil.

## Faza 4 - Dual retrieval (match + club)

- [x] Extindem `RetrievalService` pentru query in 2 surse:
  - colectia meciului (`match_<id>`)
  - colectia statica (`club_knowledge_<clubKey>`)
- [x] Implementam strategia de merge/ranking:
  - topK dinamic
  - topK static
  - scor final combinat
- [x] Pastram filtrele existente (`teamId`, `documentTypes`, `minScore`) si pentru static unde are sens.
- [x] Deducem si eliminam duplicatele dupa `docId`.
- [x] Adaugam warnings clare cand lipseste una dintre colectii.

Definition of done Faza 4:
- query-ul returneaza dovezi mixte (match + club) in mod stabil.

## Faza 5 - Context + Prompting pentru WHY

- [x] Adaptam `ContextService` sa marcheze explicit sursa:
  - `source_scope=match` vs `source_scope=club`
- [x] Updatam prompt-ul (`app/prompts/answer_prompt.txt`) cu regula:
  - match docs => WHAT happened
  - club docs => WHY it matters (principii/filozofie)
- [x] Cerem citari explicite in raspuns (docId, title, page daca exista).
- [x] Verificam ca fallback template ramane functional fara OpenAI.

Definition of done Faza 5:
- raspunsurile explica atat evenimentul, cat si relevanta tactica fata de filozofia clubului.

## Faza 6 - API, contracte, observabilitate

- [x] Extindem schema request pentru query cu identificator club (`clubKey` sau `teamId` mapat).
- [x] Updatam endpointul `/rag/query/debug` cu vizibilitate pe surse dinamice/statice.
- [x] Adaugam metrici minime in log:
  - retrieved_dynamic_count
  - retrieved_static_count
  - merged_count
  - latency per etapa
- [x] Actualizam `README.md` cu noul flow de integrare.

Definition of done Faza 6:
- contractul API este clar si debuggable end-to-end.

## Faza 7 - Testing, demo, acceptanta

- [x] Test indexare club knowledge din PDF real.
- [x] Test dual retrieval pe intrebari cheie:
  - "Why is build-up instability important?"
  - "What principle is affected by ball loss?"
  - "Why does player X need support?"
- [x] Verificam surse citate corect in output.
- [x] Smoke test complet:
  - index match
  - index club
  - rag query combinat
- [x] Pregatim payload demo pentru prezentare.

Definition of done Faza 7:
- functionalitate validata pe scenarii reale si demo reproductibil.

## Riscuri / blocaje anticipate

- Extragera textului din PDF poate necesita OCR sau curatare suplimentara.
- Schema actuala `RagDocument` cere `matchId > 0`; pentru static trebuie decizie clara.
- Ranking mixt dynamic/static poate necesita tuning de scoruri.
- Calitatea citarilor depinde de granularitatea chunking-ului si metadatelor de pagina.

## Update log

- 2026-04-25: creat TODO executabil si structurat pe faze (acest document).
- 2026-04-25: implementat primul increment end-to-end: indexare club din PDF, colectii FAISS `club_knowledge_*`, endpointuri noi de indexing/listare, dual retrieval match+club si update prompt/context.
- 2026-04-25: adaugat observabilitate pe etape in `QueryService` (embed/retrieval/context/llm + counts dynamic/static/merged), citari explicite in raspuns (`Surse utilizate`), teste unitare pentru builder/fallback/citations si validare pe PDF real.
- 2026-04-25: adaugat `smoke_test_club_rag.py`, validat cele 3 intrebari cheie WHY, confirmat surse mixte match+club si pregatite payload-uri demo (`demo_index_club_payload.json`, `demo_rag_club_query_payload.json`).
