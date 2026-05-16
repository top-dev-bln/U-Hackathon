from __future__ import annotations

from typing import Any

from app.builders.common import make_doc
from app.schemas.documents import RagDocument
from app.utils.numeric import fmt_float, to_float
from app.utils.safe_get import as_list
from app.utils.text_formatting import safe_text, to_sentence


class BallLossesDocumentBuilder:
    source_service = "ball-losses-service"

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

        team = payload.get("team") or {}
        resolved_team_name = safe_text(team.get("name"), team_name or "unknown_team")
        by_zone = payload.get("by_zone") or {}
        by_type = payload.get("by_type") or {}
        by_player = as_list(payload.get("by_player"))
        events = as_list(payload.get("events"))
        grid = payload.get("grid") or {}

        docs.append(
            make_doc(
                match_id=match_id,
                team_id=team_id or team.get("id"),
                team_name=team_name or resolved_team_name,
                source_service=self.source_service,
                document_type="ball_losses_summary",
                slug="summary",
                title="Ball losses summary",
                category="ball_losses",
                text=(
                    f"Ball losses profile for {resolved_team_name} in match {match_id}: "
                    f"total losses {payload.get('total_losses', 0)} and danger score "
                    f"{fmt_float(payload.get('danger_score'), digits=3)}. "
                    f"By zone: defensive {by_zone.get('defensive_third', 0)}, "
                    f"middle {by_zone.get('middle_third', 0)}, attacking {by_zone.get('attacking_third', 0)}. "
                    f"By type: inaccurate pass {by_type.get('inaccurate_pass', 0)}, duel lost "
                    f"{by_type.get('duel_lost', 0)}, loss tag {by_type.get('loss_tag', 0)}."
                ),
                metadata={
                    "period": payload.get("period"),
                    "totalLosses": payload.get("total_losses"),
                    "dangerScore": payload.get("danger_score"),
                    "tags": ["ball_losses", "summary"],
                },
            )
        )

        players_sorted = sorted(
            by_player,
            key=lambda row: (to_float(row.get("dangerous_losses")), to_float(row.get("losses"))),
            reverse=True,
        )
        for row in players_sorted[:5]:
            player_name = safe_text(row.get("name"), "unknown_player")
            docs.append(
                make_doc(
                    match_id=match_id,
                    team_id=team_id or team.get("id"),
                    team_name=team_name or resolved_team_name,
                    source_service=self.source_service,
                    document_type="ball_loss_player_profile",
                    slug=player_name,
                    title=f"Ball loss profile: {player_name}",
                    category="ball_losses",
                    text=(
                        f"{player_name} recorded {row.get('losses', 0)} ball losses, including "
                        f"{row.get('dangerous_losses', 0)} dangerous losses. "
                        f"Position: {safe_text(row.get('position'))}."
                    ),
                    metadata={
                        "playerId": row.get("id"),
                        "player": player_name,
                        "position": row.get("position"),
                        "losses": row.get("losses"),
                        "dangerousLosses": row.get("dangerous_losses"),
                        "tags": ["ball_losses", "player_profile"],
                    },
                )
            )

        hot_cells = self._extract_hot_cells(as_list(grid.get("cells")))
        docs.append(
            make_doc(
                match_id=match_id,
                team_id=team_id or team.get("id"),
                team_name=team_name or resolved_team_name,
                source_service=self.source_service,
                document_type="ball_loss_heatmap_summary",
                slug="heatmap",
                title="Ball loss heatmap summary",
                category="ball_losses",
                text=(
                    f"Ball loss heatmap for {resolved_team_name}: grid {grid.get('rows', 0)}x{grid.get('cols', 0)}. "
                    f"Highest loss cells (row,col,losses): {', '.join(hot_cells) if hot_cells else 'none'}."
                ),
                metadata={
                    "rows": grid.get("rows"),
                    "cols": grid.get("cols"),
                    "hotCells": hot_cells,
                    "tags": ["ball_losses", "heatmap"],
                },
            )
        )

        if events:
            danger_first = sorted(
                events,
                key=lambda row: 1 if safe_text(row.get("zone"), "").lower() == "defensive_third" else 0,
                reverse=True,
            )
            snippets = []
            for row in danger_first[:6]:
                minute = int(to_float(row.get("minute"), 0))
                second = int(to_float(row.get("second"), 0))
                player = safe_text(row.get("player_name"), "unknown_player")
                zone = safe_text(row.get("zone"), "n/a")
                loss_type = safe_text(row.get("type"), "unknown")
                snippets.append(f"{minute}:{second:02d} {player} {loss_type} in {zone}")

            docs.append(
                make_doc(
                    match_id=match_id,
                    team_id=team_id or team.get("id"),
                    team_name=team_name or resolved_team_name,
                    source_service=self.source_service,
                    document_type="ball_loss_events_summary",
                    slug="events",
                    title="Ball loss events summary",
                    category="ball_losses",
                    text=(
                        f"Representative ball loss events for {resolved_team_name}: "
                        f"{to_sentence(snippets, max_items=len(snippets))}."
                    ),
                    metadata={
                        "eventsIncluded": len(snippets),
                        "tags": ["ball_losses", "events"],
                    },
                )
            )
        else:
            warnings.append("ballLosses.events missing or empty.")

        if not by_player:
            warnings.append("ballLosses.by_player missing or empty.")

        return docs, warnings

    @staticmethod
    def _extract_hot_cells(cells: list[Any]) -> list[str]:
        scored: list[tuple[int, int, float]] = []
        for row_index, row in enumerate(cells):
            if not isinstance(row, list):
                continue
            for col_index, value in enumerate(row):
                losses = to_float(value, default=0.0)
                if losses > 0:
                    scored.append((row_index, col_index, losses))

        scored.sort(key=lambda item: item[2], reverse=True)
        return [f"({r},{c},{int(v)})" for r, c, v in scored[:5]]
