# RAG Document & Embeddings Pipeline - Implementation Roadmap

## 0. Context

Aplicatia aceasta este un microserviciu nou care NU face inca RAG complet.

Scopul ei este sa transforme outputurile JSON produse de modelele existente in documente text human-readable si apoi in embeddings cautabile.

Pipeline curent de implementat:

```text
1. Primeste outputurile JSON de la microservicii
2. Document Builder transforma JSON -> documente text
3. Face embeddings pe documente
4. Le salveaza in FAISS / Chroma
```

RAG / LLM answering vine ulterior.

---

# 1. Obiectivul aplicatiei

Construim un serviciu Python/FastAPI numit:

```text
tactical-rag-indexer-service
```

Rolul serviciului:

```text
- primeste outputuri JSON de la microserviciile ML
- valideaza schema de input
- extrage informatiile importante
- construieste documente text clare
- adauga metadata structurata
- genereaza embeddings
- salveaza documentele in vector store
```

Output-ul acestui serviciu NU este inca un raspuns conversational.

Output-ul este:

```json
{
  "matchId": 99042601,
  "documentsCreated": 18,
  "embeddingsCreated": 18,
  "vectorStore": "faiss",
  "status": "indexed"
}
```

---

# 2. De ce NU facem embeddings pe JSON brut

Nu indexam raw JSON.

Motiv:

```text
JSON-ul contine structura, metrici, campuri si liste.
Embedding-urile functioneaza mai bine pe text semantic.
```

Corect:

```text
JSON -> structured facts -> human-readable text document -> embedding
```

Gresit:

```text
raw JSON -> embedding
```

---

# 3. Inputurile existente de la microservicii

Aplicatia de indexare va primi outputurile deja generate de modelele existente.

---

## 3.1 Tactical Fusion Aggregator Output

Microserviciu:

```text
tactical-fusion-service
```

Rol:

```text
Combina Tactical Baseline + Decision Quality si produce insight-uri tactice finale.
```

Campuri importante:

```text
fusionOutput.combinedInsights[]
fusionOutput.playerPriorities[]
fusionOutput.trainingFocus[]
frontendOutput.headline
frontendOutput.topProblems[]
frontendOutput.recommendations[]
meta.baselineSignals
meta.decisionSignals
meta.fusedCategories
```

Ce documente construim din el:

```text
- match_fusion_summary
- tactical_insight per combinedInsight
- player_priority per playerPriority
- training_focus per trainingFocus
- frontend_summary
```

---

## 3.2 Tactical Intelligence / Tactical Baseline Output

Microserviciu:

```text
tactical-baseline-service
```

Rol:

```text
Compara echipa cu baseline-ul Superliga si detecteaza slabiciuni macro.
```

Campuri importante:

```text
matchId
teamId
teamName
baselineModel.overallWeaknessScore
baselineModel.riskLevel
baselineModel.tacticalProfile
baselineModel.clusterId
baselineModel.anomalyScore
baselineModel.isAnomalous
weaknessSignals[]
metricComparisons{}
```

Ce documente construim din el:

```text
- baseline_summary
- baseline_weakness_signal per weaknessSignal
- metric_comparison_summary
- tactical_profile_document
- anomaly_document
```

---

## 3.3 Decision Quality Output

Microserviciu:

```text
decision-quality-service
```

Rol:

```text
Evalueaza calitatea deciziilor jucatorilor pe actiuni: pass, shot, carry.
```

Campuri importante:

```text
match
summary.actionsAnalyzed
summary.averageDecisionValue
summary.lowDecisionPhases
summary.phasesWithAlternative
summary.missedShotOrGoalOpportunities
players.needsSupport[]
players.underperformers[]
phases.improvablePhases[]
phases.missedShotOrGoalOpportunities[]
teamStats.decisionByType[]
teamStats.timeline[]
```

Ce documente construim din el:

```text
- decision_quality_summary
- player_decision_profile per needsSupport / underperformer
- improvable_phase per top N improvablePhases
- missed_opportunity per missedShotOrGoalOpportunities
- decision_by_type_summary
- decision_timeline_summary
```

---

## 3.4 Player Profile Output

Microserviciu:

```text
player-profile-service
```

Rol:

```text
Descrie profilul spatial al unui jucator: heatmap, zone, flancuri, receptii.
```

Campuri importante:

```text
match_id
period
player.id
player.name
player.position
team.id
team.name
grid.cols
grid.rows
grid.cells
stats.total_touches
stats.avg_x
stats.avg_y
stats.zones.def_third
stats.zones.mid_third
stats.zones.att_third
stats.flanks.left
stats.flanks.center
stats.flanks.right
stats.receptions
```

