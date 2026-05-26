"""Persistence entities for the import_trades capability."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass
class TradeImportJob:
    """Describes a single import job: one xlsx file maps to one DB table.

    Attributes
    ----------
    file_name_like : str
        Glob pattern used to locate the source Excel file.
    dict_dtypes : dict[str, Any]
        Column name → dtype mapping for reading the Excel file.
    table_name : str
        Target PostgreSQL table name.
    dt_date_ref : date or None
        Reference date injected as ``data_pregao`` for annual reports.
    """

    file_name_like: str
    dict_dtypes: dict[str, Any]
    table_name: str
    dt_date_ref: date | None = field(default=None)
