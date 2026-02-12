"""SHA-256 hashing utilities for file deduplication."""

import hashlib


def compute_file_hash(content: bytes) -> str:
    """Compute SHA-256 hash of file content.

    Args:
        content: Raw bytes of the file

    Returns:
        Hex string of SHA-256 hash (64 characters)
    """
    return hashlib.sha256(content).hexdigest()


def compute_string_hash(text: str) -> str:
    """Compute SHA-256 hash of text string.

    Args:
        text: String content

    Returns:
        Hex string of SHA-256 hash (64 characters)
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