Ce documente construim din el:

```text
- player_movement_profile
- player_heatmap_summary
- player_role_interpretation
```

---

## 3.5 Pressing Output

Microserviciu:

```text
pressing-intensity-service
```

Rol:

```text
Evalueaza eficienta pressingului si jucatorii implicati.
```

Campuri importante:

```text
match_id
team_id
period
teamPressingEfficiency
firstHalfEfficiency
secondHalfEfficiency
intensityDrop
insight
players[]
topPresser
```

Player fields:

```text
id
name
position
pressingDuels
won
efficiency
inOpponentHalf
intensityDrop
```

Ce documente construim din el:

```text
- pressing_summary
- pressing_player_profile per top/worst relevant players
- pressing_timeline_summary
```

---

## 3.6 Passing Network Output

Microserviciu:

```text
passing-network-service
```

Rol:

```text
Descrie reteaua de pase intre jucatori.
```

Campuri importante:

```text
match_id
team.id
team.name
period
cutoff_minute
nodes[]
edges[]
```

Node fields:

```text
id
name
position
x
y
touches
```

Edge fields:

```text
source
target
weight
```

Ce documente construim din el:

```text
- passing_network_summary
- passing_hubs_summary
- passing_connections_summary
- isolated_players_summary
- flank_usage_summary
```

---

# 4. Arhitectura microserviciului nou

## 4.1 Nume recomandat

```text
tactical-rag-indexer-service
```

## 4.2 Responsabilitati

```text
- input validation
- document building
- embedding generation
- vector store persistence
- indexing status
```

## 4.3 Ce NU face acest serviciu acum

```text
- nu raspunde la intrebari
- nu face LLM reasoning
- nu face retrieval conversational
- nu inlocuieste modelele ML
```

---

# 5. Structura proiectului

Recomandare pentru un serviciu FastAPI de senior engineer:

```text
tactical-rag-indexer-service/
  app/
    main.py

    api/
      routes_indexing.py
      routes_health.py

    core/
      config.py
      logging.py
      errors.py

    schemas/
      input_bundle.py
      documents.py
      indexing.py

    services/
      document_builder_service.py
      embedding_service.py
      vector_store_service.py
      indexing_service.py

    builders/
      fusion_builder.py
      tactical_baseline_builder.py
      decision_quality_builder.py
      player_profile_builder.py
      pressing_builder.py
      passing_network_builder.py

    vectorstores/
      faiss_store.py
      chroma_store.py

    utils/
      text_formatting.py
      ids.py
      safe_get.py
      numeric.py

  tests/
    test_document_builder.py
    test_fusion_builder.py
    test_decision_builder.py
    test_embedding_service.py
    test_vector_store.py

  requirements.txt
  README.md
```

---

# 6. Input contract pentru serviciul nou

Endpoint-ul principal primeste un bundle cu toate outputurile existente.

## 6.1 Endpoint

```http
POST /index/match
```

## 6.2 Request body

```json
{
  "matchId": 99042601,
  "teamId": 9001,
  "teamName": "FC Universitatea Cluj",
  "source": "generated_models",
  "outputs": {
    "fusion": {},
    "tacticalBaseline": {},
    "decisionQuality": {},
    "playerProfiles": [],
    "pressing": {},
    "passingNetwork": {}
  },
  "options": {
    "vectorStore": "faiss",
    "rebuild": true,
    "topNPhases": 10,
    "includeDebugDocuments": false
  }
}
```

## 6.3 Optional inputs

Unele microservicii pot lipsi.

Regula:

```text
Daca un output lipseste, indexerul continua cu ce are.
Returneaza warning in response.
```

Exemplu:

```json
{
  "warnings": [
    "passingNetwork output missing",
    "playerProfiles output missing"
  ]
}
```

---

# 7. Output contract pentru serviciul nou

## 7.1 Response body

```json
{
  "matchId": 99042601,
  "teamId": 9001,
  "teamName": "FC Universitatea Cluj",
  "status": "indexed",
  "documentsCreated": 24,
  "embeddingsCreated": 24,
  "vectorStore": "faiss",
  "collectionName": "match_99042601",
  "documentTypes": {
    "match_summary": 1,
    "tactical_insight": 5,
    "player_priority": 5,
    "training_focus": 3,
    "decision_quality_summary": 1,
    "player_decision_quality": 4,
    "pressing_summary": 1,
    "passing_network_summary": 1,
    "player_movement_profile": 3
  },
  "warnings": [],
  "documentPreview": [
    {
      "docId": "match_99042601_fusion_summary",
      "type": "match_summary",
      "textPreview": "In match 99042601, U Cluj's main tactical risk was build-up instability..."
    }
  ]
}
```

