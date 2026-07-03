"""
claude_bridge.py - Bridge between the web app and Claude Code running locally.

The app's "AI intelligence layer" is Claude Code itself. This module:
  1. Takes the user's question + the full current build state.
  2. Formats a structured prompt (archetype, powersets, every power with its
     slotted enhancements, calculated set-bonus totals vs caps, and the open
     slots with their available set categories).
  3. Sends it to Claude Code via its local headless CLI (`claude -p ...`).
  4. Returns the text response.

Claude Code exposes a local "endpoint" through its CLI headless mode rather than
an HTTP port, so we invoke it as a subprocess. The executable is auto-detected
(claude / claude.cmd on PATH) and can be overridden with the CLAUDE_BIN env var.
"""

import glob
import json
import os
import re
import shutil
import subprocess
import time
import urllib.error
import urllib.request

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")

# --- Direct Messages API (fast path) -------------------------------------
# `claude -p` spins up the full Claude Code agent (system prompt, every MCP
# server, tools) on each call — ~250s for one build. The Messages API returns
# the same completion in ~25s. We authenticate with the user's Claude Code
# subscription via the OAuth token (the same one start.bat loads), which the API
# accepts under the oauth beta as long as the first system block identifies as
# Claude Code. Falls back to ANTHROPIC_API_KEY, then to the `claude -p` CLI.
API_URL = "https://api.anthropic.com/v1/messages"
OAUTH_BETA = "oauth-2025-04-20"
CLAUDE_CODE_IDENTITY = "You are Claude Code, Anthropic's official CLI for Claude."
# Build generation is hard combinatorial optimization (which sets in which
# powers to hit bonus thresholds, respecting categories/ED/rule-of-5). Opus does
# it markedly better than Sonnet (uses Winter sets correctly, doesn't over-stack
# the wrong resistance) at similar latency via the API. Q&A is lighter — Sonnet.
GEN_MODEL = os.environ.get("COH_GEN_MODEL", "claude-opus-4-8")
QA_MODEL = os.environ.get("COH_QA_MODEL", "claude-sonnet-4-6")


def ensure_oauth_token():
    """If CLAUDE_CODE_OAUTH_TOKEN isn't in the process env (e.g. the server was
    launched directly rather than via start.bat), load it from the Windows user
    environment (registry HKCU\\Environment) so the API fast-path works. No-op on
    non-Windows or if already set. Returns True if a token is available."""
    if os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"):
        return True
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            val, _ = winreg.QueryValueEx(k, "CLAUDE_CODE_OAUTH_TOKEN")
        if val:
            os.environ["CLAUDE_CODE_OAUTH_TOKEN"] = val
            return True
    except (ImportError, OSError):
        pass
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _api_creds():
    """(kind, credential) — 'oauth' (subscription token) preferred, else
    'apikey' (ANTHROPIC_API_KEY), else (None, None)."""
    tok = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")
    if tok:
        return ("oauth", tok)
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return ("apikey", key)
    return (None, None)


def _complete(prompt, system_extra=None, model=None, max_tokens=4096, timeout=150):
    """One-shot completion via the Messages API. Returns {ok, response[, prompt]}.
    Retries transient 429/5xx a few times. Returns ok=False if no creds or a
    hard error (caller may fall back to the CLI)."""
    kind, cred = _api_creds()
    if not kind:
        return {"ok": False, "via": None, "response": "no-api-credentials"}

    if kind == "oauth":
        # First system block MUST be the Claude Code identity for the oauth beta.
        system = [{"type": "text", "text": CLAUDE_CODE_IDENTITY}]
        if system_extra:
            system.append({"type": "text", "text": system_extra})
        headers = {"authorization": "Bearer " + cred,
                   "anthropic-beta": OAUTH_BETA}
    else:
        system = system_extra or CLAUDE_CODE_IDENTITY
        headers = {"x-api-key": cred}
    headers.update({"anthropic-version": "2023-06-01", "content-type": "application/json"})
    body = json.dumps({"model": model or GEN_MODEL, "max_tokens": max_tokens,
                       "system": system,
                       "messages": [{"role": "user", "content": prompt}]}).encode()

    last = "unknown error"
    for attempt in range(4):
        req = urllib.request.Request(API_URL, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                d = json.load(r)
            text = "".join(b.get("text", "") for b in d.get("content", [])).strip()
            return {"ok": True, "via": "api", "response": text, "prompt": prompt}
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:300]
            last = f"HTTP {e.code}: {detail}"
            if e.code in (429, 500, 502, 503, 529) and attempt < 3:
                time.sleep((attempt + 1) * 4)
                continue
            return {"ok": False, "via": "api", "response": last, "prompt": prompt}
        except Exception as e:  # noqa: BLE001
            last = f"API call failed: {e}"
            if attempt < 3:
                time.sleep((attempt + 1) * 2)
                continue
            return {"ok": False, "via": "api", "response": last, "prompt": prompt}
    return {"ok": False, "via": "api", "response": last, "prompt": prompt}


