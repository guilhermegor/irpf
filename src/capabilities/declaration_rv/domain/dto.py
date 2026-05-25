"""DTOs for the declaration_rv capability."""

from __future__ import annotations

from typing import TypedDict


class DeclarationReportDTO(TypedDict):
    """Output DTO: declaration text and the base year it covers.

    Attributes
    ----------
    int_year : int
        IRPF base year (e.g. 2024).
    str_report : str
        Full declaration text, ready to be written to a ``.txt`` file.
    """

    int_year: int
    str_report: str
