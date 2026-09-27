# Safe Filename Sanitizer

A single-purpose library that takes an arbitrary string and returns a filename safe to use on Windows, macOS, and Linux.

## Usage

```python
from safe_filename_sanitizer import sanitize_filename, sanitize_path_segment

sanitize_filename('my file: name?.txt')   # 'my file_ name_.txt'
sanitize_filename('CON')                  # 'CON_'
sanitize_path_segment('..')                # '_'
```

## Why this exists

Saving user-supplied text as a filename is a recurring source of bugs. Windows forbids a dozen punctuation characters and a set of reserved names (CON, PRN, COM1, etc.); macOS historically dislikes colons; Linux only forbids slashes and NUL. Targeting the intersection of all three means the resulting filename works everywhere without per-platform branches.

The trade-off is that the library is conservative: it replaces characters rather than trying to transliterate them (ä does not become "ae"), and it strips leading and trailing dots unconditionally. That keeps the implementation small and dependency-free at the cost of some cosmetic fidelity.

## Edge cases you will hit

- A name that is entirely illegal characters (e.g. `<>:?*`) collapses to a single underscore `_`, never an empty string.
- Windows reserved names like `CON.txt` become `CON_.txt` — the extension is preserved.
- Names longer than 255 UTF-8 bytes are truncated on a character boundary, so multi-byte sequences are never split.
- `sanitize_filename` treats `/` and `\` as illegal characters and replaces them with underscores; it does not split a path. Use `sanitize_path_segment` on each component individually if you are building a path.

## Exports

- `sanitize_filename(name: str) -> str`
- `sanitize_path_segment(name: str) -> str`

## Running the tests

```
PYTHONPATH=src python -m unittest discover -s tests
```
