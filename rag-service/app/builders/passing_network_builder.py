from __future__ import annotations

from typing import Any

from app.builders.common import make_doc
from app.schemas.documents import RagDocument
from app.utils.numeric import fmt_float, to_float
from app.utils.safe_get import as_list
from app.utils.text_formatting import safe_text, to_sentence


class PassingNetworkDocumentBuilder:
    source_service = "passing-network-service"

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
        nodes = as_list(payload.get("nodes"))
        edges = as_list(payload.get("edges"))
        resolved_team_name = safe_text(team.get("name"), team_name or "unknown_team")

        docs.append(
            make_doc(
                match_id=match_id,
                team_id=team_id or team.get("id"),
                team_name=team_name or resolved_team_name,
                source_service=self.source_service,
                document_type="passing_network_summary",
                slug="summary",
                title="Passing network summary",
                category="passing_network",
                text=(
                    f"The passing network for {resolved_team_name} contains {len(nodes)} player nodes and "
                    f"{len(edges)} connections, with cutoff minute {payload.get('cutoff_minute', 'n/a')}. "
                    f"This network captures positional shape, circulation hubs, and connection strengths."
                ),
                metadata={
                    "period": payload.get("period"),
                    "nodeCount": len(nodes),
                    "edgeCount": len(edges),
                    "tags": ["passing_network", "summary"],
                },
            )
        )

        id_to_name = {int(node.get("id", -1)): safe_text(node.get("name"), "unknown") for node in nodes}
        top_nodes = sorted(nodes, key=lambda n: to_float(n.get("touches"), 0.0), reverse=True)[:5]
        top_node_names = [f"{safe_text(n.get('name'))} ({int(to_float(n.get('touches'), 0.0))} touches)" for n in top_nodes]
        docs.append(
            make_doc(
                match_id=match_id,
                team_id=team_id or team.get("id"),
                team_name=team_name or resolved_team_name,
                source_service=self.source_service,
                document_type="passing_hubs_summary",
                slug="hubs",
                title="Passing hubs summary",
                category="passing_network",
                text=(
                    f"Main passing hubs for {resolved_team_name}: {to_sentence(top_node_names, max_items=5)}. "
                    f"These players anchor circulation and shape build-up stability."
                ),
                metadata={"topHubs": top_node_names, "tags": ["passing_network", "hubs"]},
            )
        )

        top_edges = sorted(edges, key=lambda e: to_float(e.get("weight"), 0.0), reverse=True)[:6]
        edge_summaries = []
        for edge in top_edges:
            source_id = int(to_float(edge.get("source"), -1))
            target_id = int(to_float(edge.get("target"), -1))
            weight = int(to_float(edge.get("weight"), 0))
            edge_summaries.append(
                f"{id_to_name.get(source_id, str(source_id))} -> {id_to_name.get(target_id, str(target_id))} ({weight})"
            )
        docs.append(
            make_doc(
                match_id=match_id,
                team_id=team_id or team.get("id"),
                team_name=team_name or resolved_team_name,
                source_service=self.source_service,
                document_type="passing_connections_summary",
                slug="connections",
                title="Passing connections summary",
                category="passing_network",
                text=(
                    f"Strongest passing connections in match {match_id}: "
                    f"{to_sentence(edge_summaries, max_items=len(edge_summaries) or 1)}."
                ),
                metadata={"topConnections": edge_summaries, "tags": ["passing_network", "connections"]},
            )
        )

        isolated_nodes = sorted(nodes, key=lambda n: to_float(n.get("touches"), 0.0))[:3]
        isolated_names = [f"{safe_text(n.get('name'))} ({int(to_float(n.get('touches'), 0.0))} touches)" for n in isolated_nodes]
        docs.append(
            make_doc(
                match_id=match_id,
                team_id=team_id or team.get("id"),
                team_name=team_name or resolved_team_name,
                source_service=self.source_service,
                document_type="isolated_players_summary",
                slug="isolated",
                title="Isolated players summary",
                category="passing_network",
                text=(
                    f"Potentially isolated players by low touch volume: "
                    f"{to_sentence(isolated_names, max_items=len(isolated_names) or 1)}."
                ),
                metadata={"isolatedPlayers": isolated_names, "tags": ["passing_network", "isolated_players"]},
            )
        )

        flank_left, flank_center, flank_right = self._flank_distribution(nodes)
        docs.append(
            make_doc(
                match_id=match_id,
                team_id=team_id or team.get("id"),
                team_name=team_name or resolved_team_name,
                source_service=self.source_service,
                document_type="flank_usage_summary",
                slug="flanks",
                title="Flank usage summary",
                category="passing_network",
                text=(
                    f"Flank usage by weighted node positions: left {fmt_float(flank_left, digits=2)}%, "
                    f"center {fmt_float(flank_center, digits=2)}%, right {fmt_float(flank_right, digits=2)}%."
                ),
                metadata={
                    "leftPct": flank_left,
                    "centerPct": flank_center,
                    "rightPct": flank_right,
                    "tags": ["passing_network", "flank_usage"],
                },
            )
        )

        if not nodes:
            warnings.append("passingNetwork.nodes missing or empty.")
        if not edges:
            warnings.append("passingNetwork.edges missing or empty.")

        return docs, warnings

    @staticmethod
    def _flank_distribution(nodes: list[dict[str, Any]]) -> tuple[float, float, float]:
        left_touches = 0.0
        center_touches = 0.0
        right_touches = 0.0

        for node in nodes:
            y = to_float(node.get("y"), 50.0)
            touches = max(to_float(node.get("touches"), 0.0), 0.0)
            if y < 33.33:
                left_touches += touches
            elif y < 66.66:
                center_touches += touches
            else:
                right_touches += touches

        total = left_touches + center_touches + right_touches
        if total <= 0:
            return 0.0, 0.0, 0.0

        return (
            left_touches * 100 / total,
            center_touches * 100 / total,
            right_touches * 100 / total,
        )

