#!/usr/bin/env python3
"""Run a CI diagnostic and expose a bounded error annotation on failure.

Only use for non-secret audit commands. Successful and failed output remains
in the normal Actions log; a sanitized tail makes failures diagnosable when
log artifact download is unavailable. The underlying exit status is preserved.
"""
import subprocess
import sys


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: ci_checked.py COMMAND [ARG ...]")
    result = subprocess.run(sys.argv[1:], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    print(result.stdout, end="")
    if result.returncode:
        tail = result.stdout[-3000:].replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
        name = " ".join(sys.argv[1:3]).replace("%", "%25").replace(",", " ")
        print(f"::error file=scripts/ci_checked.py,line=1,title={name} failed::{tail}")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
