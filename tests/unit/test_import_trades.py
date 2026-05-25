"""Unit tests for ImportTrades use case."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.capabilities.import_trades.application.use_cases import ImportTrades
from src.capabilities.import_trades.domain.dto import ImportResultDTO
from src.capabilities.import_trades.domain.entities import TradeImportJob


def test_import_trades_delegates_to_repo() -> None:
    """ImportTrades.execute calls import_job once and returns its result."""
    cls_repo = MagicMock()
    cls_repo.import_job.return_value = ImportResultDTO(
        table_name="b3_movimentacao", rows_processed=42, status="ok"
    )
    list_jobs = [
        TradeImportJob(
            file_name_like="movimentacao-2025*.xlsx",
            dict_dtypes={"entrada_saida": str},
            table_name="b3_movimentacao",
        )
    ]
    list_results = ImportTrades(cls_repo).execute(list_jobs)
    cls_repo.import_job.assert_called_once()
    assert list_results[0]["rows_processed"] == 42


def test_import_trades_empty_jobs_returns_empty_list() -> None:
    """ImportTrades.execute returns an empty list when given no jobs."""
    cls_repo = MagicMock()
    list_results = ImportTrades(cls_repo).execute([])
    assert list_results == []
    cls_repo.import_job.assert_not_called()