---

# 8. Canonical document schema

Toate documentele generate trebuie sa aiba aceeasi schema.

```json
{
  "docId": "match_99042601_insight_build_up",
  "matchId": 99042601,
  "teamId": 9001,
  "teamName": "FC Universitatea Cluj",
  "sourceService": "tactical-fusion-service",
  "documentType": "tactical_insight",
  "category": "build_up",
  "title": "Critical build-up instability",
  "text": "U Cluj had a critical build-up problem...",
  "metadata": {
    "severity": "critical",
    "score": 0.8773,
    "confidence": 0.95,
    "players": ["A. Gorcea", "A. Miron"],
    "tags": ["build_up", "critical", "decision_quality"],
    "minute": null,
    "eventId": null
  }
}
```

## 8.1 Required fields

```text
docId
matchId
sourceService
documentType
text
metadata
```

## 8.2 Recommended metadata

```text
teamId
teamName
category
severity
score
confidence
players
tags
minute
eventId
period
sourceIds
```

---

# 9. Document types to generate

## 9.1 From Tactical Fusion

### A. match_summary

Source:

```text
frontendOutput.headline
fusionOutput.combinedInsights
fusionOutput.trainingFocus
```

Example text:

```text
In match 99042601, FC Universitatea Cluj's main tactical risk was build-up instability. The fusion model identified critical risk in build-up, medium risk in ball retention, and low risk in pressing. Main recommendation: train press-resistant passing triangles and own-half exit patterns.
```

### B. tactical_insight

One document per `combinedInsight`.

Example text:

```text
U Cluj had a critical build-up issue. Build-up actions were unstable and reduced controlled progression. The affected players were A. Gorcea, L. Cristea, A. Miron and D. Popa. Evidence includes low progressive pass success, low success entering the final third, improvable phases, low decision phases and players needing support. Recommendation: train press-resistant passing triangles with one-touch escape patterns.
```

### C. player_priority

One document per `playerPriorities`.

Example text:

```text
A. Miron is a priority player for review. Priority score: 0.6669. Reasons: improvable phase and player needs support. Focus categories: build-up and final third. Recommended action: review build-up decisions under pressure.
```

### D. training_focus

One document per training focus.

Example text:

```text
Training focus: build-up. Priority: critical. Objective: increase pass security under pressure. Recommended drill: 6v4 build-up under press with mandatory support angles.
```

---

## 9.2 From Tactical Baseline

### A. baseline_summary

Example text:

```text
The tactical baseline model rated U Cluj with an overall weakness score of 0.75 and medium-high risk level. The tactical profile was high-loss low-control. The match was anomalous compared to the Superliga baseline.
```

### B. baseline_weakness_signal

One document per weakness signal.

Example text:

```text
U Cluj showed a high build-up weakness in progressive pass success. Progressive pass success was 0.3913 compared to the league average of 0.6908. The z-score was -2.8062 and percentile was 0.72, indicating a very poor result compared to Superliga baseline.
```

### C. metric_comparison_summary

One aggregated document for key metrics.

Example text:

```text
U Cluj was very weak in pass success, progressive pass success, final third pass success and forward pass success. The team was also very weak in loss rate, with a value of 0.3753 compared to league average 0.1871.
```

### D. tactical_profile_document

Example text:

```text
U Cluj's tactical profile was high-loss low-control. This means the team combined poor ball retention with weak control in possession and build-up progression.
```

---

## 9.3 From Decision Quality

### A. decision_quality_summary

Example text:

```text
The Decision Quality model analyzed 333 actions from 11 U Cluj players. The average decision value was 0.2138. The model found 85 low-decision phases, 14 phases with better alternatives and 5 missed shot or goal opportunities.
```

### B. player_decision_quality

One document per `players.needsSupport` and top underperformers.

Example text:

```text
A. Gorcea had a low decision score of 0.137 across 12 analyzed actions. He had 8 low-score actions and needs decision support. His weak decision type was pass. When his decisions were low-value, the model recommended carry.
```

### C. improvable_phase

One document per top N `improvablePhases`.

Example text:

