from __future__ import annotations

from pathlib import Path

from app.builders.club_knowledge_builder import ClubKnowledgeDocumentBuilder
from app.core.errors import BadRequestError, InternalServerError
from app.schemas.documents import RagDocument
from app.schemas.input_bundle import IndexClubKnowledgeRequest


class ClubKnowledgeService:
    def __init__(self) -> None:
        self._builder = ClubKnowledgeDocumentBuilder()
        self._project_root = Path(__file__).resolve().parents[2]

    def build_documents(self, request: IndexClubKnowledgeRequest) -> tuple[list[RagDocument], list[str]]:
        pdf_path = self._resolve_pdf_path(request.pdfPath)
        pages, extract_warnings = self._extract_pdf_pages(
            pdf_path=pdf_path,
            max_pages=request.options.maxPages,
        )
        docs, build_warnings = self._builder.build(
            club_key=request.clubKey,
            team_id=request.teamId,
            team_name=request.teamName,
            pages=pages,
            max_chars_per_page=request.options.maxCharsPerPage,
        )
        warnings = extract_warnings + build_warnings
        if not docs:
            raise BadRequestError("No club knowledge documents generated from PDF.")
        return docs, warnings

    def _resolve_pdf_path(self, raw_path: str) -> Path:
        candidate = Path(raw_path)
        if not candidate.is_absolute():
            candidate = (self._project_root / candidate).resolve()
        if not candidate.exists():
            raise BadRequestError(f"PDF file not found: {candidate}")
        if candidate.suffix.lower() != ".pdf":
            raise BadRequestError(f"Expected a .pdf file, got: {candidate.name}")
        return candidate

    @staticmethod
    def _extract_pdf_pages(
        *,
        pdf_path: Path,
        max_pages: int | None,
    ) -> tuple[list[dict[str, int | str]], list[str]]:
        warnings: list[str] = []
        try:
            from pypdf import PdfReader
        except Exception as exc:  # pragma: no cover - dependency path
            raise InternalServerError(
                "pypdf is not installed. Add it to requirements and install dependencies."
            ) from exc

        try:
            reader = PdfReader(str(pdf_path))
        except Exception as exc:
            raise InternalServerError(f"Failed to open PDF file: {pdf_path}") from exc

        total_pages = len(reader.pages)
        limit = min(total_pages, max_pages) if max_pages is not None else total_pages
        extracted: list[dict[str, int | str]] = []
        for idx in range(limit):
            page_number = idx + 1
            page = reader.pages[idx]
            text = (page.extract_text() or "").strip()
            if not text:
                warnings.append(f"PDF page {page_number} has no extractable text.")
                continue
            extracted.append({"page": page_number, "text": text})
        return extracted, warnings
