# 📊 Wyscout API v3 – Endpointuri + Payload Examples

---

## ⚽ 1. Match Events
### `GET /matches/{wyId}/events`

### 📦 Description
Returnează toate evenimentele dintr-un meci (pase, șuturi, dueluri etc.)

### 🧾 Example Response
```json
{
  "elements": [
    {
      "match": {
        "id": 2852835,
        "date": "2024-03-10"
      },
      "teams": {
        "3185": { "name": "Torino" },
        "3166": { "name": "Bologna" }
      },
      "players": {
        "21123": { "name": "S. Verdi" }
      },
      "events": [
        {
          "id": 663292348,
          "matchId": 2852835,
          "matchPeriod": "1H",
          "minute": 0,
          "second": 1,
          "type": {
            "primary": "pass",
            "secondary": ["short_pass"]
          },
          "location": { "x": 52, "y": 47 },
          "team": { "id": 3185, "name": "Torino" },
          "player": { "id": 21123, "name": "S. Verdi" },
          "pass": {
            "accurate": false,
            "length": 13.2,
            "endLocation": { "x": 60, "y": 32 }
          }
        }
      ]
    }
  ],
  "meta": {
    "total": 1
  }
}
```

---

## 🏟️ 2. Match Info
### `GET /matches/{wyId}`

```json
{
  "matchId": 2852835,
  "date": "2024-03-10",
  "competition": {
    "id": 28,
    "name": "Serie A"
  },
  "teams": [
    {
      "teamId": 3185,
      "name": "Torino",
      "score": 1
    },
    {
      "teamId": 3166,
      "name": "Bologna",
      "score": 2
    }
  ],
  "status": "played"
}
```

---

## 📋 3. Matches List
### `GET /matches`

```json
{
  "matches": [
    {
      "matchId": 2852835,
      "date": "2024-03-10",
      "competitionId": 28,
      "teams": [
        { "teamId": 3185, "name": "Torino" },
        { "teamId": 3166, "name": "Bologna" }
      ]
    }
  ],
  "meta": {
    "total": 1
  }
}
```

---

## 🏆 4. Competitions
### `GET /competitions`

```json
{
  "competitions": [
    {
      "id": 28,
      "name": "Serie A",
      "area": {
        "name": "Italy"
      },
      "type": "league"
    }
  ]
}
```

---

## 🏟️ 5. Teams
### `GET /teams`

```json
{
  "teams": [
    {
      "id": 3185,
      "name": "Torino",
      "area": {
        "name": "Italy"
      }
    }
  ]
}
```

---

## 👤 6. Players
### `GET /players`

```json
{
  "players": [
    {
      "id": 21123,
      "name": "S. Verdi",
      "position": "CF",
      "teamId": 3185,
      "nationality": "Italy"
    }
  ]
}
```

---

## 📊 7. Player Matches / Stats
### `GET /players/{wyId}/matches`

```json
{
  "playerId": 21123,
  "matches": [
    {
      "matchId": 2852835,
      "minutesPlayed": 90,
      "goals": 1,
      "assists": 0,
      "shots": 3
    }
  ]
}
```

---

## 📈 8. Team Matches
### `GET /teams/{wyId}/matches`

```json
{
  "teamId": 3185,
  "matches": [
    {
      "matchId": 2852835,
      "opponentId": 3166,
      "score": "1-2",
      "date": "2024-03-10"
    }
  ]
}
```

---

## 🔄 9. Updated Objects
### `GET /updatedobjects`

```json
{
  "updatedObjects": [
    {
      "id": 2852835,
      "type": "match",
      "updatedAt": "2026-04-20T10:00:00Z"
    }
  ]
}
```

---

# 🧠 Notes utile
- `wyId` = ID intern Wyscout  
- toate răspunsurile sunt JSON  
- endpointul IMPORTANT:  
  👉 `/matches/{wyId}/events` (data brută pentru analiză)