```text
At minute 44:54, A. Gorcea made a pass with decision value 0.112. The model suggested carry as a better alternative with value 0.1593, giving a potential gain of 0.0473.
```

### D. missed_opportunity

One document per top N `missedShotOrGoalOpportunities`.

Example text:

```text
At minute 22:59, D. Oancea made a pass with decision value 0.3554. The model identified a potential missed shot or goal opportunity, with carry as the best decision type and potential gain 0.0434.
```

### E. decision_timeline_summary

Example text:

```text
Decision quality declined after halftime. Between minutes 45-59, average decision value was 0.1973 with 18 low-decision phases. Between minutes 60-74, average decision value was 0.1913 with 17 low-decision phases.
```

---

## 9.4 From Player Profile

### A. player_movement_profile

Example text:

```text
D. Popa played mostly in advanced central areas. He had 71 touches, with average location x=72.86 and y=45.52. He had 51 touches in the attacking third and 20 in the middle third. His activity was heavily central, with 58 central touches, 10 left touches and 3 right touches.
```

### B. player_role_interpretation

Optional.

Example text:

```text
D. Popa's movement profile suggests an advanced central attacking midfielder role, with most touches in the attacking third and central lanes.
```

---

## 9.5 From Pressing

### A. pressing_summary

Example text:

```text
U Cluj pressing efficiency was 0.49. First-half efficiency was 0.47 and second-half efficiency improved to 0.52. The model concluded that pressing was largely ineffective but improved in the second half. Top presser was D. Oancea.
```

### B. pressing_player_profile

One document for top pressers and weak pressers.

Example text:

```text
D. Oancea was the top presser with 6 pressing duels, 4 won and efficiency 0.67. He had no pressing actions in the opponent half.
```

---

## 9.6 From Passing Network

### A. passing_network_summary

Example text:

```text
The passing network represents team chemistry through player nodes and pass edges. Nodes show player average positions and touches, while edges show pass frequency between players.
```

### B. passing_hubs_summary

Example text:

```text
The main passing hubs were identified by touch volume and central network connections. These players are important for ball circulation and build-up stability.
```

### C. isolated_players_summary

Example text:

```text
Players with low touches or weak network connections may be isolated from build-up. Isolated attackers can indicate poor service into advanced zones.
```

---

# 10. Document Builder rules

## 10.1 Deterministic first

Document Builder should be mostly deterministic.

Recommended:

```text
facts from JSON -> templates -> text
```

Not recommended:

```text
raw JSON -> LLM decides what matters
```

Reason:

```text
LLM can omit, distort or invent details.
```

Optional later:

```text
deterministic facts -> LLM rewrite for nicer language
```

## 10.2 Keep numbers in text

Documents should include important numbers.

Good:

```text
Progressive pass success was 0.3913 compared to league average 0.6908.
```

Bad:

```text
Progressive pass success was poor.
```

## 10.3 Include tactical category

Every document should include category where possible:

```text
build_up
ball_loss
pressing
final_third
progression
duels
player_profile
passing_network
```

## 10.4 Limit document size

Recommended:

```text
100-250 words per document
```

Do not create huge documents.

---

# 11. Embedding strategy

## 11.1 What to embed

Embed only:

```text
document.text
```

Optionally append metadata into text:

```text
Category: build_up. Severity: critical. Text: ...
```

Recommended embedding text format:

```text
Title: Critical build-up instability
Type: tactical_insight
Category: build_up
Players: A. Gorcea, A. Miron
Text: U Cluj had a critical build-up problem...
```

## 11.2 What NOT to embed

Do not embed:

```text
raw JSON
full grid matrices
full node-edge graph JSON
very long event lists
debug metadata
```

## 11.3 Embedding model

For hackathon / local:

```text
sentence-transformers/all-MiniLM-L6-v2
```

Pros:

```text
local
free
fast
good enough
```

Alternative:

```text
OpenAI text-embedding-3-small
```

Pros:

```text
better quality
simple API
```

Cons:

```text
needs API key
cost
internet dependency
```

Recommendation:

```text
Use sentence-transformers locally for MVP.
```

---

# 12. Vector store strategy

## 12.1 Recommended for MVP

```text
FAISS
```

Pros:

```text
simple
local
fast
no server needed
```

Cons:

```text
metadata persistence must be handled manually
```

## 12.2 Alternative

```text
Chroma
```

Pros:

```text
metadata support easier
collections easier
```

Cons:

```text
slightly more moving parts
```

## 12.3 Recommendation

For fastest implementation:

```text
FAISS + documents.json metadata sidecar
```

Files:

