"""Text chunking utilities for the ingestion pipeline."""


def chunk_text(
    text: str,
    *,
    chunk_size: int = 400,
    overlap: int = 50,
) -> list[str]:
    """Split *text* into overlapping word-based chunks.

    Parameters
    ----------
    text:
        The full document text to split.
    chunk_size:
        Target number of words per chunk (300–500 range recommended).
    overlap:
        Number of words to overlap between consecutive chunks.

    Returns
    -------
    list[str]
        Ordered list of text chunks.  Empty input yields an empty list.
    """
    words = text.split()
    if not words:
        return []

    chunks: list[str] = []
    start = 0

    while start < len(words):
        end = start + chunk_size
        chunk_words = words[start:end]
        chunks.append(" ".join(chunk_words))

        # Advance by (chunk_size - overlap) so consecutive chunks share
        # *overlap* words at the boundary.
        step = chunk_size - overlap
        if step < 1:
            step = 1
        start += step

    return chunks
