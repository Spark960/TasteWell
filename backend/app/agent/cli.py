"""CLI runner — a venue brief in, a grounded concept brief out (P2 gate).

Usage:
  py -3.12 -m app.agent.cli "natural wine bar" --region Brooklyn --audience millennials
  py -3.12 -m app.agent.cli "listening bar" --region "Williamsburg" --audience millennials
  py -3.12 -m app.agent.cli "..." --mode generic      # Qloo-off (side-by-side)

Outputs: concept brief JSON (--out) + trace.json (--trace). Exit codes:
0 ok · 2 needs_input · 3 error/aborted. On a terminal, needs_input
candidates get an interactive pick and the run continues with that id.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import uuid
from typing import Awaitable, Callable

from app.agent.loop import AGGREGATE_DISCLAIMER, AgentRunner, BriefRequest
from app.agent.provider import LlmProvider, ProviderConfigError
from app.agent.tools import GroundedTools
from app.qloo.mcp_client import QlooMcpClient
from app.qloo.redact import register_secret
from app.settings import MissingCredential, get_settings
from app.trace import Trace

log = logging.getLogger("tastewell.cli")

EXIT_OK, EXIT_NEEDS_INPUT, EXIT_ERROR = 0, 2, 3


def make_chooser(
    interactive: bool, forced_pick: str = ""
) -> Callable[[list[dict]], Awaitable[str | None]]:
    async def choose(candidates: list[dict]) -> str | None:
        if forced_pick:
            return f"{forced_pick} (the user's pre-picked Qloo candidate id)"
        if not interactive or not sys.stdin.isatty():
            return None
        print("\nNEEDS INPUT — pick the Qloo candidate you meant:", file=sys.stderr)
        for i, c in enumerate(candidates, 1):
            line = (
                f"  [{i}] {c.get('name')} — type={c.get('type')} "
                f"popularity={c.get('popularity')}"
            )
            print(line, file=sys.stderr)
        try:
            raw = input("Pick number or paste id (empty = skip): ").strip()
        except (EOFError, KeyboardInterrupt):
            return None
        if not raw:
            return None
        if raw.isdigit() and 1 <= int(raw) <= len(candidates):
            c = candidates[int(raw) - 1]
            return f"{c.get('id')} (name: {c.get('name')})"
        return f"{raw} (the user's pasted Qloo id)"

    return choose


async def run(args: argparse.Namespace) -> int:
    from app.trace import now_iso

    run_id = f"{now_iso()[:19].replace(':', '').replace('-', '')}-{uuid.uuid4().hex[:6]}"
    trace = Trace(run_id=run_id)
    settings = get_settings()

    tools: GroundedTools | None = None
    if args.mode != "generic":
        try:
            key = settings.require_qloo_key()
        except MissingCredential as exc:
            print(f"MISSING CREDENTIAL: {exc}", file=sys.stderr)
            return EXIT_ERROR
        if key:
            register_secret(key)
        client = QlooMcpClient(
            qloo_bin=settings.qloo_bin,
            api_key=key,
            base_urls=(settings.qloo_base_url, settings.qloo_trusted_base_url),
        )
        async with client as c:
            if not c.tools:
                print("Harness exposed no MCP tools — check qloo --version.",
                      file=sys.stderr)
                return EXIT_ERROR
            log.info("mcp tools ready: %s", ", ".join(sorted(c.tools)))
            trace.log("status", message="readiness_ok", mode="mcp",
                      tools=sorted(c.tools))
            tools = GroundedTools(client=c, trace=trace)
            return await _run_agent(args, trace, tools, run_id)
    return await _run_agent(args, trace, None, run_id)


async def _run_agent(
    args: argparse.Namespace,
    trace: Trace,
    tools: GroundedTools | None,
    run_id: str,
) -> int:
    settings = get_settings()
    try:
        provider = LlmProvider(
            provider=settings.llm_provider,
            model=settings.llm_model,
            api_key=args.llm_api_key_override or _llm_key(settings),
        )
    except ProviderConfigError as exc:
        print(f"MISSING CREDENTIAL: {exc}", file=sys.stderr)
        return EXIT_ERROR
    runner = AgentRunner(
        provider=provider,
        tools=tools,
        trace=trace,
        chooser=make_chooser(
            interactive=not args.non_interactive, forced_pick=args.pick
        ),
    )
    req = BriefRequest(
        brief=args.brief, region=args.region, audience=args.audience,
        extras={"city": args.city} if args.city else {},
    )
    outcome = await runner.run(req)
    trace.dump(args.trace)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(outcome.brief, f, indent=2, ensure_ascii=False)
    _print_brief(outcome.brief, run_id)
    if outcome.status == "needs_input":
        print("\nNeeds your pick → rerun with the id, or re-pick interactively.",
              file=sys.stderr)
        return EXIT_NEEDS_INPUT
    if outcome.status != "ok":
        print(f"\nRun did not complete: {outcome.status}", file=sys.stderr)
        return EXIT_ERROR
    return EXIT_OK


def _llm_key(settings) -> str:
    mapping = {
        "gemini": settings.gemini_api_key,
        "openai": settings.openai_api_key,
        "groq": getattr(settings, "groq_api_key", ""),
        "openrouter": getattr(settings, "openrouter_api_key", ""),
    }
    key = mapping.get(get_settings().llm_provider, "")
    if key:
        register_secret(key)
    return key


_SECTION_TITLES = {
    "audience_profile": "AUDIENCE PROFILE",
    "menu_tilt": "MENU TILT",
    "music_programming": "MUSIC / PROGRAMMING",
    "adjacent_brands": "ADJACENT BRANDS",
    "tag_themes": "TAG THEMES",
    "honest_absences": "HONEST ABSENCES (abstained)",
}


def _print_brief(brief: dict, run_id: str) -> None:
    mode = brief.get("mode", "?")
    print(f"\n=== Tastewell concept brief (run {run_id}, mode={mode}) ===")
    for key, title in _SECTION_TITLES.items():
        val = brief.get(key)
        if not val:
            continue
        print(f"\n{title}")
        if isinstance(val, list):
            for item in val:
                print(f"  • {item}")
        else:
            print(f"  {val}")
    for d in brief.get("disclaimers", []):
        print(f"\n[{d}]")
    ev = brief.get("evidence") or []
    if ev:
        print(f"\nEvidence: {len(ev)} tool call(s) — "
              + ", ".join(f"{e['tool']}:{e['status']}" for e in ev))
    else:
        print("\nEvidence: none — this brief is ungrounded.")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tastewell",
        description="Venue taste agent grounded in Qloo (MCP route).",
    )
    p.add_argument("brief", help="venue concept, e.g. 'natural wine bar'")
    p.add_argument("--region", default="", help="neighborhood / city")
    p.add_argument("--audience", default="", help="target audience descriptor")
    p.add_argument("--city", default="")
    p.add_argument("--mode", choices=["grounded", "generic"], default="grounded",
                   help="generic = Qloo-off (side-by-side demo)")
    p.add_argument("--out", default="tastewell-brief.json")
    p.add_argument("--trace", default="trace.json")
    p.add_argument("--pick", default="",
                   help="pre-answer a needs_input prompt with this Qloo id")
    p.add_argument("--non-interactive", action="store_true",
                   help="never prompt on needs_input")
    p.add_argument("--llm-api-key-override", default="")
    return p


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, stream=sys.stderr,
                        format="%(levelname)s %(name)s: %(message)s")
    logging.getLogger("tastewell.qloo").setLevel(logging.WARNING)
    logging.getLogger("tastewell.cli").setLevel(logging.INFO)
    args = build_parser().parse_args(argv)
    sys.exit(asyncio.run(run(args)))


if __name__ == "__main__":
    main()
