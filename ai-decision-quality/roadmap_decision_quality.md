# Decision Quality Model - Roadmap

## Obiectiv

Construim un model care evalueaza cat de buna este decizia unui jucator intr-un context dat: pasa, sut sau carry/dribling.

Output final dorit:

```
{
  "player": "Popescu",
  "decisionScore": 0.72,
  "actionsAnalyzed": 48
}
```

---

## 1. Ce vrem sa prezica modelul

Modelul nu trebuie sa spuna daca o actiune este "frumoasa", ci daca acea actiune creste sansa ca atacul sa devina periculos.

Definitie simpla:

```
O decizie buna = o actiune care duce in urmatoarele secunde la:
- sut
- sut pe poarta
- gol
- intrare in zona periculoasa
- progresie clara spre poarta
```

Pentru MVP folosim regula:

```
label = 1 daca in urmatoarele 10 secunde apare un sut sau gol
label = 0 altfel
```

---

## 2. Date de intrare

Pornim de la date Wyscout-style:

```
GET /matches/{wyId}/events
```

Din fiecare event ne intereseaza:

```
event id
match id
team id
player id
player name
event type
minute
second
location x
location y
pass data
shot data
carry data
possession data
```

Pentru ML folosim in principal CSV-ul flat generat din JSON.

---

## 3. Dataset pentru ML

Fiecare rand din dataset reprezinta o actiune.

Pastram doar actiunile relevante:

```
pass
shot
carry
```

Nu folosim direct toate evenimentele, deoarece unele nu sunt decizii ofensive clare.

Excludem initial:

```
infraction
aerial_duel
ground_duel
goalkeeper_action
```

Acestea pot fi adaugate ulterior ca feature/context.

---

## 4. Preprocesare

### 4.1 Sortare temporala

Sortam evenimentele dupa:

```
match_id
minute
second
event_id
```

### 4.2 Timp absolut

Cream o coloana:

```
absolute_second = minute * 60 + second
```

Aceasta ajuta la gasirea evenimentelor care apar dupa actiunea curenta.

---

## 5. Feature engineering

### 5.1 Features de baza

```
event_type
player_position
minute
x
y
team_id
is_u_cluj
```

### 5.2 Features spatiale

```
distance_to_goal
angle_to_goal
zone_x
zone_y
is_final_third
is_box_entry_zone
```

Exemplu:

```
distance_to_goal = distanta dintre punctul actiunii si poarta adversa
```

### 5.3 Features pentru pasa

Doar pentru event_type = pass:

```
pass_length
pass_angle
pass_end_x
pass_end_y
is_forward_pass
is_progressive_pass
pass_accurate
```

Pentru alte tipuri de actiuni, aceste valori pot fi 0 sau null completat cu 0.

### 5.4 Features pentru carry/dribling

Doar pentru event_type = carry:

```
carry_end_x
carry_end_y
carry_progression
carry_length
```

### 5.5 Features pentru sut

Doar pentru event_type = shot:

```
shot_xg
shot_on_target
distance_to_goal
angle_to_goal
```

### 5.6 Context anterior

Adaugam informatii despre actiunea anterioara din aceeasi posesie sau acelasi meci:

```
previous_event_type
previous_x
previous_y
previous_player_position
previous_team_id
```

Pentru MVP, contextul anterior poate fi optional.

---

## 6. Label creation

Pentru fiecare actiune verificam ce se intampla dupa ea.

Regula MVP:

```
Pentru fiecare event:
  cautam evenimentele aceleiasi echipe
  din acelasi meci
  care apar in urmatoarele 10 secunde

Daca apare un shot sau goal:
  label = 1
Altfel:
  label = 0
```

Exemplu de rand final:

```
event_type,x,y,pass_length,is_forward_pass,progression,distance_to_goal,label
pass,52,47,13.2,1,8.0,48.3,1
pass,30,62,7.1,0,-2.0,72.5,0
carry,61,41,0,0,12.0,39.1,1
shot,88,50,0,0,0,12.0,0
```

---

## 7. Model ML

### Model recomandat pentru hackathon

```
RandomForestClassifier
```

De ce:

```
rapid
usor de antrenat
merge bine pe date tabulare
nu necesita mult tuning
poate returna probabilitati
```

Output-ul modelului:

```
probability = sansa ca actiunea sa duca la pericol
```

Aceasta probabilitate devine:

```
decision_value
```

---

## 8. Decision value

Pentru fiecare actiune:

```
decision_value = model.predict_proba(action_features)
```

Exemplu:

```
{
  "eventId": 880100234,
  "player": "D. Nistor",
  "decision": "pass",
  "decisionValue": 0.81
}
```

Interpretare:

```
0.81 = actiunea are sanse mari sa duca la o faza periculoasa
0.22 = actiunea are sanse mici sa duca la o faza periculoasa
```

---

## 9. Decision score pe jucator

