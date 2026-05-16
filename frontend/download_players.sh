#!/bin/bash
mkdir -p public/players

declare -A PLAYERS
PLAYERS[559470]="Alessandro_Murgia"
PLAYERS[2086370]="Alex_Orban"
PLAYERS[1477485]="Alexandru_Bota"
PLAYERS[44435]="Alexandru_Chipciu"
PLAYERS[1426614]="Alin_Chintes"
PLAYERS[110210]="Alin_Tosca"
PLAYERS[1113174]="Andrei_Gheorghita"
PLAYERS[824206]="Andrej_Fabry"
PLAYERS[1907275]="Atanas_Trica"
PLAYERS[93842]="Dan_Nistor"
PLAYERS[245249]="Dino_Mikanovic"
PLAYERS[946446]="Dorin_Codrea"
PLAYERS[284355]="Elio_Capradossi"
PLAYERS[849788]="Gabriel_Simion"
PLAYERS[1101188]="Issouf_Macalou"
PLAYERS[578526]="Iulian_Cristea"
PLAYERS[925011]="Jasper_van_der_Werff"
PLAYERS[1005396]="Jonathan_Cisse"
PLAYERS[927797]="Jovo_Lukic"
PLAYERS[1152491]="Matei_Moraru"
PLAYERS[914160]="Miguel_Munoz"
PLAYERS[1085101]="Mouhamadou_Drammeh"
PLAYERS[1146209]="Omar_El_Sawy"
PLAYERS[812807]="Ovidiu_Bic"
PLAYERS[2430478]="Taiwo_Quadri"
PLAYERS[901913]="Virgiliu_Postolachi"

for ID in "${!PLAYERS[@]}"; do
  NAME=${PLAYERS[$ID]}
  FILE="public/players/${ID}.png"
  if [ ! -f "$FILE" ]; then
    echo "Downloading $NAME ($ID)..."
    curl -s -L \
      -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36" \
      -H "Referer: https://www.sofascore.com/" \
      "https://api.sofascore.com/api/v1/player/${ID}/image" \
      -o "$FILE"
    sleep 0.5
  else
    echo "Already exists: $NAME"
  fi
done

echo "Done! Check public/players/"
