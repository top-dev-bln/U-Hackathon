# Tactical Intelligence Fusion - Implementation Roadmap

## Objective
Build one fusion pipeline that combines two inputs:
- `input1`: Tactical Baseline data
- `input2`: Decision Quality data

Output must explain:
- what is failing
- why it is failing
- who is impacted
- what action is recommended

## Input Contracts
Define and freeze schemas from day 1.

### input1 (Tactical Baseline)
- `baselineModel.overallWeaknessScore`
- `baselineModel.riskLevel`
- `baselineModel.tacticalProfile`
- `baselineModel.anomalyScore`
- `weaknessSignals[]`
- `metricComparisons{}`

### input2 (Decision Quality)
- `summary.averageDecisionValue`
- `summary.lowDecisionPhases`
- `summary.phasesWithAlternative`
- `players.needsSupport[]`
- `phases.improvablePhases[]`
- `phases.missedShotOrGoalOpportunities[]`
- `teamStats.decisionByType[]`
- `teamStats.timeline[]`

## Target Outputs

### Fusion output
```json
{
  "combinedInsights": [],
  "playerPriorities": [],
  "trainingFocus": []
}
```

### Frontend output
```json
{
  "headline": "...",
  "topProblems": [],
  "recommendations": []
}
```

## Implementation Phases (Execute Now)

### Phase 0 - Foundations
- Create module structure: `ingestion`, `normalization`, `fusion`, `insights`, `api`.
- Add JSON schema validation for `input1` and `input2`.
- Add typed domain models.

Deliverables:
- schema files
- validator functions
- sample payloads for both inputs

Acceptance:
- invalid payloads fail with explicit field errors

### Phase 1 - Normalization Layer
Normalize both inputs into one internal model:
```json
{
  "baselineSignals": [],
  "decisionSignals": []
}
```

- Map severity to a common numeric scale `[0..1]`.
- Normalize role names (GK/CB/LB/RB) and phase labels.
- Add fallback defaults for missing optional fields.

Deliverables:
- `normalizeInput1()`
- `normalizeInput2()`
- normalization tests

Acceptance:
- same tactical event maps consistently from both inputs

### Phase 2 - Taxonomy and Signal Generation
Define tactical categories:
- `build_up`
- `ball_loss`
- `progression`
- `final_third`
- `duels`
- `pressing`

Generate signals:
```json
{ "type": "ball_loss", "severity": 0.65 }
```
```json
{ "type": "ball_loss", "severity": 0.60, "players": ["Miron"] }
```

Deliverables:
- category mapper
- baseline signal generator
- decision signal generator

Acceptance:
- each source event produces exactly one valid category

### Phase 3 - Matching and Fusion Engine
Match signals by category and combine scores:
```text
combinedScore = 0.55 * baseline + 0.45 * decision
```

Initial mapping rules:
- `build_up`: progressive pass performance + low pass/carry decisions
- `ball_loss`: loss/dangerous loss + low decisions in defensive roles
- `final_third`: shot quality efficiency + bad shot decisions
- `duels`: duel success + support/training indicators
- `pressing`: high recoveries + counterpressing decision quality

Deliverables:
- matching engine
- weighted score calculator
- confidence score per insight

Acceptance:
- deterministic fusion for identical inputs

### Phase 4 - Insight Generation
Generate tactical insights from fused signals:
```json
{
  "type": "risky_build_up",
  "severity": "high",
  "message": "...",
  "recommendation": "..."
}
```

- Add severity bands (`low`, `medium`, `high`, `critical`).
- Add recommendation templates by category.
- Build player priority ranking:
  - low decision score
  - repeated involvement in weak phases

Deliverables:
- insight generator
- player priority engine
- training focus engine

Acceptance:
- every top problem has at least one actionable recommendation

### Phase 5 - API and Frontend Contract
- Expose one endpoint for fusion result.
- Add serializer for frontend payload (`headline`, `topProblems`, `recommendations`).
- Add versioning in response metadata.

Deliverables:
- endpoint `/fusion/analysis`
- response contract docs
- example responses

Acceptance:
- frontend can render output without extra transformation

### Phase 6 - Quality, Calibration, Release
- Unit tests for normalization, mapping, fusion formula.
- Integration tests with full `input1` + `input2` samples.
- Calibration pass on fusion weights and thresholds.
- Add logs/metrics:
  - invalid input rate
  - category distribution
  - high severity insight frequency

Deliverables:
- test suite
- calibration report
- rollout checklist

Acceptance:
- >=95% test pass on CI
- no schema-breaking responses

## Risks and Mitigations
- Risk: inconsistent category mapping across inputs.
  Mitigation: single taxonomy registry and strict mapping tests.
- Risk: noisy severity from sparse data.
  Mitigation: confidence score + minimum evidence threshold.
- Risk: recommendation quality too generic.
  Mitigation: category-specific templates + role-aware rules.

## Definition of Done (MVP)
- Two validated inputs (`input1`, `input2`) accepted.
- Normalized signals generated consistently.
- Fused scores produced per tactical category.
- Actionable insights, player priorities, and training focus returned.
- Frontend-ready payload delivered from one stable endpoint.
