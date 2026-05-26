"""Ports for the declaration_rv capability."""

from __future__ import annotations

from typing import Protocol

from src.capabilities.declaration_rv.domain.entities import DeclarationData


class DeclarationRepository(Protocol):
    """Outbound port: fetch all data needed for one IRPF year.

    Parameters
    ----------
    int_year : int
        IRPF base year to query.

    Returns
    -------
    DeclarationData
        Aggregated positions and income events for the given year.
    """

    def fetch(self, int_year: int) -> DeclarationData:
        """Fetch declaration data for the given base year.

        Parameters
        ----------
        int_year : int
            IRPF base year to query.

        Returns
        -------
        DeclarationData
            Aggregated positions and income events.
        """
        ...
