from __future__ import annotations

from typing import Any

from app.builders.common import make_doc
from app.schemas.documents import RagDocument
from app.utils.numeric import fmt_float, to_float
from app.utils.safe_get import as_list
from app.utils.text_formatting import safe_text, to_sentence


class LineBreaksDocumentBuilder:
    source_service = "line-breaks-service"

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
        by_type = payload.get("by_type") or {}
        by_zone = payload.get("by_target_zone") or {}
        by_player = as_list(payload.get("by_player"))
        events = as_list(payload.get("events"))

        docs.append(
            make_doc(
                match_id=match_id,
                team_id=team_id or team.get("id"),
                team_name=team_name or resolved_team_name,
                source_service=self.source_service,
                document_type="line_breaks_summary",
                slug="summary",
                title="Line breaks summary",
                category="line_breaks",
                text=(
                    f"Line break profile for {resolved_team_name} in match {match_id}: "
                    f"attempts {payload.get('total_attempts', 0)}, completed {payload.get('total_completed', 0)}, "
                    f"completion rate {fmt_float(payload.get('completion_rate'), digits=3)}. "
                    f"By type: progressive {by_type.get('progressive', 0)}, through {by_type.get('through', 0)}. "
                    f"By target zone: defensive {by_zone.get('defensive_third', 0)}, "
                    f"middle {by_zone.get('middle_third', 0)}, attacking {by_zone.get('attacking_third', 0)}."
                ),
                metadata={
                    "period": payload.get("period"),
                    "totalAttempts": payload.get("total_attempts"),
                    "totalCompleted": payload.get("total_completed"),
                    "completionRate": payload.get("completion_rate"),
                    "tags": ["line_breaks", "summary"],
                },
            )
        )

        players_sorted = sorted(by_player, key=lambda row: to_float(row.get("attempts")), reverse=True)
        for row in players_sorted[:5]:
            player_name = safe_text(row.get("name"), "unknown_player")
            docs.append(
                make_doc(
                    match_id=match_id,
                    team_id=team_id or team.get("id"),
                    team_name=team_name or resolved_team_name,
                    source_service=self.source_service,
                    document_type="line_break_player_profile",
                    slug=player_name,
                    title=f"Line break profile: {player_name}",
                    category="line_breaks",
                    text=(
                        f"{player_name} attempted {row.get('attempts', 0)} line breaks and completed "
                        f"{row.get('completed', 0)} with completion rate "
                        f"{fmt_float(row.get('completion_rate'), digits=3)}. "
                        f"Position: {safe_text(row.get('position'))}."
                    ),
                    metadata={
                        "playerId": row.get("id"),
                        "player": player_name,
                        "position": row.get("position"),
                        "attempts": row.get("attempts"),
                        "completed": row.get("completed"),
                        "completionRate": row.get("completion_rate"),
                        "tags": ["line_breaks", "player_profile"],
                    },
                )
            )

        event_rows = sorted(events, key=lambda row: to_float(row.get("length"), 0.0), reverse=True)
        if event_rows:
            snippets: list[str] = []
            for row in event_rows[:6]:
                minute = int(to_float(row.get("minute"), 0))
                second = int(to_float(row.get("second"), 0))
                passer = safe_text(row.get("passer_name"), "unknown_passer")
                recipient = safe_text(row.get("recipient_name"), "unknown_recipient")
                event_type = safe_text(row.get("type"), "unknown")
                accuracy = bool(row.get("accurate"))
                zone = safe_text(row.get("target_zone"), "n/a")
                snippets.append(
                    f"{minute}:{second:02d} {passer}->{recipient} {event_type} "
                    f"{'completed' if accuracy else 'failed'} to {zone}"
                )

            docs.append(
                make_doc(
                    match_id=match_id,
                    team_id=team_id or team.get("id"),
                    team_name=team_name or resolved_team_name,
                    source_service=self.source_service,
                    document_type="line_break_events_summary",
                    slug="events",
                    title="Line break events summary",
                    category="line_breaks",
                    text=(
                        f"Representative line break events for {resolved_team_name}: "
                        f"{to_sentence(snippets, max_items=len(snippets))}."
                    ),
                    metadata={
                        "eventsIncluded": len(snippets),
                        "tags": ["line_breaks", "events"],
                    },
                )
            )
        else:
            warnings.append("lineBreaks.events missing or empty.")

        if not by_player:
            warnings.append("lineBreaks.by_player missing or empty.")

        return docs, warnings