def _strip_ansi(s):
    return _ANSI_RE.sub("", s)


SYSTEM_PREAMBLE = (
    "You are an expert City of Heroes (Homecoming) build advisor embedded in a "
    "local build-planning app. All game data the app shows you is sourced from "
    "Mids Reborn. Defense soft cap is 45%, resistance hard cap is 75%. Most set "
    "bonuses count up to 5 identical instances (rule of five). Enhancement "
    "Diversification reduces effectiveness above ~95% enhancement in a single "
    "attribute. Be concrete and concise: name specific enhancement sets and "
    "powers, reference the build state you were given, and prefer actionable "
    "advice. The set-bonus totals in the build state are accurate; innate power "
    "values are not included, so frame defensive advice around set bonuses."
)


def _find_claude_bin():
    override = os.environ.get("CLAUDE_BIN")
    if override and (os.path.isfile(override) or shutil.which(override)):
        return override
    for name in ("claude", "claude.cmd", "claude.exe"):
        path = shutil.which(name)
        if path:
            return path
    # Claude Code desktop app bundles the CLI under a versioned dir.
    # Pick the highest version available. Covers both the normal Roaming
    # location and the MSIX/Store packaged location under LocalCache.
    candidates = []
    for base in filter(None, [os.environ.get("APPDATA"),
                              os.environ.get("LOCALAPPDATA")]):
        candidates += glob.glob(os.path.join(
            base, "Claude", "claude-code", "*", "claude.exe"))
    localappdata = os.environ.get("LOCALAPPDATA")
    if localappdata:
        candidates += glob.glob(os.path.join(
            localappdata, "Packages", "Claude*", "LocalCache", "Roaming",
            "Claude", "claude-code", "*", "claude.exe"))
    if candidates:
        def ver_key(p):
            try:
                return [int(x) for x in os.path.basename(
                    os.path.dirname(p)).split(".")]
            except ValueError:
                return [0]
        return sorted(candidates, key=ver_key)[-1]
    return None


def detect_info():
    """Diagnostic detail about Claude Code detection (for startup logging)."""
    searched = ["PATH (claude/claude.cmd/claude.exe)"]
    for base in filter(None, [os.environ.get("APPDATA"),
                              os.environ.get("LOCALAPPDATA")]):
        searched.append(os.path.join(base, "Claude", "claude-code", "*", "claude.exe"))
    return {
        "found": _find_claude_bin(),
        "CLAUDE_BIN_env": os.environ.get("CLAUDE_BIN"),
        "searched": searched,
    }


def format_prompt(build, question, totals=None):
    """Build the structured prompt string from the current build state."""
    lines = []
    lines.append(SYSTEM_PREAMBLE)
    lines.append("\n===== CURRENT BUILD STATE =====")
    lines.append(f"Archetype: {build.get('archetype', '(none)')}")
    lines.append(f"Primary:   {build.get('primary_display', build.get('primary', '-'))}")
    lines.append(f"Secondary: {build.get('secondary_display', build.get('secondary', '-'))}")
    pools = build.get("pools_display") or build.get("pools") or []
    if pools:
        lines.append("Pools:     " + ", ".join(str(p) for p in pools))
    if build.get("epic"):
        lines.append(f"Epic/Ancillary: {build.get('epic_display', build.get('epic'))}")
    incarnates = build.get("incarnates") or {}
    chosen_inc = {k: v for k, v in incarnates.items() if v}
    if chosen_inc:
        lines.append("Incarnates: " + ", ".join(
            f"{slot}: {name}" for slot, name in chosen_inc.items()))

    lines.append("\n----- Powers & slotting -----")
    powers = build.get("powers", [])
    if not powers:
        lines.append("(no powers selected yet)")
    for p in powers:
        slots = p.get("slots", []) or []
        filled = [s for s in slots if s]
        lines.append(f"* {p.get('display_name', p.get('full_name','?'))} "
                     f"[{len(filled)}/{len(slots)} slots]")
        for s in filled:
            lines.append(f"    - {s.get('set_name','?')}: {s.get('piece_name','?')}")
        open_slots = len(slots) - len(filled)
        if open_slots > 0:
            cats = p.get("accepted_set_categories", [])
            lines.append(f"    ({open_slots} open slot(s); accepts set "
                         f"categories: {', '.join(cats) if cats else 'none'})")

    if totals:
        lines.append("\n----- Set-bonus totals vs caps -----")
        df = totals.get("defense", {})
        hi_def = sorted(df.items(), key=lambda kv: -kv[1]["value"])[:4]
        lines.append("Defense (soft cap 45%): " + ", ".join(
            f"{t} {d['value']}%" for t, d in hi_def if d["value"] > 0) or "none")
        rs = totals.get("resistance", {})
        hi_res = sorted(rs.items(), key=lambda kv: -kv[1]["value"])[:4]
        lines.append("Resistance (hard cap 75%): " + ", ".join(
            f"{t} {d['value']}%" for t, d in hi_res if d["value"] > 0) or "none")
        lines.append(f"Recharge +{totals.get('recharge',{}).get('value',0)}%, "
                     f"Recovery +{totals.get('recovery',{}).get('value',0)}%, "
                     f"Regen +{totals.get('regeneration',{}).get('value',0)}%")

    lines.append("\n===== USER QUESTION =====")
    lines.append(question)
    lines.append("\nAnswer for this specific build. Keep it focused.")
    return "\n".join(lines)


