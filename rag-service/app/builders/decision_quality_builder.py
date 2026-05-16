from __future__ import annotations

from typing import Any

from app.builders.common import make_doc
from app.schemas.documents import RagDocument
from app.utils.numeric import fmt_float, to_float
from app.utils.safe_get import as_list
from app.utils.text_formatting import safe_text, to_sentence


class DecisionQualityDocumentBuilder:
    source_service = "decision-quality-service"

    def build(
        self,
        *,
        match_id: int,
        team_id: int | None,
        team_name: str | None,
        payload: dict[str, Any],
        top_n_phases: int,
        max_player_docs: int,
    ) -> tuple[list[RagDocument], list[str]]:
        warnings: list[str] = []
        docs: list[RagDocument] = []

        summary = payload.get("summary") or {}
        players = payload.get("players") or {}
        phases = payload.get("phases") or {}
        team_stats = payload.get("teamStats") or {}
        match_info = payload.get("match") or {}

        docs.append(
            make_doc(
                match_id=match_id,
                team_id=team_id,
                team_name=team_name,
                source_service=self.source_service,
                document_type="decision_quality_summary",
                slug="summary",
                title="Decision quality summary",
                category="decision_quality",
                text=(
                    f"The decision quality model analyzed {summary.get('actionsAnalyzed', 0)} actions from "
                    f"{summary.get('playersAnalyzed', 0)} players in match {match_id}. "
                    f"Average decision value was {fmt_float(summary.get('averageDecisionValue'))}. "
                    f"Low decision phases: {summary.get('lowDecisionPhases', 0)}. "
                    f"Phases with better alternative: {summary.get('phasesWithAlternative', 0)}. "
                    f"Missed shot or goal opportunities: {summary.get('missedShotOrGoalOpportunities', 0)}."
                ),
                metadata={
                    "lowScoreThresholdUsed": summary.get("lowScoreThresholdUsed"),
                    "teamScope": match_info.get("teamScope"),
                    "tags": ["decision_quality", "summary"],
                },
            )
        )

        needs_support = as_list(players.get("needsSupport"))
        underperformers = as_list(players.get("underperformers"))
        combined_players = needs_support + underperformers

        by_player_name: dict[str, dict[str, Any]] = {}
        for row in combined_players:
            player_name = safe_text(row.get("player_name"), "unknown_player")
            existing = by_player_name.get(player_name)
            if existing is None or to_float(row.get("decisionScore"), 0.0) < to_float(existing.get("decisionScore"), 0.0):
                by_player_name[player_name] = row

        sorted_players = sorted(
            by_player_name.values(),
            key=lambda item: to_float(item.get("decisionScore"), 999.0),
        )[:max_player_docs]

        for row in sorted_players:
            player_name = safe_text(row.get("player_name"), "unknown_player")
            text = (
                f"{player_name} had decision score {fmt_float(row.get('decisionScore'))} across "
                f"{row.get('actionsAnalyzed', 0)} actions, with {row.get('lowScoreActions', 0)} low-score actions. "
                f"Weak decision type: {safe_text(row.get('weakDecisionType'))}. "
                f"Best decision type: {safe_text(row.get('bestDecisionType'))}. "
                f"Recommended when low: {safe_text(row.get('recommendedDecisionTypeWhenLow'))}. "
                f"Average potential gain: {fmt_float(row.get('avgPotentialGainOnSuggestions'))}."
            )
            docs.append(
                make_doc(
                    match_id=match_id,
                    team_id=team_id,
                    team_name=team_name,
                    source_service=self.source_service,
                    document_type="player_decision_profile",
                    slug=player_name,
                    title=f"Decision profile: {player_name}",
                    category="decision_quality",
                    text=text,
                    metadata={
                        "playerId": row.get("player_id"),
                        "player": player_name,
                        "decisionScore": row.get("decisionScore"),
                        "needsDecisionSupport": row.get("needsDecisionSupport"),
                        "suggestedActions": row.get("suggestedActions"),
                        "tags": ["decision_quality", "player_profile"],
                    },
                )
            )

        improvable_phases = as_list(phases.get("improvablePhases"))
        improvable_phases.sort(key=lambda row: to_float(row.get("potentialGain"), 0.0), reverse=True)
        for phase in improvable_phases[:top_n_phases]:
            minute = phase.get("minute", 0)
            second = phase.get("second", 0)
            player_name = safe_text(phase.get("player_name"), "unknown_player")
            text = (
                f"At minute {minute}:{int(second):02d}, {player_name} chose {safe_text(phase.get('decision'))} "
                f"with decision value {fmt_float(phase.get('decisionValue'))}. "
                f"Suggested alternative: {safe_text(phase.get('suggestedAlternative'))}. "
                f"Best decision type: {safe_text(phase.get('bestDecisionType'))} with value "
                f"{fmt_float(phase.get('bestDecisionValue'))}. Potential gain: {fmt_float(phase.get('potentialGain'))}."
            )
            docs.append(
                make_doc(
                    match_id=match_id,
                    team_id=team_id,
                    team_name=team_name,
                    source_service=self.source_service,
                    document_type="improvable_phase",
                    slug=str(phase.get("event_id", f"{minute}_{second}_{player_name}")),
                    title=f"Improvable phase {minute}:{int(second):02d}",
                    category="decision_quality",
                    text=text,
                    metadata={
                        "eventId": phase.get("event_id"),
                        "minute": minute,
                        "second": second,
                        "player": player_name,
                        "potentialGain": phase.get("potentialGain"),
                        "tags": ["decision_quality", "improvable_phase"],
                    },
                )
            )

        missed = as_list(phases.get("missedShotOrGoalOpportunities"))
        missed.sort(key=lambda row: to_float(row.get("potentialGain"), 0.0), reverse=True)
        for phase in missed[:top_n_phases]:
            minute = phase.get("minute", 0)
            second = phase.get("second", 0)
            player_name = safe_text(phase.get("player_name"), "unknown_player")
            text = (
                f"At minute {minute}:{int(second):02d}, {player_name} made a "
                f"{safe_text(phase.get('decision'))} decision with value {fmt_float(phase.get('decisionValue'))}. "
                f"Potential missed shot/goal opportunity with alternative "
                f"{safe_text(phase.get('suggestedAlternative'))} and potential gain "
                f"{fmt_float(phase.get('potentialGain'))}."
            )
            docs.append(
                make_doc(
                    match_id=match_id,
                    team_id=team_id,
                    team_name=team_name,
                    source_service=self.source_service,
                    document_type="missed_opportunity",
                    slug=str(phase.get("event_id", f"{minute}_{second}_{player_name}")),
                    title=f"Missed opportunity {minute}:{int(second):02d}",
                    category="final_third",
                    text=text,
                    metadata={
                        "eventId": phase.get("event_id"),
                        "minute": minute,
                        "second": second,
                        "player": player_name,
                        "potentialGain": phase.get("potentialGain"),
                        "tags": ["decision_quality", "missed_opportunity", "final_third"],
                    },
                )
            )

        decision_by_type = as_list(team_stats.get("decisionByType"))
        if decision_by_type:
            snippets = []
            for row in decision_by_type:
                snippets.append(
                    f"{safe_text(row.get('decision'))}: {row.get('actions', 0)} actions, "
                    f"avg value {fmt_float(row.get('avgDecisionValue'))}, "
                    f"low phases {row.get('lowDecisionPhases', 0)}"
                )
            docs.append(
                make_doc(
                    match_id=match_id,
                    team_id=team_id,
                    team_name=team_name,
                    source_service=self.source_service,
                    document_type="decision_by_type_summary",
                    slug="decision_by_type",
                    title="Decision by type summary",
                    category="decision_quality",
                    text="Decision type summary: " + "; ".join(snippets) + ".",
                    metadata={"tags": ["decision_quality", "decision_by_type"]},
                )
            )
        else:
            warnings.append("decisionQuality.teamStats.decisionByType missing or empty.")

        timeline = as_list(team_stats.get("timeline"))
        if timeline:
            timeline_sorted = sorted(timeline, key=lambda row: safe_text(row.get("minuteBucket"), ""))
            timeline_text = []
            for row in timeline_sorted:
                timeline_text.append(
                    f"{safe_text(row.get('minuteBucket'))}: avg value {fmt_float(row.get('avgDecisionValue'))}, "
                    f"low phases {row.get('lowDecisionPhases', 0)}"
                )
            docs.append(
                make_doc(
                    match_id=match_id,
                    team_id=team_id,
                    team_name=team_name,
                    source_service=self.source_service,
                    document_type="decision_timeline_summary",
                    slug="timeline",
                    title="Decision timeline summary",
                    category="decision_quality",
                    text=(
                        f"Decision quality timeline for match {match_id}: "
                        f"{to_sentence(timeline_text, max_items=len(timeline_text))}."
                    ),
                    metadata={"timelineBuckets": len(timeline), "tags": ["decision_quality", "timeline"]},
                )
            )
        else:
            warnings.append("decisionQuality.teamStats.timeline missing or empty.")

        return docs, warnings

