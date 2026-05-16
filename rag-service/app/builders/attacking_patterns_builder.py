from __future__ import annotations

from typing import Any

from app.builders.common import make_doc
from app.schemas.documents import RagDocument
from app.utils.numeric import fmt_float, to_float
from app.utils.safe_get import as_list
from app.utils.text_formatting import safe_text, to_sentence


class AttackingPatternsDocumentBuilder:
    source_service = "attacking-patterns-service"

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
        attack_types = as_list(payload.get("attackTypes"))
        flank = payload.get("flankBreakdown") or {}
        top_attacker = payload.get("topAttacker")

        total_attacks = int(to_float(payload.get("totalAttacks"), 0.0))
        avg_xg = to_float(payload.get("avgXgPerAttack"), 0.0)
        most_dangerous_flank = safe_text(payload.get("mostDangerousFlank"), "center")
        insight = safe_text(payload.get("insight"), "No attacking insight provided.")

        docs.append(
            make_doc(
                match_id=match_id,
                team_id=team_id,
                team_name=team_name,
                source_service=self.source_service,
                document_type="attacking_patterns_summary",
                slug="summary",
                title="Attacking patterns summary",
                category="attacking_patterns",
                text=(
                    f"Attacking patterns for {safe_text(team_name, 'the team')} in match {match_id}: "
                    f"total attacks {total_attacks}, average xG per attack {fmt_float(avg_xg, digits=3)}, "
                    f"most dangerous flank {most_dangerous_flank}. "
                    f"Flank split: left {flank.get('left', 0)}, center {flank.get('center', 0)}, "
                    f"right {flank.get('right', 0)}. Insight: {insight}"
                ),
                metadata={
                    "totalAttacks": total_attacks,
                    "avgXgPerAttack": avg_xg,
                    "mostDangerousFlank": most_dangerous_flank,
                    "flankBreakdown": flank,
                    "tags": ["attacking_patterns", "summary"],
                },
            )
        )

        if attack_types:
            highlights = []
            sorted_types = sorted(attack_types, key=lambda row: to_float(row.get("xgTotal")), reverse=True)
            for row in sorted_types[:5]:
                label = safe_text(row.get("label"), "unknown")
                count = int(to_float(row.get("count"), 0.0))
                with_shot = int(to_float(row.get("withShot"), 0.0))
                with_goal = int(to_float(row.get("withGoal"), 0.0))
                xg_total = to_float(row.get("xgTotal"), 0.0)
                highlights.append(
                    f"{label}: {count} attacks, shots {with_shot}, goals {with_goal}, xG {fmt_float(xg_total, digits=3)}"
                )
                docs.append(
                    make_doc(
                        match_id=match_id,
                        team_id=team_id,
                        team_name=team_name,
                        source_service=self.source_service,
                        document_type="attacking_type_profile",
                        slug=label,
                        title=f"Attacking type: {label}",
                        category="attacking_patterns",
                        text=(
                            f"Attack type {label} produced {count} attacks with {with_shot} ending in shots, "
                            f"{with_goal} ending in goals and total xG {fmt_float(xg_total, digits=3)}."
                        ),
                        metadata={
                            "label": label,
                            "count": count,
                            "withShot": with_shot,
                            "withGoal": with_goal,
                            "xgTotal": xg_total,
                            "tags": ["attacking_patterns", "attack_type", label],
                        },
                    )
                )

            docs.append(
                make_doc(
                    match_id=match_id,
                    team_id=team_id,
                    team_name=team_name,
                    source_service=self.source_service,
                    document_type="attacking_type_summary",
                    slug="types",
                    title="Attacking type summary",
                    category="attacking_patterns",
                    text="Attacking type breakdown: " + to_sentence(highlights, max_items=len(highlights)) + ".",
                    metadata={"tags": ["attacking_patterns", "attack_type_summary"]},
                )
            )
        else:
            warnings.append("attackingPatterns.attackTypes missing or empty.")

        if players:
            top_players = sorted(players, key=lambda row: to_float(row.get("xgCreated")), reverse=True)[:5]
            for row in top_players:
                player_name = safe_text(row.get("name"), "unknown_player")
                preferred_flank = safe_text(row.get("preferredFlank"), "center")
                attacks = int(to_float(row.get("attacks"), 0.0))
                shots = int(to_float(row.get("shots"), 0.0))
                xg_created = to_float(row.get("xgCreated"), 0.0)
                docs.append(
                    make_doc(
                        match_id=match_id,
                        team_id=team_id,
                        team_name=team_name,
                        source_service=self.source_service,
                        document_type="attacking_player_profile",
                        slug=player_name,
                        title=f"Attacking player profile: {player_name}",
                        category="attacking_patterns",
                        text=(
                            f"{player_name} ({safe_text(row.get('position'))}) contributed {attacks} attacking sequences, "
                            f"{shots} shots and xG created {fmt_float(xg_created, digits=3)}. "
                            f"Preferred flank: {preferred_flank}."
                        ),
                        metadata={
                            "playerId": row.get("id"),
                            "player": player_name,
                            "position": row.get("position"),
                            "attacks": attacks,
                            "shots": shots,
                            "xgCreated": xg_created,
                            "preferredFlank": preferred_flank,
                            "tags": ["attacking_patterns", "player_profile"],
                        },
                    )
                )
        else:
            warnings.append("attackingPatterns.players missing or empty.")

        resolved_top_attacker: dict[str, Any] | None = None
        if isinstance(top_attacker, dict):
            resolved_top_attacker = top_attacker
        elif players:
            sorted_by_attacks = sorted(
                players,
                key=lambda row: (to_float(row.get("attacks")), to_float(row.get("xgCreated"))),
                reverse=True,
            )
            if sorted_by_attacks:
                resolved_top_attacker = sorted_by_attacks[0]

        if isinstance(resolved_top_attacker, dict):
            top_player_name = safe_text(resolved_top_attacker.get("name"), "unknown_player")
            docs.append(
                make_doc(
                    match_id=match_id,
                    team_id=team_id,
                    team_name=team_name,
                    source_service=self.source_service,
                    document_type="top_attacker_summary",
                    slug=top_player_name,
                    title=f"Top attacker: {top_player_name}",
                    category="attacking_patterns",
                    text=(
                        f"Top attacker was {top_player_name} with "
                        f"{int(to_float(resolved_top_attacker.get('attacks'), 0.0))} attacks, "
                        f"{int(to_float(resolved_top_attacker.get('shots'), 0.0))} shots and xG created "
                        f"{fmt_float(resolved_top_attacker.get('xgCreated'), digits=3)}."
                    ),
                    metadata={
                        "playerId": resolved_top_attacker.get("id"),
                        "player": top_player_name,
                        "attacks": resolved_top_attacker.get("attacks"),
                        "shots": resolved_top_attacker.get("shots"),
                        "xgCreated": resolved_top_attacker.get("xgCreated"),
                        "derived": not isinstance(top_attacker, dict),
                        "tags": ["attacking_patterns", "top_attacker"],
                    },
                )
            )

        return docs, warnings
