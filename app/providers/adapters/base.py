"""Abstract base class for external data-source adapters.

Concrete adapters (e.g. for SaaS APIs, file stores, databases) should
subclass ``BaseAdapter`` and implement all abstract methods.  This keeps
the ingestion pipeline decoupled from any specific vendor or data format.
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseAdapter(ABC):
    """Contract that every data-source adapter must fulfil."""

    @abstractmethod
    async def test_connection(self) -> bool:
        """Verify that the external data source is reachable.

        Returns
        -------
        bool
            ``True`` when the connection succeeds, ``False`` otherwise.
        """
        ...

    @abstractmethod
    async def fetch_records(self, **kwargs: Any) -> list[dict[str, Any]]:
        """Retrieve raw records from the data source.

        Parameters
        ----------
        **kwargs:
            Adapter-specific query parameters (pagination tokens, filters,
            date ranges, etc.).

        Returns
        -------
        list[dict[str, Any]]
            A list of raw records in the source's native schema.
        """
        ...

    @abstractmethod
    async def normalize_record(self, raw_record: dict[str, Any]) -> dict[str, Any]:
        """Transform a single raw record into the internal canonical schema.

        Parameters
        ----------
        raw_record:
            One record as returned by :meth:`fetch_records`.

        Returns
        -------
        dict[str, Any]
            The record converted to the internal schema expected by the
            indexing / embedding pipeline.
        """
        ...