def run_prompt(prompt, timeout=240, model=None, max_tokens=4096):
    """Generate a completion. Uses the Messages API when credentials are present
    (fast: ~25s vs the CLI's ~250s); otherwise falls back to the `claude -p` CLI.
    Returns {ok, response, prompt}."""
    kind, _ = _api_creds()
    if kind:
        r = _complete(prompt, model=model, max_tokens=max_tokens,
                      timeout=min(timeout, 150))
        # Only fall through to the slow CLI if the API path is unusable; surface
        # real API errors (rate limits, bad request) rather than silently waiting.
        if r["ok"] or r.get("via") == "api":
            return r
    return _run_prompt_cli(prompt, timeout)


def _run_prompt_cli(prompt, timeout=240):
    """Legacy path: run the prompt through the local `claude -p` CLI."""
    claude_bin = _find_claude_bin()
    if not claude_bin:
        info = detect_info()
        return {"ok": False, "prompt": prompt, "response": (
            "Claude Code CLI was not found. Searched:\n  - "
            + "\n  - ".join(info["searched"])
            + f"\nCLAUDE_BIN env = {info['CLAUDE_BIN_env'] or '(unset)'}")}
    try:
        proc = subprocess.run(
            [claude_bin, "-p", "--output-format", "text"],
            input=prompt, capture_output=True, text=True, timeout=timeout,
            encoding="utf-8", errors="replace",
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "prompt": prompt,
                "response": f"Claude Code timed out after {timeout}s."}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "prompt": prompt,
                "response": f"Failed to call Claude Code: {e}"}

    out = _strip_ansi((proc.stdout or "").strip())
    err = _strip_ansi((proc.stderr or "").strip())
    combined = f"{out}\n{err}".strip()
    if "not logged in" in combined.lower() or "/login" in combined.lower():
        return {"ok": False, "prompt": prompt, "response": (
            "Claude Code is installed but not logged in for headless use. "
            "Run `claude setup-token`, store it as CLAUDE_CODE_OAUTH_TOKEN, and relaunch.")}
    if proc.returncode != 0:
        return {"ok": False, "prompt": prompt,
                "response": f"Claude Code returned an error: {err or out or '(no output)'}"}
    return {"ok": True, "prompt": prompt, "response": out}


def ask_claude(build, question, totals=None, timeout=240):
    """Format the prompt, call Claude (API fast-path, CLI fallback), return the
    response dict."""
    prompt = format_prompt(build, question, totals)
    kind, _ = _api_creds()
    if kind:
        r = _complete(prompt, model=QA_MODEL, max_tokens=2048,
                      timeout=min(timeout, 150))
        if r["ok"] or r.get("via") == "api":
            return {"ok": r["ok"], "response": r["response"], "prompt": prompt}
    claude_bin = _find_claude_bin()
    if not claude_bin:
        info = detect_info()
        return {
            "ok": False,
            "response": (
                "Claude Code CLI was not found. Searched:\n  - "
                + "\n  - ".join(info["searched"])
                + f"\nCLAUDE_BIN env = {info['CLAUDE_BIN_env'] or '(unset)'}\n"
                "Set CLAUDE_BIN to your claude.exe full path and relaunch."),
            "prompt": prompt,
        }

    # Pipe the prompt via STDIN rather than as an argv arg: avoids the CLI's
    # "no stdin data received" wait and Windows' ~32K command-line length limit.
    try:
        proc = subprocess.run(
            [claude_bin, "-p", "--output-format", "text"],
            input=prompt,
            capture_output=True, text=True, timeout=timeout,
            encoding="utf-8", errors="replace",
        )
    except subprocess.TimeoutExpired:
        return {"ok": False,
                "response": f"Claude Code timed out after {timeout}s.",
                "prompt": prompt}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "response": f"Failed to call Claude Code: {e}",
                "prompt": prompt}

    out = _strip_ansi((proc.stdout or "").strip())
    err = _strip_ansi((proc.stderr or "").strip())
    combined = f"{out}\n{err}".strip()

    if "not logged in" in combined.lower() or "/login" in combined.lower():
        return {"ok": False, "prompt": prompt, "response": (
            "Claude Code is installed but not logged in for headless use. "
            "Open a terminal, run `claude`, complete `/login` once, then retry. "
            "(Alternatively set an ANTHROPIC_API_KEY environment variable before "
            "launching the app.)")}

    if proc.returncode != 0:
        return {"ok": False,
                "response": f"Claude Code returned an error: {err or out or '(no output)'}",
                "prompt": prompt}

    return {"ok": True, "response": out, "prompt": prompt}
