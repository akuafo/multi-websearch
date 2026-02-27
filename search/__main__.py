from __future__ import annotations

import sys
import time

from dotenv import load_dotenv

load_dotenv()

from . import search


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m src.search <query>")
        sys.exit(1)

    query = " ".join(sys.argv[1:])
    print(f"Searching: {query}\n")

    start = time.time()
    result = search(query)
    elapsed = time.time() - start

    print("=" * 60)
    print("SYNTHESIS")
    print("=" * 60)
    print(result.synthesis)
    print()

    print("=" * 60)
    print("PROVIDER DETAILS")
    print("=" * 60)
    for pr in result.provider_results:
        status = "OK" if not pr.error else f"ERROR: {pr.error}"
        print(f"  {pr.provider}: {status} ({len(pr.content)} chars, {len(pr.sources)} sources)")
    print()

    if result.errors:
        print("Errors:", "; ".join(result.errors))

    print(f"Model: {result.model}")
    print(f"Tokens: {result.tokens_in} in / {result.tokens_out} out")
    print(f"Time: {elapsed:.1f}s")


if __name__ == "__main__":
    main()
