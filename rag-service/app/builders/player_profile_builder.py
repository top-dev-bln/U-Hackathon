from __future__ import annotations

from typing import Any

from app.builders.common import make_doc
from app.schemas.documents import RagDocument
from app.utils.numeric import fmt_float, to_float
from app.utils.safe_get import as_list
from app.utils.text_formatting import safe_text


class PlayerProfileDocumentBuilder:
    source_service = "player-profile-service"

    def build(
        self,
        *,
        match_id: int,
        team_id: int | None,
        team_name: str | None,
        profiles: list[dict[str, Any]],
    ) -> tuple[list[RagDocument], list[str]]:
        warnings: list[str] = []
        docs: list[RagDocument] = []

        for profile in profiles:
            player = profile.get("player") or {}
            team = profile.get("team") or {}
            stats = profile.get("stats") or {}
            grid = profile.get("grid") or {}
            zones = stats.get("zones") or {}
            flanks = stats.get("flanks") or {}

            player_name = safe_text(player.get("name"), "unknown_player")
            position = safe_text(player.get("position"), "unknown_position")
            profile_team_name = safe_text(team.get("name"), team_name or "unknown_team")

            docs.append(
                make_doc(
                    match_id=match_id,
                    team_id=team_id or team.get("id"),
                    team_name=team_name or profile_team_name,
                    source_service=self.source_service,
                    document_type="player_movement_profile",
                    slug=player_name,
                    title=f"Movement profile: {player_name}",
                    category="player_profile",
                    text=(
                        f"{player_name} played as {position}. Total touches: {stats.get('total_touches', 0)}. "
                        f"Average location: x={fmt_float(stats.get('avg_x'), digits=2)}, "
                        f"y={fmt_float(stats.get('avg_y'), digits=2)}. "
                        f"Touches by thirds: defensive {zones.get('def_third', 0)}, "
                        f"middle {zones.get('mid_third', 0)}, attacking {zones.get('att_third', 0)}. "
                        f"Flank usage: left {flanks.get('left', 0)}, center {flanks.get('center', 0)}, "
                        f"right {flanks.get('right', 0)}."
                    ),
                    metadata={
                        "playerId": player.get("id"),
                        "player": player_name,
                        "position": position,
                        "totalTouches": stats.get("total_touches"),
                        "receptions": stats.get("receptions"),
                        "tags": ["player_profile", "movement"],
                    },
                )
            )

            cells = as_list(grid.get("cells"))
            hot_cells = self._extract_hot_cells(cells)
            docs.append(
                make_doc(
                    match_id=match_id,
                    team_id=team_id or team.get("id"),
                    team_name=team_name or profile_team_name,
                    source_service=self.source_service,
                    document_type="player_heatmap_summary",
                    slug=f"{player_name}_heatmap",
                    title=f"Heatmap summary: {player_name}",
                    category="player_profile",
                    text=(
                        f"Heatmap profile for {player_name} in match {match_id}: "
                        f"grid size {grid.get('rows', 0)}x{grid.get('cols', 0)}. "
                        f"Most active cells (row,col,touches): {', '.join(hot_cells) if hot_cells else 'none'}."
                    ),
                    metadata={
                        "rows": grid.get("rows"),
                        "cols": grid.get("cols"),
                        "hotCells": hot_cells,
                        "tags": ["player_profile", "heatmap"],
                    },
                )
            )

            docs.append(
                make_doc(
                    match_id=match_id,
                    team_id=team_id or team.get("id"),
                    team_name=team_name or profile_team_name,
                    source_service=self.source_service,
                    document_type="player_role_interpretation",
                    slug=f"{player_name}_role",
                    title=f"Role interpretation: {player_name}",
                    category="player_profile",
                    text=self._role_text(player_name=player_name, position=position, zones=zones, flanks=flanks),
                    metadata={
                        "zones": zones,
                        "flanks": flanks,
                        "tags": ["player_profile", "role_interpretation"],
                    },
                )
            )

        if not profiles:
            warnings.append("playerProfiles output empty.")

        return docs, warnings

    @staticmethod
    def _extract_hot_cells(cells: list[Any]) -> list[str]:
        scored: list[tuple[int, int, float]] = []
        for row_index, row in enumerate(cells):
            if not isinstance(row, list):
                continue
            for col_index, value in enumerate(row):
                touches = to_float(value, default=0.0)
                if touches > 0:
                    scored.append((row_index, col_index, touches))

        scored.sort(key=lambda item: item[2], reverse=True)
        return [f"({r},{c},{int(v)})" for r, c, v in scored[:5]]

    @staticmethod
    def _role_text(
        *,
        player_name: str,
        position: str,
        zones: dict[str, Any],
        flanks: dict[str, Any],
    ) -> str:
        att = to_float(zones.get("att_third"))
        mid = to_float(zones.get("mid_third"))
        deff = to_float(zones.get("def_third"))
        left = to_float(flanks.get("left"))
        center = to_float(flanks.get("center"))
        right = to_float(flanks.get("right"))

        zone_hint = "balanced zone presence"
        if att > mid and att > deff:
            zone_hint = "advanced attacking orientation"
        elif deff > mid and deff > att:
            zone_hint = "deep defensive orientation"
        elif mid >= att and mid >= deff:
            zone_hint = "midfield circulation orientation"

        flank_hint = "balanced flank usage"
        if center > left and center > right:
            flank_hint = "central-lane dominance"
        elif left > center and left > right:
            flank_hint = "left-lane bias"
        elif right > center and right > left:
            flank_hint = "right-lane bias"

        return (
            f"{player_name}'s movement profile suggests a {position} role with {zone_hint} "
            f"and {flank_hint}. Zone touches were defensive={int(deff)}, middle={int(mid)}, "
            f"attacking={int(att)}."
        )

