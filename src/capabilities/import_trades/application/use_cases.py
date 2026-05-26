"""Use cases for the import_trades capability."""

from __future__ import annotations

from src.capabilities.import_trades.domain.dto import ImportResultDTO
from src.capabilities.import_trades.domain.entities import TradeImportJob
from src.capabilities.import_trades.domain.ports import TradeImportRepository


class ImportTrades:
    """Import a batch of B3 Excel files into PostgreSQL.

    Parameters
    ----------
    cls_repo : TradeImportRepository
        Repository port that handles file reading and DB insertion.
    """

    def __init__(self, cls_repo: TradeImportRepository) -> None:
        """Initialise with the given repository.

        Parameters
        ----------
        cls_repo : TradeImportRepository
            Repository port that handles file reading and DB insertion.
        """
        self._cls_repo = cls_repo

    def execute(self, list_jobs: list[TradeImportJob]) -> list[ImportResultDTO]:
        """Run every import job in order and return results.

        Parameters
        ----------
        list_jobs : list[TradeImportJob]
            Ordered list of import jobs to process.

        Returns
        -------
        list[ImportResultDTO]
            One result dict per job.
        """
        return [self._cls_repo.import_job(cls_job) for cls_job in list_jobs]
