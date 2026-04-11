from __future__ import annotations

import argparse
from typing import Any

from coding_deepgent.app import agent_loop
from coding_deepgent.rendering import extract_text


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the coding-deepgent cumulative s03 agent")
    parser.add_argument("--prompt", help="Run one prompt and exit")
    return parser


def run_once(prompt: str, *, history: list[dict[str, Any]] | None = None) -> str:
    transcript = history if history is not None else []
    transcript.append({"role": "user", "content": prompt})
    return agent_loop(transcript)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.prompt:
        final = run_once(args.prompt)
        print(extract_text(final) or "(no response)")
        return 0

    history: list[dict[str, Any]] = []
    while True:
        try:
            query = input("[36mcoding-deepgent >> [0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in {"", "q", "exit"}:
            break
        final = run_once(query, history=history)
        print(extract_text(final) or "(no response)")
        print()

    return 0


def cli() -> None:
    raise SystemExit(main())


if __name__ == "__main__":  # pragma: no cover
    cli()
