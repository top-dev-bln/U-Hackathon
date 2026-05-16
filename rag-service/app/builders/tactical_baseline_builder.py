from __future__ import annotations

from typing import Any

from app.builders.common import make_doc
from app.schemas.documents import RagDocument
from app.utils.numeric import fmt_float, to_float
from app.utils.safe_get import as_list
from app.utils.text_formatting import safe_text


class TacticalBaselineDocumentBuilder:
    source_service = "tactical-baseline-service"

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

        baseline_model = payload.get("baselineModel") or {}
        weakness_signals = as_list(payload.get("weaknessSignals"))
        metric_comparisons = payload.get("metricComparisons") or {}

        summary_text = (
            f"The tactical baseline model rated {safe_text(team_name, 'the team')} with an overall weakness "
            f"score of {fmt_float(baseline_model.get('overallWeaknessScore'))} and risk level "
            f"{safe_text(baseline_model.get('riskLevel'), 'unknown')}. "
            f"The tactical profile is {safe_text(baseline_model.get('tacticalProfile'), 'unknown')}. "
            f"Anomaly flag: {bool(baseline_model.get('isAnomalous', False))} with anomaly score "
            f"{fmt_float(baseline_model.get('anomalyScore'))}."
        )
        docs.append(
            make_doc(
                match_id=match_id,
                team_id=team_id,
                team_name=team_name,
                source_service=self.source_service,
                document_type="baseline_summary",
                slug="summary",
                title="Tactical baseline summary",
                category="baseline",
                text=summary_text,
                metadata={
                    "riskLevel": baseline_model.get("riskLevel"),
                    "overallWeaknessScore": baseline_model.get("overallWeaknessScore"),
                    "clusterId": baseline_model.get("clusterId"),
                    "tags": ["baseline", "summary"],
                },
            )
        )

        for signal in weakness_signals:
            metric = safe_text(signal.get("metric"), "unknown_metric")
            category = safe_text(signal.get("category"), "general")
            severity = safe_text(signal.get("severity"), "unknown")
            text = (
                f"{safe_text(team_name, 'The team')} showed a {severity} weakness in {metric}. "
                f"Value: {fmt_float(signal.get('value'))}. "
                f"League average: {fmt_float(signal.get('leagueAverage'))}. "
                f"Z-score: {fmt_float(signal.get('zScore'))}. "
                f"Percentile: {fmt_float(signal.get('percentile'))}. "
                f"This belongs to the {category} category."
            )
            docs.append(
                make_doc(
                    match_id=match_id,
                    team_id=team_id,
                    team_name=team_name,
                    source_service=self.source_service,
                    document_type="baseline_weakness_signal",
                    slug=f"{category}_{metric}",
                    title=f"Weakness signal: {metric}",
                    category=category,
                    text=text,
                    metadata={
                        "signalId": signal.get("signalId"),
                        "severity": severity,
                        "severityScore": signal.get("severityScore"),
                        "metric": metric,
                        "value": signal.get("value"),
                        "leagueAverage": signal.get("leagueAverage"),
                        "zScore": signal.get("zScore"),
                        "percentile": signal.get("percentile"),
                        "direction": signal.get("direction"),
                        "tags": ["baseline", "weakness_signal", category, severity],
                    },
                )
            )

        if metric_comparisons:
            metric_rows: list[tuple[str, dict[str, Any]]] = []
            for metric_name, metric_data in metric_comparisons.items():
                if isinstance(metric_data, dict):
                    metric_rows.append((metric_name, metric_data))

            # Keep most negative z-score first as weak signals.
            metric_rows.sort(key=lambda row: to_float(row[1].get("zScore"), default=999.0))
            highlights = metric_rows[:6]
            summary_parts = []
            for metric_name, metric_data in highlights:
                summary_parts.append(
                    f"{metric_name}={fmt_float(metric_data.get('value'))} vs league "
                    f"{fmt_float(metric_data.get('leagueAverage'))} (z={fmt_float(metric_data.get('zScore'))})"
                )

            docs.append(
                make_doc(
                    match_id=match_id,
                    team_id=team_id,
                    team_name=team_name,
                    source_service=self.source_service,
                    document_type="metric_comparison_summary",
                    slug="metrics",
                    title="Baseline metric comparison summary",
                    category="baseline",
                    text=(
                        f"Key baseline metric comparisons for {safe_text(team_name, 'the team')}: "
                        f"{'; '.join(summary_parts)}."
                    ),
                    metadata={
                        "metricsIncluded": [name for name, _ in highlights],
                        "tags": ["baseline", "metric_comparison"],
                    },
                )
            )
        else:
            warnings.append("tacticalBaseline.metricComparisons missing or empty.")

        docs.append(
            make_doc(
                match_id=match_id,
                team_id=team_id,
                team_name=team_name,
                source_service=self.source_service,
                document_type="tactical_profile_document",
                slug="tactical_profile",
                title="Tactical profile interpretation",
                category="baseline",
                text=(
                    f"{safe_text(team_name, 'The team')}'s tactical profile is "
                    f"{safe_text(baseline_model.get('tacticalProfile'), 'unknown')}, "
                    f"with risk level {safe_text(baseline_model.get('riskLevel'), 'unknown')}."
                ),
                metadata={
                    "tacticalProfile": baseline_model.get("tacticalProfile"),
                    "riskLevel": baseline_model.get("riskLevel"),
                    "tags": ["baseline", "tactical_profile"],
                },
            )
        )

        docs.append(
            make_doc(
                match_id=match_id,
                team_id=team_id,
                team_name=team_name,
                source_service=self.source_service,
                document_type="anomaly_document",
                slug="anomaly",
                title="Anomaly analysis",
                category="baseline",
                text=(
                    f"Anomaly detection for match {match_id}: isAnomalous="
                    f"{bool(baseline_model.get('isAnomalous', False))}, anomalyScore="
                    f"{fmt_float(baseline_model.get('anomalyScore'))}, clusterId="
                    f"{safe_text(baseline_model.get('clusterId'))}."
                ),
                metadata={
                    "isAnomalous": bool(baseline_model.get("isAnomalous", False)),
                    "anomalyScore": baseline_model.get("anomalyScore"),
                    "clusterId": baseline_model.get("clusterId"),
                    "tags": ["baseline", "anomaly"],
                },
            )
        )

        return docs, warnings

