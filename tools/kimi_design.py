"""Generate dashboard screen mockups with Kimi K3 through ZenMux (OpenAI-compatible API).

Usage (from eyewear-trends/, with the backend venv; key in .env or ZENMUX_API_KEY):
    backend/.venv/Scripts/python tools/kimi_design.py B                  # medium effort, 20k reasoning cap
    backend/.venv/Scripts/python tools/kimi_design.py B C D E F
    backend/.venv/Scripts/python tools/kimi_design.py B --effort low --reasoning-max 12000
    backend/.venv/Scripts/python tools/kimi_design.py B --effort default  # model's own default (can think very long)

Default protocol is ZenMux's Anthropic Messages endpoint (as the ZenMux playground does), where
--reasoning-max becomes the thinking budget. --protocol openai uses chat completions + --effort.

Screens B-F automatically get design/kimi/A.html attached as the reference implementation,
so they reuse its CSS and app shell (brief section 8).

Cost note: stopping this script (Ctrl+C) does NOT stop the provider - it keeps generating and
billing up to max_tokens. The token caps are the real cost limit.

Output: design/kimi/<screen>.html (open in a browser). The logo is copied next to it.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
BRIEF = ROOT / "docs" / "design-brief.md"
OUT = ROOT / "design" / "kimi"
# Two ZenMux protocols. "anthropic" is what the ZenMux playground uses for Kimi K3, and its
# thinking budget (budget_tokens) is a first-class parameter; the OpenAI-side
# reasoning.max_tokens was ignored for Kimi K3 in practice (screen B reasoned past it).
BASE_URLS = {"anthropic": "https://zenmux.ai/api/anthropic", "openai": "https://zenmux.ai/api/v1"}
MODEL = os.environ.get("KIMI_MODEL", "moonshotai/kimi-k3")
MAX_TOKENS = int(os.environ.get("KIMI_MAX_TOKENS", "50000"))  # reasoning (<= 20k) + a long HTML file (~20-30k)
IDLE_TIMEOUT = 180  # seconds without any streamed data before giving up (no cap on total time)

SCREENS = {
    "A": "A. Vue d'ensemble",
    "B": "B. Tendances (onglet Formes actif)",
    "C": "C. Détail d'une tendance (Œil de chat)",
    "D": "D. Demande (onglet Formes actif)",
    "E": "E. Sources",
    "F": "F. Rapport PDF",
}


def extract_html(content: str) -> str:
    """The ```html block; tolerate a missing closing fence when the reply was cut off."""
    match = re.search(r"```html\s*(.*?)(?:```|\Z)", content, re.DOTALL)
    return match.group(1) if match else content


def reasoning_params(effort: str, reasoning_max: int) -> dict:
    """ZenMux reasoning controls: `effort` asks for shorter thinking, `max_tokens` is the hard cap.

    Whether a given model honors them is up to the provider — watch the reasoning counter.
    """
    if effort == "default":
        return {}
    params: dict = {"reasoning_effort": effort, "reasoning": {"enabled": True, "effort": effort}}
    if reasoning_max:
        params["reasoning"]["max_tokens"] = reasoning_max
    return params


def anthropic_thinking(effort: str, reasoning_max: int) -> dict:
    """Anthropic-protocol thinking budget (>= 1024 and < max_tokens); effort 'default' sends none."""
    if effort == "default" or not reasoning_max:
        return {}
    return {"thinking": {"type": "enabled", "budget_tokens": max(1024, min(reasoning_max, MAX_TOKENS - 1024))}}


def parse_event(protocol: str, chunk: dict) -> list[tuple[str, str]]:
    """Normalize one streamed event to [("reasoning"|"content"|"finish"|"error"|"stop", value)]."""
    out: list[tuple[str, str]] = []
    if protocol == "anthropic":
        kind = chunk.get("type")
        if kind == "content_block_delta":
            delta = chunk.get("delta") or {}
            if delta.get("type") == "thinking_delta":
                out.append(("reasoning", delta.get("thinking", "")))
            elif delta.get("type") == "text_delta":
                out.append(("content", delta.get("text", "")))
        elif kind == "message_delta":
            reason = (chunk.get("delta") or {}).get("stop_reason")
            if reason:
                out.append(("finish", "length" if reason == "max_tokens" else reason))
        elif kind == "error":
            out.append(("error", json.dumps(chunk.get("error"))))
        elif kind == "message_stop":
            out.append(("stop", ""))
        return out
    if "error" in chunk:
        return [("error", json.dumps(chunk["error"]))]
    for choice in chunk.get("choices", []):
        delta = choice.get("delta") or {}
        out.append(("reasoning", delta.get("reasoning_content") or delta.get("reasoning") or ""))
        if delta.get("content"):
            out.append(("content", delta["content"]))
        if choice.get("finish_reason"):
            out.append(("finish", choice["finish_reason"]))
    return out


def generate(screen: str, client: httpx.Client, extra: dict | None = None, protocol: str = "openai") -> Path:
    prompt = BRIEF.read_text(encoding="utf-8")
    reference = OUT / "A.html"
    if screen != "A" and reference.exists():
        # Reuse screen A's design system and shell instead of re-deriving it (brief section 8).
        prompt += (
            "\n\n---\n\n## Reference implementation: screen A (approved)\n"
            "Reuse its <style> block, app shell and shell scripts verbatim, as described in section 8.\n\n"
            "```html\n" + reference.read_text(encoding="utf-8") + "\n```"
        )
    prompt += (
        f"\n\n---\n\n## Your task now\nBuild screen **{SCREENS[screen]}** as a single self-contained HTML file "
        "following every rule above (app shell included, the nav item for this screen active, working theme toggle)."
    )
    body = {"model": MODEL, "messages": [{"role": "user", "content": prompt}], "max_tokens": MAX_TOKENS, "stream": True, **(extra or {})}
    path = "/v1/messages" if protocol == "anthropic" else "/chat/completions"
    partial = OUT / f"{screen}.partial.html"
    content: list[str] = []
    reasoning_chars = 0
    finish_reason = None
    started = last_print = last_save = time.monotonic()

    def progress(final: bool = False) -> None:
        elapsed = int(time.monotonic() - started)
        html_chars = sum(map(len, content))
        phase = "writing HTML" if html_chars else ("reasoning" if reasoning_chars else "waiting for first token")
        line = f"  {phase:<24} reasoning {reasoning_chars:>7,} chars | html {html_chars:>7,} chars | {elapsed // 60}:{elapsed % 60:02d}"
        print("\r" + line, end="\n" if final else "", flush=True)

    try:
        with client.stream("POST", path, json=body) as resp:
            if resp.status_code >= 400:
                resp.read()
                # Show ZenMux's own explanation (quota, model access, key scope…) instead of a bare status code.
                sys.exit(f"\nZenMux returned HTTP {resp.status_code} for model {MODEL}:\n{resp.text[:2000]}")
            for line in resp.iter_lines():
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                except json.JSONDecodeError:
                    continue
                stop = False
                for kind, value in parse_event(protocol, chunk):
                    if kind == "error":
                        sys.exit(f"\nZenMux stream error: {value}")
                    elif kind == "reasoning":
                        reasoning_chars += len(value)
                    elif kind == "content":
                        content.append(value)
                    elif kind == "finish":
                        finish_reason = value
                    elif kind == "stop":
                        stop = True
                if stop:
                    break
                now = time.monotonic()
                if now - last_print >= 1:
                    progress()
                    last_print = now
                if content and now - last_save >= 5:
                    partial.write_text(extract_html("".join(content)), encoding="utf-8")
                    last_save = now
    except KeyboardInterrupt:
        progress(final=True)
        partial.write_text(extract_html("".join(content)), encoding="utf-8")
        sys.exit(f"Interrupted - partial output kept in {partial}")
    except httpx.TimeoutException:
        progress(final=True)
        if content:
            partial.write_text(extract_html("".join(content)), encoding="utf-8")
        sys.exit(f"No data from ZenMux for {IDLE_TIMEOUT}s - gave up. Partial output (if any): {partial}")
    progress(final=True)

    full = "".join(content)
    if not full.strip():
        sys.exit("The model finished without writing any HTML (only reasoning). Try again, or raise MAX_TOKENS.")
    if finish_reason == "length":
        print(f"  WARNING: hit the {MAX_TOKENS:,}-token output limit - the HTML is probably cut off at the end.")
    path = OUT / f"{screen}.html"
    path.write_text(extract_html(full), encoding="utf-8")
    partial.unlink(missing_ok=True)
    return path


def mask(key: str) -> str:
    return f"{key[:3]}...{key[-4:]} ({len(key)} chars)" if len(key) > 8 else f"<{len(key)} chars>"


def load_key() -> str | None:
    """Environment variable first, then ZENMUX_API_KEY=... in the git-ignored .env at the project root."""
    if key := os.environ.get("ZENMUX_API_KEY"):
        print(f"Using ZENMUX_API_KEY from the environment: {mask(key.strip())}")
        return key.strip()
    env_file = ROOT / ".env"
    if env_file.exists():
        raw = env_file.read_bytes()
        # PowerShell 5.1 `echo ... > .env` writes UTF-16 with a BOM; editors usually write UTF-8.
        encoding = "utf-16" if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else "utf-8-sig"
        for line in raw.decode(encoding).splitlines():
            name, _, value = line.partition("=")
            if name.strip() == "ZENMUX_API_KEY" and value.strip():
                key = value.strip().strip('"').strip("'")
                print(f"Using ZENMUX_API_KEY from {env_file}: {mask(key)}")
                return key
    return None


def main(screens: list[str], effort: str = "medium", reasoning_max: int = 20000, protocol: str = "anthropic") -> None:
    key = load_key()
    if not key:
        sys.exit(
            "ZENMUX_API_KEY not found. Either set it in THIS terminal "
            "(PowerShell: $env:ZENMUX_API_KEY = \"sk-...\" | Git Bash: export ZENMUX_API_KEY=\"sk-...\") "
            f"or add a line ZENMUX_API_KEY=sk-... to {ROOT / '.env'}"
        )
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "brand").mkdir(exist_ok=True)
    shutil.copy(ROOT / "frontend" / "public" / "brand" / "noe-noah-logo-coral.png", OUT / "brand")
    timeout = httpx.Timeout(connect=30, read=IDLE_TIMEOUT, write=60, pool=30)
    headers = (
        {"x-api-key": key, "anthropic-version": "2023-06-01"} if protocol == "anthropic"
        else {"Authorization": f"Bearer {key}"}
    )
    with httpx.Client(base_url=BASE_URLS[protocol], headers=headers, timeout=timeout) as client:
        for s in screens:
            s = s.upper()
            if s not in SCREENS:
                sys.exit(f"Unknown screen {s}; choose from {', '.join(SCREENS)}")
            if protocol == "anthropic":
                extra = anthropic_thinking(effort, reasoning_max)
                budget = extra.get("thinking", {}).get("budget_tokens")
                settings = f"thinking budget {budget:,} tokens" if budget else "no thinking budget"
            else:
                extra = reasoning_params(effort, reasoning_max)
                settings = f"effort {effort}" + (f", reasoning cap {reasoning_max:,} tokens" if extra and reasoning_max else "")
            print(f"Generating {SCREENS[s]} with {MODEL} via {protocol} protocol ({settings}; "
                  f"max {MAX_TOKENS:,} output tokens; streaming)...", flush=True)
            print("  ->", generate(s, client, extra, protocol))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate dashboard mockups with Kimi via ZenMux.")
    parser.add_argument("screens", nargs="*", default=["A"], help="screen letters: A B C D E F")
    parser.add_argument("--effort", default="medium", choices=["low", "medium", "high", "default"],
                        help="reasoning effort (default: medium; 'default' sends no reasoning settings)")
    parser.add_argument("--reasoning-max", type=int, default=20000,
                        help="thinking budget / cap on reasoning tokens (0 = none; default 20000)")
    parser.add_argument("--protocol", default="anthropic", choices=["anthropic", "openai"],
                        help="ZenMux API protocol (default: anthropic, like the playground; its thinking budget is "
                             "what limits Kimi K3's reasoning. --effort only applies to openai)")
    args = parser.parse_args()
    main(args.screens, args.effort, args.reasoning_max, args.protocol)
