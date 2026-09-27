"""Portable filename sanitisation.

The goal is a single function that produces a filename safe on Windows,
macOS, and Linux simultaneously. We replace every character that any of
the three major operating systems dislike in a filename with an
underscore, then collapse runs of underscores so the result stays
readable, and finally enforce length and reserved-name rules.

Design decisions (stated plainly so the tests can lock them down):

* Replacement character is the underscore. It is legal on all three
  platforms and visually unobtrusive.
* We collapse runs of the replacement character into a single one so
  that ``a//b`` becomes ``a_b``, not ``a__b``.
* We strip leading and trailing dots and spaces. A trailing dot or
  space is silently dropped by Windows Explorer, which is a data-loss
  bug waiting to happen; a leading dot makes the file hidden on Unix.
  Stripping is the safest single behaviour.
* Windows reserved names (CON, PRN, AUX, NUL, COM1..9, LPT1..9) are
  suffixed with ``_`` so they are no longer reserved. We check the
  stem (the part before the last dot), case-insensitively, because
  Windows checks case-insensitively.
* We cap the total length at 255 bytes when encoded as UTF-8, which is
  the common denominator across modern filesystems. Truncation happens
  on a character boundary so we never emit a split surrogate.
* An empty result after all of the above becomes ``_``. We never return
  an empty string, because an empty filename is invalid everywhere.
* ``sanitize_path_segment`` is the same operation but also rejects
  ``.`` and ``..`` as whole-segment results, which would traverse
  directories. It is intended for a single path component, not a full
  path.
"""

from __future__ import annotations

import re

# Characters that are illegal in filenames on at least one of the
# target platforms. We use a set for fast membership testing and build
# a regex from it for the replacement pass.
#
# Windows forbids: < > : " / \ | ? * and code points 0..31
# macOS forbids: : (HFS+ uses colon as the path separator historically)
#               and / (the path separator)
# Linux forbids: / and NUL
#
# The union is: control characters 0..31, NUL (0x00, already in 0..31),
# and the punctuation set below. NUL (0x00) is included in range(0,32).
_ILLEGAL_CHARS: set[str] = {chr(c) for c in range(0, 32)}
_ILLEGAL_CHARS.update({"<", ">", ":", '"', "/", "\\", "|", "?", "*"})

# Pre-compiled pattern: any single illegal character.
_ILLEGAL_RE = re.compile("[" + re.escape("".join(sorted(_ILLEGAL_CHARS))) + "]")

# Runs of underscores (the replacement char) to collapse.
_UNDERSCORE_RUN_RE = re.compile(r"_+")

# Windows reserved names, case-insensitive. We match the stem against
# this set. COM1..COM9 and LPT1..LPT9 are generated.
_RESERVED_WINDOWS: set[str] = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
}
for _i in range(1, 10):
    _RESERVED_WINDOWS.add(f"COM{_i}")
    _RESERVED_WINDOWS.add(f"LPT{_i}")

# 255 bytes is the maximum filename length on ext4, HFS+, and NTFS for
# practical purposes. We measure in UTF-8 bytes, not characters, because
# that is what the filesystem enforces.
_MAX_BYTES = 255


def _replace_illegal(name: str) -> str:
    """Replace every illegal character with an underscore."""
    return _ILLEGAL_RE.sub("_", name)


def _collapse_underscores(name: str) -> str:
    """Collapse runs of underscores into a single underscore."""
    return _UNDERSCORE_RUN_RE.sub("_", name)


def _strip_edges(name: str) -> str:
    """Strip leading/trailing dots and spaces.

    A trailing dot is dropped silently by Windows, which loses data. A
    leading dot hides the file on Unix. Leading/trailing spaces are a
    nuisance on every platform.
    """
    return name.strip(". ")


def _handle_reserved(name: str) -> str:
    """If the stem is a Windows reserved name, append an underscore."""
    if not name:
        return name
    # Split on the last dot only, so an extension is preserved.
    if "." in name:
        stem, dot, ext = name.rpartition(".")
    else:
        stem, dot, ext = name, "", ""
    if stem.upper() in _RESERVED_WINDOWS:
        # Insert the underscore after the stem, preserving any extension.
        return stem + "_" + dot + ext
    return name


def _truncate(name: str) -> str:
    """Truncate to at most _MAX_BYTES UTF-8 bytes on a character boundary."""
    encoded = name.encode("utf-8")
    if len(encoded) <= _MAX_BYTES:
        return name
    # Cut the byte string, then decode with errors="ignore" so we drop
    # any trailing partial multi-byte sequence rather than raising.
    truncated = encoded[:_MAX_BYTES].decode("utf-8", errors="ignore")
    return truncated


def sanitize_filename(name: str) -> str:
    """Return a portable, safe filename derived from *name*.

    The result is guaranteed to be non-empty, at most 255 UTF-8 bytes,
    and free of characters illegal on Windows, macOS, or Linux. Windows
    reserved names are neutralised. Leading and trailing dots and
    spaces are removed.

    This function operates on a bare filename, not a path. Any ``/`` or
    ``\\`` in the input is treated as an illegal character and replaced
    with an underscore; it is not interpreted as a path separator.
    """
    if not isinstance(name, str):
        raise TypeError("name must be a string")

    # Normalise NULs and control characters first, then punctuation.
    cleaned = _replace_illegal(name)
    cleaned = _collapse_underscores(cleaned)
    cleaned = _strip_edges(cleaned)
    cleaned = _handle_reserved(cleaned)
    cleaned = _truncate(cleaned)
    # Truncation may expose a trailing dot again (rare, but possible if
    # a multi-byte sequence was cut), so strip once more.
    cleaned = _strip_edges(cleaned)
    if not cleaned:
        return "_"
    return cleaned


def sanitize_path_segment(name: str) -> str:
    """Like :func:`sanitize_filename`, but also reject ``.`` and ``..``.

    Use this when the input is meant to become a single component of a
    path. If sanitisation would produce ``.`` or ``..`` — which would
    traverse the directory tree — an underscore is returned instead.
    """
    cleaned = sanitize_filename(name)
    if cleaned in (".", ".."):
        return "_"
    return cleaned
