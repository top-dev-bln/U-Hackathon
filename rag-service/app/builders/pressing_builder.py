from __future__ import annotations

from typing import Any

from app.builders.common import make_doc
from app.schemas.documents import RagDocument
from app.utils.numeric import fmt_float, to_float
from app.utils.safe_get import as_list
from app.utils.text_formatting import safe_text


class PressingDocumentBuilder:
    source_service = "pressing-intensity-service"

    def build(
        self,
        *,
        match_id: int,
        team_id: int | None,
        team_name: str | None,
        payload: dict[str, Any],
    ) -> tuple[list[RagDocument], list[str]]:
        warnings: list[str] = []
        docs: list[RagDocument] = []

        players = as_list(payload.get("players"))
        top_presser = safe_text(payload.get("topPresser"), "n/a")

        docs.append(
            make_doc(
                match_id=match_id,
                team_id=team_id or payload.get("team_id"),
                team_name=team_name,
                source_service=self.source_service,
                document_type="pressing_summary",
                slug="summary",
                title="Pressing summary",
                category="pressing",
                text=(
                    f"{safe_text(team_name, 'The team')} pressing efficiency was "
                    f"{fmt_float(payload.get('teamPressingEfficiency'), digits=2)}. "
                    f"First half efficiency: {fmt_float(payload.get('firstHalfEfficiency'), digits=2)}. "
                    f"Second half efficiency: {fmt_float(payload.get('secondHalfEfficiency'), digits=2)}. "
                    f"Intensity drop: {fmt_float(payload.get('intensityDrop'), digits=2)}. "
                    f"Insight: {safe_text(payload.get('insight'))}. Top presser: {top_presser}."
                ),
                metadata={
                    "teamPressingEfficiency": payload.get("teamPressingEfficiency"),
                    "firstHalfEfficiency": payload.get("firstHalfEfficiency"),
                    "secondHalfEfficiency": payload.get("secondHalfEfficiency"),
                    "topPresser": top_presser,
                    "tags": ["pressing", "summary"],
                },
            )
        )

        # Build player profiles for top and weak pressing contributors.
        players_with_duels = [p for p in players if to_float(p.get("pressingDuels"), 0.0) > 0]
        sorted_by_eff = sorted(players_with_duels, key=lambda p: to_float(p.get("efficiency"), 0.0), reverse=True)

        selected = sorted_by_eff[:3]
        weak = list(reversed(sorted_by_eff[-2:])) if len(sorted_by_eff) > 3 else []

        emitted_ids: set[int] = set()
        for row in selected + weak:
            player_id = int(row.get("id", -1))
            if player_id in emitted_ids:
                continue
            emitted_ids.add(player_id)
            player_name = safe_text(row.get("name"), "unknown_player")
            efficiency = to_float(row.get("efficiency"), 0.0)
            text = (
                f"{player_name} ({safe_text(row.get('position'))}) had {row.get('pressingDuels', 0)} pressing duels, "
                f"won {row.get('won', 0)}, efficiency {fmt_float(efficiency, digits=2)}. "
                f"Opponent-half pressing actions: {row.get('inOpponentHalf', 0)}. "
                f"Individual intensity drop: {fmt_float(row.get('intensityDrop'), digits=2)}."
            )
            docs.append(
                make_doc(
                    match_id=match_id,
                    team_id=team_id or payload.get("team_id"),
                    team_name=team_name,
                    source_service=self.source_service,
                    document_type="pressing_player_profile",
                    slug=player_name,
                    title=f"Pressing profile: {player_name}",
                    category="pressing",
                    text=text,
                    metadata={
                        "playerId": row.get("id"),
                        "player": player_name,
                        "efficiency": efficiency,
                        "pressingDuels": row.get("pressingDuels"),
                        "won": row.get("won"),
                        "tags": ["pressing", "player_profile"],
                    },
                )
            )

        docs.append(
            make_doc(
                match_id=match_id,
                team_id=team_id or payload.get("team_id"),
                team_name=team_name,
                source_service=self.source_service,
                document_type="pressing_timeline_summary",
                slug="timeline",
                title="Pressing timeline summary",
                category="pressing",
                text=(
                    f"Pressing trend in match {match_id}: first half "
                    f"{fmt_float(payload.get('firstHalfEfficiency'), digits=2)} and second half "
                    f"{fmt_float(payload.get('secondHalfEfficiency'), digits=2)}. "
                    f"Net intensity drop indicator: {fmt_float(payload.get('intensityDrop'), digits=2)}."
                ),
                metadata={"tags": ["pressing", "timeline"]},
            )
        )

        if not players:
            warnings.append("pressing.players missing or empty.")

        return docs, warnings