```text
storage/
  match_99042601/
    index.faiss
    documents.json
```

---

# 13. Storage design

## 13.1 Per-match index

Recommended for MVP:

```text
one vector index per match
```

Example:

```text
storage/vector_store/match_99042601/index.faiss
storage/vector_store/match_99042601/documents.json
```

Pros:

```text
easy to delete/rebuild
easy to query per match
simple for demo
```

## 13.2 Global index

Later:

```text
one global index for all matches
```

Use when you want questions like:

```text
Compare this match with previous U Cluj matches.
```

Not needed now.

---

# 14. API design

## 14.1 Health endpoint

```http
GET /health
```

Response:

```json
{
  "status": "ok",
  "service": "tactical-rag-indexer-service"
}
```

## 14.2 Build documents only

Useful for debugging.

```http
POST /documents/build
```

Response:

```json
{
  "matchId": 99042601,
  "documentsCreated": 24,
  "documents": [
    {
      "docId": "match_99042601_fusion_summary",
      "documentType": "match_summary",
      "text": "..."
    }
  ]
}
```

## 14.3 Index match

```http
POST /index/match
```

Response:

```json
{
  "matchId": 99042601,
  "status": "indexed",
  "documentsCreated": 24,
  "embeddingsCreated": 24,
  "collectionName": "match_99042601"
}
```

## 14.4 List indexed matches

```http
GET /index/matches
```

## 14.5 Document preview

```http
GET /index/matches/{matchId}/documents
```

---

# 15. Implementation order

## Phase 1 - Contracts and models

Build:

```text
schemas/input_bundle.py
schemas/documents.py
schemas/indexing.py
```

Define:

```text
InputBundle
ModelOutputs
RagDocument
IndexRequest
IndexResponse
```

Acceptance criteria:

```text
- service accepts all current microservice outputs
- missing optional output does not crash
- invalid matchId returns validation error
```

---

## Phase 2 - Document Builder

Build:

```text
DocumentBuilderService
FusionDocumentBuilder
TacticalBaselineDocumentBuilder
DecisionQualityDocumentBuilder
PlayerProfileDocumentBuilder
PressingDocumentBuilder
PassingNetworkDocumentBuilder
```

Acceptance criteria:

```text
- each builder returns List[RagDocument]
- every document has stable docId
- every document has non-empty text
- every document has documentType and sourceService
```

---

## Phase 3 - Embedding Service

Build:

```text
EmbeddingService
```

Methods:

```python
embed_text(text: str) -> list[float]
embed_documents(documents: list[RagDocument]) -> list[EmbeddedDocument]
```

Acceptance criteria:

```text
- embedding dimension is consistent
- empty text is rejected
- batch embedding works
```

---

## Phase 4 - Vector Store Service

Build FAISS first.

Methods:

```python
save_match_index(match_id: int, embedded_documents: list[EmbeddedDocument])
load_match_index(match_id: int)
list_indexes()
delete_match_index(match_id: int)
```

Acceptance criteria:

```text
- index.faiss saved to disk
- documents.json saved to disk
- index can be reloaded after restart
```

---

## Phase 5 - API endpoints

Implement:

```text
GET /health
POST /documents/build
POST /index/match
GET /index/matches
GET /index/matches/{matchId}/documents
```

Acceptance criteria:

```text
- Java backend can call POST /index/match
- frontend/dev can preview generated docs
- response contains counts and warnings
```

---

## Phase 6 - Tests

Minimum tests:

```text
test_fusion_builder_creates_documents
test_baseline_builder_creates_signal_documents
test_decision_builder_creates_player_documents
test_player_profile_builder_creates_heatmap_summary
test_pressing_builder_creates_summary
test_passing_network_builder_creates_summary
test_embedding_dimensions
test_faiss_save_and_load
```

Acceptance criteria:

```text
- all tests pass locally
- deterministic docIds
- no duplicate docIds
```

---

# 16. Document ID strategy

Use deterministic IDs.

Format:

```text
match_{matchId}_{source}_{type}_{slug}
```

Examples:

```text
match_99042601_fusion_summary
match_99042601_fusion_insight_build_up
match_99042601_fusion_player_a_miron
match_99042601_decision_player_a_gorcea
match_99042601_pressing_summary
match_99042601_profile_d_popa
match_99042601_passing_network_summary
```

Why deterministic:

```text
- easy rebuild
- easy debugging
- easy source references later in RAG
```

---

# 17. Text generation templates

## 17.1 Fusion insight template

