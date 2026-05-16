from __future__ import annotations

from typing import Any

from app.builders.common import make_doc
from app.schemas.documents import RagDocument
from app.utils.numeric import fmt_float
from app.utils.safe_get import as_list
from app.utils.text_formatting import safe_text, to_sentence


class FusionDocumentBuilder:
    source_service = "tactical-fusion-service"

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

        fusion_output = payload.get("fusionOutput") or {}
        frontend_output = payload.get("frontendOutput") or {}
        meta = payload.get("meta") or {}

        combined_insights = as_list(fusion_output.get("combinedInsights"))
        player_priorities = as_list(fusion_output.get("playerPriorities"))
        training_focus = as_list(fusion_output.get("trainingFocus"))

        headline = safe_text(frontend_output.get("headline"), "No headline available.")
        top_problems = as_list(frontend_output.get("topProblems"))
        recommendations = as_list(frontend_output.get("recommendations"))

        summary_text = (
            f"In match {match_id}, {safe_text(team_name, 'the team')} fusion headline was: {headline} "
            f"The model produced {len(combined_insights)} tactical insights, "
            f"{len(player_priorities)} player priorities, and {len(training_focus)} training focuses. "
            f"Top problems: {to_sentence(top_problems)}. "
            f"Main recommendations: {to_sentence(recommendations)}."
        )
        docs.append(
            make_doc(
                match_id=match_id,
                team_id=team_id,
                team_name=team_name,
                source_service=self.source_service,
                document_type="match_summary",
                slug="summary",
                title="Fusion tactical summary",
                category="fusion",
                text=summary_text,
                metadata={
                    "tags": ["fusion", "match", "summary"],
                    "baselineSignals": as_list(meta.get("baselineSignals")),
                    "decisionSignals": as_list(meta.get("decisionSignals")),
                    "fusedCategories": as_list(meta.get("fusedCategories")),
                },
            )
        )

        for insight in combined_insights:
            category = safe_text(insight.get("category"), "general")
            severity = safe_text(insight.get("severity"), "unknown")
            players = as_list(insight.get("players"))
            evidence = as_list(insight.get("evidence"))
            text = (
                f"{safe_text(team_name, 'The team')} had a {severity} {category} issue. "
                f"{safe_text(insight.get('message'), 'No detailed message provided.')}. "
                f"Affected players: {to_sentence(players)}. "
                f"Evidence: {to_sentence(evidence)}. "
                f"Recommendation: {safe_text(insight.get('recommendation'), 'No recommendation provided.')}"
            )
            docs.append(
                make_doc(
                    match_id=match_id,
                    team_id=team_id,
                    team_name=team_name,
                    source_service=self.source_service,
                    document_type="tactical_insight",
                    slug=f"{category}_{severity}",
                    title=f"{severity.capitalize()} {category} insight",
                    category=category,
                    text=text,
                    metadata={
                        "severity": severity,
                        "score": insight.get("score"),
                        "confidence": insight.get("confidence"),
                        "players": players,
                        "tags": ["fusion", "tactical_insight", category, severity],
                        "type": insight.get("type"),
                    },
                )
            )

        for priority in player_priorities:
            player = safe_text(priority.get("player"), "unknown_player")
            focus_categories = as_list(priority.get("focus_categories"))
            reasons = as_list(priority.get("reasons"))
            priority_score = fmt_float(priority.get("priority_score"), digits=4)
            text = (
                f"{player} is a priority player for review. Priority score: {priority_score}. "
                f"Reasons: {to_sentence(reasons)}. "
                f"Focus categories: {to_sentence(focus_categories)}. "
                f"Recommended action: {safe_text(priority.get('recommendedAction'), 'No action provided.')}"
            )
            docs.append(
                make_doc(
                    match_id=match_id,
                    team_id=team_id,
                    team_name=team_name,
                    source_service=self.source_service,
                    document_type="player_priority",
                    slug=player,
                    title=f"Priority player: {player}",
                    category="priority_player",
                    text=text,
                    metadata={
                        "player": player,
                        "priorityScore": priority.get("priority_score"),
                        "reasons": reasons,
                        "focusCategories": focus_categories,
                        "tags": ["fusion", "priority_player"] + [str(x) for x in focus_categories],
                    },
                )
            )

        for training in training_focus:
            category = safe_text(training.get("category"), "general")
            priority = safe_text(training.get("priority"), "medium")
            text = (
                f"Training focus: {category}. Priority: {priority}. "
                f"Objective: {safe_text(training.get('objective'), 'No objective provided.')}. "
                f"Recommended drill: {safe_text(training.get('drill'), 'No drill provided.')}"
            )
            docs.append(
                make_doc(
                    match_id=match_id,
                    team_id=team_id,
                    team_name=team_name,
                    source_service=self.source_service,
                    document_type="training_focus",
                    slug=category,
                    title=f"Training focus: {category}",
                    category=category,
                    text=text,
                    metadata={
                        "priority": priority,
                        "objective": training.get("objective"),
                        "drill": training.get("drill"),
                        "tags": ["fusion", "training", category, priority],
                    },
                )
            )

        if top_problems or recommendations:
            docs.append(
                make_doc(
                    match_id=match_id,
                    team_id=team_id,
                    team_name=team_name,
                    source_service=self.source_service,
                    document_type="frontend_summary",
                    slug="frontend",
                    title="Frontend tactical summary",
                    category="fusion",
                    text=(
                        f"Frontend summary for match {match_id}: {headline}. "
                        f"Top problems: {to_sentence(top_problems)}. "
                        f"Recommendations: {to_sentence(recommendations)}."
                    ),
                    metadata={
                        "topProblems": top_problems,
                        "recommendations": recommendations,
                        "tags": ["fusion", "frontend_summary"],
                    },
                )
            )
        else:
            warnings.append("fusion.frontendOutput has no topProblems/recommendations.")

        return docs, warnings

