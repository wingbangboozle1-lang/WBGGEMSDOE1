#!/usr/bin/env python3
"""Disabled historical Focus-9 synthetic null generator.

The frozen result already fails the literal registry gate. Its former private
writer and implementation remain available in Git history for audit, not reuse.
This entry point must not create dots, overwrite receipts, or approve submissions.
"""


def main():
    raise SystemExit(
        "STOP: the Focus-9 synthetic lane is frozen and fails the literal "
        "registry gate. Existing files are research only; do not submit."
    )


if __name__ == "__main__":
    main()