```text
{teamName} had a {severity} {category} issue. {message}
Affected players: {players}.
Evidence: {baselineSignals} and {decisionSignals}.
Recommendation: {recommendation}
```

## 17.2 Player priority template

```text
{player} is a priority player for review. Priority score: {priority_score}.
Reasons: {reasons}. Focus categories: {focus_categories}.
Recommended action: {recommendedAction}
```

## 17.3 Baseline signal template

```text
{teamName} showed a {severity} weakness in {metric}.
Value: {value}. League average: {leagueAverage}.
Z-score: {zScore}. Percentile: {percentile}.
This belongs to the {category} category.
```

## 17.4 Decision phase template

```text
At minute {minute}:{second}, {player_name} chose {decision}.
Decision value: {decisionValue}. Suggested alternative: {suggestedAlternative}.
Best decision type: {bestDecisionType}. Potential gain: {potentialGain}.
```

## 17.5 Player profile template

```text
{playerName} played as {position}. Total touches: {total_touches}.
Average location: x={avg_x}, y={avg_y}.
Touches by thirds: defensive {def_third}, middle {mid_third}, attacking {att_third}.
Flank usage: left {left}, center {center}, right {right}.
```

## 17.6 Pressing template

```text
{teamName} pressing efficiency was {teamPressingEfficiency}.
First half efficiency: {firstHalfEfficiency}. Second half efficiency: {secondHalfEfficiency}.
Insight: {insight}. Top presser: {topPresser}.
```

## 17.7 Passing network template

```text
The passing network for {teamName} contains {nodeCount} players and {edgeCount} connections.
Top touch players: {topPlayers}.
Strongest passing connections: {topEdges}.
This network can indicate hubs, isolated players and flank usage.
```

---

# 18. Metadata tags

Use tags to improve future retrieval filtering.

Recommended tags:

```text
match
team
build_up
ball_loss
progression
final_third
pressing
duels
player_profile
decision_quality
fusion
baseline
passing_network
training
priority_player
critical
high
medium
low
```

---

# 19. Error handling

## Missing service output

Behavior:

```text
continue indexing
add warning
```

## Malformed section

Behavior:

```text
skip that section
add warning with path
```

## Embedding failure

Behavior:

```text
fail request
return 500 with clear message
```

## Vector store save failure

Behavior:

```text
fail request
do not report indexed
```

---

# 20. Logging

Log important lifecycle events:

```text
received_index_request
documents_built
embeddings_created
vector_index_saved
index_request_failed
```

Include:

```text
matchId
teamId
documentCount
embeddingCount
durationMs
warningsCount
```

Do not log full raw JSON in production mode.

---

# 21. Configuration

Use environment variables:

```text
APP_ENV=dev
VECTOR_STORE=faiss
STORAGE_DIR=./storage/vector_store
EMBEDDING_PROVIDER=sentence_transformers
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
MAX_PHASE_DOCUMENTS=10
MAX_PLAYER_DOCUMENTS=10
```

---

# 22. Recommended dependencies

```text
fastapi
uvicorn
pydantic
sentence-transformers
faiss-cpu
numpy
python-slugify
orjson
pytest
```

Optional:

```text
chromadb
```

---

# 23. Java backend integration

Java backend role:

```text
- orchestrates Wyscout polling
- calls model microservices
- collects outputs
- sends output bundle to tactical-rag-indexer-service
```

Flow:

```text
Java Backend
  -> decision-quality-service
  -> tactical-baseline-service
  -> fusion-service
  -> player-profile-service
  -> pressing-service
  -> passing-network-service
  -> tactical-rag-indexer-service /index/match
```

---

# 24. What to show in demo for this service

Since RAG is later, demo this service by showing:

```text
1. raw model JSON outputs
2. generated human-readable documents
3. embeddings count
4. FAISS index saved
5. document preview endpoint
```

Example message:

```text
We convert structured ML outputs into a searchable tactical knowledge base per match.
```

This is a strong technical step toward:

```text
Ask the Match / AI Tactical Assistant
```

---

# 25. Definition of Done

The service is done when:

```text
- accepts a full match output bundle
- creates documents from all available microservice outputs
- each document has stable metadata
- creates embeddings for each document
- persists FAISS index and documents sidecar
- exposes document preview
- handles missing optional outputs
- has tests for all builders
```

---

# 26. Next step after this roadmap

After this service is ready, build the RAG query service:

```text
query -> embedding -> vector search -> retrieved docs -> LLM answer
```

That later service can use the same FAISS/Chroma index produced here.
