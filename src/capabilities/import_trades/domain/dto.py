"""DTOs for the import_trades capability."""

from __future__ import annotations

from typing import TypedDict


class ImportResultDTO(TypedDict):
    """Result of a single trade import job.

    Attributes
    ----------
    table_name : str
        Name of the target PostgreSQL table.
    rows_processed : int
        Number of rows inserted (duplicates skipped).
    status : str
        Outcome string, e.g. ``"ok"`` or ``"error"``.
    """

    table_name: str
    rows_processed: int
    status: str