Pentru fiecare jucator calculam media valorilor deciziilor sale.

Formula MVP:

```
decisionScore = media(decision_value pentru toate actiunile jucatorului)
```

Output:

```
{
  "playerId": 1007,
  "playerName": "D. Nistor",
  "decisionScore": 0.78,
  "actionsAnalyzed": 52
}
```

Putem adauga si:

```
bestDecisionType
worstDecisionType
dangerousActions
lowValueActions
```

---

## 10. Comparatie pasa vs sut vs carry

Aceasta este varianta advanced.

Pentru o actiune concreta, simulam alternative:

```
scenariu 1: playerul paseaza
scenariu 2: playerul suteaza
scenariu 3: playerul face carry
```

Modelul estimeaza valoarea fiecarei alternative.

Output posibil:

```
{
  "player": "D. Popa",
  "minute": 64,
  "actualDecision": "shot",
  "actualDecisionValue": 0.22,
  "alternatives": [
    {
      "decision": "pass",
      "predictedValue": 0.61
    },
    {
      "decision": "carry",
      "predictedValue": 0.44
    },
    {
      "decision": "shot",
      "predictedValue": 0.22
    }
  ],
  "insight": "A pass was likely a better decision than the shot."
}
```

Pentru hackathon, aceasta parte poate fi prezentata ca extensie, nu obligatoriu MVP.

---

## 11. Evaluare model

Metrici simple:

```
accuracy
precision
recall
f1-score
ROC AUC
confusion matrix
```

Foarte important:

```
Nu prezentam modelul ca fiind perfect.
Il prezentam ca prototip antrenat pe date Wyscout-style simulate.
```

---

## 12. Export rezultate

Dupa training exportam:

```
u_cluj_decision_quality_player_scores.csv
u_cluj_decision_quality_player_scores.json
u_cluj_decision_quality_event_predictions.csv
u_cluj_decision_quality_event_predictions.json
```

Aceste fisiere pot fi folosite de backend sau frontend.

---

## 13. Endpoint backend

Endpoint propus:

```
GET /api/matches/{matchId}/decision-quality
```

Response:

```
{
  "matchId": 99042601,
  "teamId": 9001,
  "players": [
    {
      "playerId": 1007,
      "playerName": "D. Nistor",
      "decisionScore": 0.78,
      "actionsAnalyzed": 52
    }
  ],
  "topDecisions": [
    {
      "minute": 34,
      "playerName": "D. Nistor",
      "decision": "pass",
      "decisionValue": 0.84,
      "result": "shot created"
    }
  ],
  "badDecisions": [
    {
      "minute": 67,
      "playerName": "D. Popa",
      "decision": "shot",
      "decisionValue": 0.19,
      "suggestedAlternative": "pass"
    }
  ]
}
```

---

## 14. Frontend

Ce afisam:

```
player cards cu decisionScore
top 5 best decisions
top 5 worst decisions
timeline cu actiuni importante
filtru pe meci
filtru pe jucator
```

Pentru demo:

```
verde = decizie buna
galben = decizie medie
rosu = decizie slaba
```

---

## 15. MVP pentru hackathon

### Must have

```
1. CSV cu features + label
2. RandomForest antrenat
3. decision_value pe fiecare actiune
4. decisionScore pe fiecare jucator
5. export JSON pentru frontend/backend
```

### Nice to have

```
1. alternative decisions: pass vs shot vs carry
2. explicatii automate
3. vizualizare pe teren
4. comparatie intre meciuri
```

---

## 16. Limitari

```
Datasetul este mock.
Label-ul este aproximativ.
Modelul nu intelege complet contextul tactic.
Nu avem tracking data real pentru pozitia adversarilor.
```

Aceste limitari sunt normale pentru un hackathon.

---

## 17. Cum prezentam proiectul

Pitch:

```
We built a Decision Quality Model that evaluates every offensive action by estimating how likely it is to create danger in the next phase of play.
```

Varianta in romana:

```
Am construit un model care analizeaza fiecare decizie ofensiva si estimeaza daca acea actiune creste probabilitatea ca atacul sa devina periculos.
```

---

## 18. Ordinea de lucru

```
1. Pregatim CSV-ul
2. Filtram pass / shot / carry
3. Cream features
4. Cream label
5. Antrenam RandomForest
6. Calculam decision_value
7. Agregam pe jucator
8. Exportam JSON
9. Integram in backend
10. Afisam in frontend
```

---

## 19. Rezultat final dorit

Output pe jucator:

```
{
  "player": "Popescu",
  "decisionScore": 0.72
}
```

Output extins:

```
{
  "playerId": 1009,
  "playerName": "D. Popa",
  "decisionScore": 0.72,
  "actionsAnalyzed": 44,
  "bestDecisionType": "progressive_pass",
  "weakDecisionType": "low_xg_shot"
}
```
