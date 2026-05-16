from __future__ import annotations

from collections import defaultdict

from app.builders.attacking_patterns_builder import AttackingPatternsDocumentBuilder
from app.builders.ball_losses_builder import BallLossesDocumentBuilder
from app.builders.decision_quality_builder import DecisionQualityDocumentBuilder
from app.builders.fusion_builder import FusionDocumentBuilder
from app.builders.line_breaks_builder import LineBreaksDocumentBuilder
from app.builders.passing_network_builder import PassingNetworkDocumentBuilder
from app.builders.player_profile_builder import PlayerProfileDocumentBuilder
from app.builders.pressing_builder import PressingDocumentBuilder
from app.builders.tactical_baseline_builder import TacticalBaselineDocumentBuilder
from app.schemas.documents import RagDocument
from app.schemas.input_bundle import IndexMatchRequest
from app.utils.ids import slugify


class DocumentBuilderService:
    def __init__(self, *, max_player_documents: int) -> None:
        self._fusion = FusionDocumentBuilder()
        self._baseline = TacticalBaselineDocumentBuilder()
        self._decision = DecisionQualityDocumentBuilder()
        self._profile = PlayerProfileDocumentBuilder()
        self._pressing = PressingDocumentBuilder()
        self._passing = PassingNetworkDocumentBuilder()
        self._line_breaks = LineBreaksDocumentBuilder()
        self._ball_losses = BallLossesDocumentBuilder()
        self._attacking_patterns = AttackingPatternsDocumentBuilder()
        self._max_player_documents = max_player_documents

    def build_documents(self, request: IndexMatchRequest) -> tuple[list[RagDocument], list[str]]:
        outputs = request.outputs
        warnings: list[str] = []
        documents: list[RagDocument] = []

        fusion = outputs.fusion
        if fusion:
            built_docs, built_warnings = self._fusion.build(
                match_id=request.matchId,
                team_id=request.teamId,
                team_name=request.teamName,
                payload=fusion,
            )
            documents.extend(built_docs)
            warnings.extend(built_warnings)
        else:
            warnings.append("fusion output missing.")

        tactical_baseline = outputs.tacticalBaseline or outputs.tacticalIntelligence
        if tactical_baseline:
            built_docs, built_warnings = self._baseline.build(
                match_id=request.matchId,
                team_id=request.teamId,
                team_name=request.teamName,
                payload=tactical_baseline,
            )
            documents.extend(built_docs)
            warnings.extend(built_warnings)
        else:
            warnings.append("tacticalBaseline output missing.")

        decision_quality = outputs.decisionQuality
        if decision_quality:
            built_docs, built_warnings = self._decision.build(
                match_id=request.matchId,
                team_id=request.teamId,
                team_name=request.teamName,
                payload=decision_quality,
                top_n_phases=request.options.topNPhases,
                max_player_docs=self._max_player_documents,
            )
            documents.extend(built_docs)
            warnings.extend(built_warnings)
        else:
            warnings.append("decisionQuality output missing.")

        player_profiles = outputs.playerProfiles
        if player_profiles:
            built_docs, built_warnings = self._profile.build(
                match_id=request.matchId,
                team_id=request.teamId,
                team_name=request.teamName,
                profiles=player_profiles,
            )
            documents.extend(built_docs)
            warnings.extend(built_warnings)
        else:
            warnings.append("playerProfiles output missing.")

        pressing = outputs.pressing
        if pressing:
            built_docs, built_warnings = self._pressing.build(
                match_id=request.matchId,
                team_id=request.teamId,
                team_name=request.teamName,
                payload=pressing,
            )
            documents.extend(built_docs)
            warnings.extend(built_warnings)
        else:
            warnings.append("pressing output missing.")

        passing_network = outputs.passingNetwork or outputs.passingNewtork
        if passing_network:
            built_docs, built_warnings = self._passing.build(
                match_id=request.matchId,
                team_id=request.teamId,
                team_name=request.teamName,
                payload=passing_network,
            )
            documents.extend(built_docs)
            warnings.extend(built_warnings)
        else:
            warnings.append("passingNetwork output missing.")

        line_breaks = outputs.lineBreaks or outputs.line_breaks
        if line_breaks:
            built_docs, built_warnings = self._line_breaks.build(
                match_id=request.matchId,
                team_id=request.teamId,
                team_name=request.teamName,
                payload=line_breaks,
            )
            documents.extend(built_docs)
            warnings.extend(built_warnings)
        else:
            warnings.append("lineBreaks output missing.")

        ball_losses = outputs.ballLosses or outputs.ball_losses
        if ball_losses:
            built_docs, built_warnings = self._ball_losses.build(
                match_id=request.matchId,
                team_id=request.teamId,
                team_name=request.teamName,
                payload=ball_losses,
            )
            documents.extend(built_docs)
            warnings.extend(built_warnings)
        else:
            warnings.append("ballLosses output missing.")

        attacking_patterns = outputs.attackingPatterns or outputs.attacking_patterns
        if attacking_patterns:
            built_docs, built_warnings = self._attacking_patterns.build(
                match_id=request.matchId,
                team_id=request.teamId,
                team_name=request.teamName,
                payload=attacking_patterns,
            )
            documents.extend(built_docs)
            warnings.extend(built_warnings)
        else:
            warnings.append("attackingPatterns output missing.")

        deduped_documents = self._deduplicate_doc_ids(documents)
        return deduped_documents, warnings

    @staticmethod
    def _deduplicate_doc_ids(documents: list[RagDocument]) -> list[RagDocument]:
        counts = defaultdict(int)
        deduped: list[RagDocument] = []
        for doc in documents:
            counts[doc.docId] += 1
            if counts[doc.docId] == 1:
                deduped.append(doc)
                continue
            new_id = f"{doc.docId}_{slugify(str(counts[doc.docId]))}"
            deduped.append(doc.model_copy(update={"docId": new_id}))
        return deduped
