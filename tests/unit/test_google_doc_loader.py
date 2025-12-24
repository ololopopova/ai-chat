"""Unit тесты для GoogleDocLoader."""

import pytest

from src.core.exceptions import IngestError
from src.services.ingest.google_doc_loader import GoogleDocLoader


class TestGoogleDocLoader:
    """Тесты для GoogleDocLoader."""

    def test_extract_doc_id_standard_url(self) -> None:
        """Извлечение DOC_ID из стандартного URL."""
        loader = GoogleDocLoader()
        url = "https://docs.google.com/document/d/ABC123xyz/edit"
        doc_id = loader.extract_doc_id(url)
        assert doc_id == "ABC123xyz"

    def test_extract_doc_id_with_tab(self) -> None:
        """Извлечение DOC_ID из URL с параметром tab."""
        loader = GoogleDocLoader()
        url = "https://docs.google.com/document/d/10UelJwksL3T57zC4vGvgjyq_ePlzr_e7HdmJgciM3Wk/edit?tab=t.0"
        doc_id = loader.extract_doc_id(url)
        assert doc_id == "10UelJwksL3T57zC4vGvgjyq_ePlzr_e7HdmJgciM3Wk"

    def test_extract_doc_id_without_edit(self) -> None:
        """Извлечение DOC_ID из URL без /edit."""
        loader = GoogleDocLoader()
        url = "https://docs.google.com/document/d/XYZ789/view"
        doc_id = loader.extract_doc_id(url)
        assert doc_id == "XYZ789"

    def test_extract_doc_id_invalid_url(self) -> None:
        """Ошибка при невалидном URL."""
        loader = GoogleDocLoader()
        url = "https://example.com/document/123"
        with pytest.raises(IngestError, match="Invalid Google Doc URL"):
            loader.extract_doc_id(url)

    def test_build_export_url(self) -> None:
        """Построение export URL."""
        loader = GoogleDocLoader()
        url = "https://docs.google.com/document/d/ABC123/edit"
        export_url = loader.build_export_url(url)
        assert export_url == "https://docs.google.com/document/d/ABC123/export?format=html"

    def test_extract_doc_id_case_insensitive(self) -> None:
        """Извлечение DOC_ID с разным регистром."""
        loader = GoogleDocLoader()
        url = "https://DOCS.GOOGLE.COM/DOCUMENT/d/TestID123/edit"
        doc_id = loader.extract_doc_id(url)
        assert doc_id == "TestID123"
