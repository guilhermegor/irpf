"""Ports for the import_trades capability."""

from __future__ import annotations

from typing import Protocol

from src.capabilities.import_trades.domain.dto import ImportResultDTO
from src.capabilities.import_trades.domain.entities import TradeImportJob


class TradeImportRepository(Protocol):
    """Outbound port: persist one import job.

    Parameters
    ----------
    cls_job : TradeImportJob
        Job describing the source file and target table.

    Returns
    -------
    ImportResultDTO
        Result with row count and status.
    """

    def import_job(self, cls_job: TradeImportJob) -> ImportResultDTO:
        """Execute one import job.

        Parameters
        ----------
        cls_job : TradeImportJob
            Job describing the source file and target table.

        Returns
        -------
        ImportResultDTO
            Result with row count and status.
        """
        ...
