"""
tools.py — Siemens Lighthouse Architect backend (Agentic edition)
Three functions the agent calls via tool invocation:
  - run_audit(file_path, categories)  →  raw LHR dict
  - parse_lhr(lhr)                    →  compact reasoning summary string
  - suggest_fix(audit_id, snippet)    →  LLM-reasoned fix dict

Change from v1: suggest_fix() no longer uses static FIX_HANDLERS.
Instead it sends the audit finding + code snippet to Groq and lets the
LLM reason out the correct fix — handles JSX, frameworks, and edge cases
that string .replace() calls would silently mangle.
"""

import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

from groq import Groq
load_dotenv()

# ─────────────────────────────────────────────
# Groq client (reads GROQ_API_KEY from env)
# ─────────────────────────────────────────────

_groq = Groq(api_key=os.environ["GROQ_API_KEY"])
GROQ_MODEL = "llama-3.3-70b-versatile"  # fast + strong enough for code fixes


# ─────────────────────────────────────────────
# 1.  run_audit
# ────────────────────────────────────────────

def run_audit(
    file_path: str,
    categories: Optional[list[str]] = None,
    locale: str = "en",
) -> dict:
    _URL_RE = re.compile(r'^https?://', re.IGNORECASE)
    is_url = bool(_URL_RE.match(file_path))

    if is_url:
        url = file_path
    else:
        path = Path(file_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        url = path.as_uri()

    if categories is None:
        categories = ["performance", "accessibility", "seo", "best-practices"]

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        output_path = tmp.name

    cmd = [
        "lighthouse",
        url,
        "--output=json",
        f"--output-path={output_path}",
        f"--only-categories={','.join(categories)}",
        f"--locale={locale}",
        "--chrome-flags=--headless --no-sandbox --disable-gpu",
        "--quiet",
        "--no-enable-error-reporting",
    ]

    # For http:// targets, Lighthouse needs a real browser profile
    # (file:// works headless, but localhost URLs need --disable-dev-shm-usage)
    if is_url:
        cmd[-3] = "--chrome-flags=--headless --no-sandbox --disable-gpu --disable-dev-shm-usage"

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(
            f"Lighthouse exited {result.returncode}:\n{result.stderr.strip()}"
        )

    with open(output_path) as f:
        lhr = json.load(f)

    os.unlink(output_path)
    return lhr


# ─────────────────────────────────────────────
# 2.  parse_lhr
# ─────────────────────────────────────────────

TRACKED_AUDITS: dict[str, list[str]] = {
    "performance": [
        "cumulative-layout-shift",
        "largest-contentful-paint",
        "total-blocking-time",
        "first-contentful-paint",
        "speed-index",
        "interactive",
    ],
    "accessibility": [
        "image-alt",
        "color-contrast",
        "label",
        "button-name",
        "link-name",
        "document-title",
        "html-lang",
        "aria-required-attr",
        "aria-valid-attr",
    ],
    "seo": [
        "meta-description",
        "document-title",
        "crawlable-anchors",
        "robots-txt",
        "canonical",
    ],
    "best-practices": [
        "uses-https",
        "no-vulnerable-libraries",
        "csp-xss",
        "deprecations",
    ],
}

AUDIT_LABELS: dict[str, str] = {
    "cumulative-layout-shift": "CLS",
    "largest-contentful-paint": "LCP",
    "total-blocking-time": "TBT",
    "first-contentful-paint": "FCP",
    "speed-index": "Speed Index",
    "interactive": "TTI",
    "image-alt": "Missing alt text",
    "color-contrast": "Color contrast",
    "label": "Missing form label",
    "button-name": "Unnamed button",
    "link-name": "Unnamed link",
    "document-title": "Missing <title>",
    "html-lang": "Missing lang attribute",
    "aria-required-attr": "Missing ARIA attr",
    "aria-valid-attr": "Invalid ARIA attr",
    "meta-description": "Missing meta description",
    "crawlable-anchors": "Uncrawlable anchor",
    "robots-txt": "robots.txt invalid",
    "canonical": "Missing canonical",
    "uses-https": "Not using HTTPS",
    "no-vulnerable-libraries": "Vulnerable library",
    "csp-xss": "Missing CSP header",
    "deprecations": "Deprecated API",
}

SCORE_THRESHOLDS = {"PASS": 0.9, "WARN": 0.5}


def _score_label(score: float | None) -> str:
    if score is None:
        return "N/A"
    if score >= SCORE_THRESHOLDS["PASS"]:
        return "PASS"
    if score >= SCORE_THRESHOLDS["WARN"]:
        return "WARN"
    return "FAIL"


def _extract_items(audit: dict) -> str:
    details = audit.get("details", {})
    items = details.get("items", [])
    if not items:
        return ""

    lines = []
    for item in items[:5]:
        node = item.get("node", {})
        snippet = node.get("snippet", "")
        source = node.get("nodeLabel", "")
        url_ref = item.get("url", "")
        source_obj = item.get("source", {})
        file_ref = source_obj.get("url", url_ref)
        line_ref = source_obj.get("line")

        ref_parts = []
        if file_ref:
            ref_parts.append(file_ref.replace("file://", ""))
        if line_ref:
            ref_parts.append(f"line {line_ref}")
        if snippet and len(snippet) < 80:
            ref_parts.append(f"-> `{snippet.strip()}`")
        elif source and len(source) < 60:
            ref_parts.append(f"-> {source.strip()}")

        if ref_parts:
            lines.append("    " + " ".join(ref_parts))

    if len(items) > 5:
        lines.append(f"    ... and {len(items) - 5} more")

    return "\n".join(lines)


def parse_lhr(lhr: dict) -> str:
    """
    Distill a raw Lighthouse Result into a compact reasoning summary.
    Only surfaces FAIL/WARN items — PASS audits are intentionally omitted.
    """
    categories = lhr.get("categories", {})
    audits = lhr.get("audits", {})
    sections: list[str] = []

    for cat_id, audit_ids in TRACKED_AUDITS.items():
        cat = categories.get(cat_id)
        if not cat:
            continue

        cat_score = cat.get("score")
        cat_display = int(cat_score * 100) if cat_score is not None else "?"
        header = f"{cat_id.upper()}: {cat_display}/100"
        findings: list[str] = []

        for audit_id in audit_ids:
            audit = audits.get(audit_id)
            if not audit:
                continue

            score = audit.get("score")
            label = _score_label(score)
            if label == "PASS":
                continue

            display_name = AUDIT_LABELS.get(audit_id, audit_id)
            display_value = audit.get("displayValue", "")
            description = audit.get("description", "")

            finding = f"  {display_name}: {display_value} ({label})"
            if description:
                finding += f" -- {description.split('.')[0]}"

            item_detail = _extract_items(audit)
            if item_detail:
                finding += f"\n{item_detail}"

            findings.append(finding)

        if findings:
            sections.append(header + "\n" + "\n".join(findings))
        else:
            sections.append(header + "\n  All tracked audits passed.")

    if not sections:
        return "No audit data found. Ensure the categories were included in the run."

    return "\n\n".join(sections)


# ─────────────────────────────────────────────
# 3.  suggest_fix  (Agentic — Groq-powered)
# ─────────────────────────────────────────────

# Grounding context per audit ID.
# Sent to the LLM alongside the snippet so it understands *what* to fix
# without hallucinating what the audit measures.
# The LLM still reasons freely about the best fix for the specific code.
AUDIT_CONTEXT: dict[str, str] = {
    "cumulative-layout-shift": (
        "CLS measures unexpected layout shifts during page load. "
        "Common causes: images/videos without explicit width+height, "
        "dynamically injected content above existing content, "
        "web fonts causing text reflow (FOIT/FOUT). "
        "Fix goal: reserve space before content loads so nothing shifts."
    ),
    "largest-contentful-paint": (
        "LCP measures when the largest above-the-fold element finishes rendering. "
        "Common causes: lazy-loaded LCP image, no preload hint, "
        "render-blocking scripts/styles, slow server TTFB. "
        "Fix goal: fetch the LCP resource as early as possible."
    ),
    "total-blocking-time": (
        "TBT measures main-thread blocking time between FCP and TTI. "
        "Common causes: large JS bundles, long tasks >50ms, "
        "synchronous third-party scripts. "
        "Fix goal: break up long tasks or defer non-critical scripts."
    ),
    "image-alt": (
        "Every <img> element must have an alt attribute. "
        "Decorative images use alt=''. Informative images need a descriptive string. "
        "In JSX the attribute is still 'alt'. In React, alt is passed as a prop. "
        "Next.js <Image> also requires alt."
    ),
    "color-contrast": (
        "Text must have contrast ratio >= 4.5:1 (normal text) or >= 3:1 (large text/UI). "
        "Fix by darkening text color or lightening background. "
        "If exact color values are unknown, suggest a CSS custom property approach "
        "and provide the Lighthouse-recommended ratio."
    ),
    "label": (
        "Every form input needs an accessible label. Options: "
        "(1) <label for='id'> referencing the input, "
        "(2) aria-label='...' on the input, "
        "(3) aria-labelledby='id-of-visible-text'. "
        "In React/JSX, 'for' becomes 'htmlFor'."
    ),
    "button-name": (
        "Buttons must have an accessible name via: visible text content, "
        "aria-label, aria-labelledby, or title. "
        "Icon-only buttons always need aria-label."
    ),
    "document-title": (
        "The page must have a <title> in <head>. "
        "In React, use react-helmet or Next.js <Head>. "
        "Title format: 'Page Name -- Site Name', unique per page."
    ),
    "meta-description": (
        "Add <meta name='description' content='...'> in <head>. "
        "In Next.js/React use the framework's Head component. "
        "150-160 characters, unique description of the page."
    ),
    "html-lang": (
        "The <html> element must have a lang attribute (e.g. lang='en'). "
        "In Next.js set it in next.config.js i18n or _document.js."
    ),
    "aria-required-attr": (
        "ARIA roles require certain attributes to be present. "
        "For example, role='checkbox' requires aria-checked. "
        "Add the missing required ARIA attribute with an appropriate value."
    ),
    "link-name": (
        "Anchor elements must have discernible text. "
        "Options: visible text content, aria-label, aria-labelledby, or title. "
        "Icon links need aria-label."
    ),
}

_AUDIT_ALIASES: dict[str, str] = {
    "cls":         "cumulative-layout-shift",
    "lcp":         "largest-contentful-paint",
    "tbt":         "total-blocking-time",
    "fcp":         "first-contentful-paint",
    "alt":         "image-alt",
    "contrast":    "color-contrast",
    "title":       "document-title",
    "lang":        "html-lang",
    "description": "meta-description",
}


def _build_prompts(audit_id: str, snippet: str, context: str) -> tuple[str, str]:
    """
    Build the system + user prompts for the Groq call.
    Returns (system_prompt, user_prompt).

    Design notes:
    - response_format=json_object is enforced at the API level, but we also
      instruct it in the system prompt so the model knows the expected shape.
    - temperature=0.2 keeps fixes deterministic; creativity isn't wanted here.
    - AUDIT_CONTEXT provides grounding so the model doesn't hallucinate what
      the audit measures — it only needs to reason about *how* to fix the code.
    """
    guidance = AUDIT_CONTEXT.get(audit_id, "")

    system = (
        "You are a senior web performance and accessibility engineer.\n"
        "Your job: fix the code snippet to resolve the specific Lighthouse audit failure.\n\n"
        "Output rules:\n"
        "- Return ONLY a valid JSON object. No markdown, no backtick fences.\n"
        '- Shape: {"fixed_code": "...", "explanation": "...", "caveat": "..."}\n'
        "- fixed_code: corrected snippet, preserving original language/framework "
        "(HTML, JSX, TSX, Vue SFC, etc.). Minimal diff — change only what is needed.\n"
        "- explanation: 2-3 sentences on exactly why this fix resolves the audit. "
        "Be specific about the mechanism, not generic advice.\n"
        "- caveat: one sentence on anything the developer must verify manually. "
        'Empty string "" if no caveat.\n'
        "- If the snippet cannot be safely auto-fixed (e.g. contrast needs design tokens), "
        "return fixed_code unchanged and put full actionable guidance in explanation."
    )

    user = (
        f"Lighthouse audit failing: {audit_id}\n\n"
        f"Audit context (what this measures and common fixes):\n"
        f"{guidance if guidance else '(no additional context)'}\n\n"
        f"Developer context:\n"
        f"{context if context else '(none provided)'}\n\n"
        f"Code snippet to fix:\n"
        f"{snippet}\n\n"
        "Return the JSON fix object now."
    )

    return system, user


def suggest_fix(
    audit_id: str,
    code_snippet: str,
    context: str = "",
) -> dict:
    """
    Use Groq to reason out a fix for a specific Lighthouse audit finding.

    Why Groq instead of static templates:
    - Handles JSX/TSX attribute syntax (htmlFor, className, fetchPriority)
      without brittle string replacements that break on real-world code.
    - Adapts to framework context (Next.js Image vs plain <img>,
      React Hook Form labels vs native HTML, etc.).
    - Provides a tailored explanation specific to the actual snippet,
      not a generic description of the audit category.

    Parameters
    ----------
    audit_id : str
        Lighthouse audit ID or alias (e.g. "cls", "image-alt", "color-contrast").
    code_snippet : str
        The offending HTML/JSX/TSX/CSS extracted from the file.
    context : str
        Optional: framework, version, styling library, or other relevant info.
        More context = more accurate fix (e.g. "Next.js 14, Tailwind, TypeScript").

    Returns
    -------
    dict:
        audit_id    - resolved canonical ID
        before      - original snippet (unchanged)
        after       - fixed snippet (may equal before if fix is manual-only)
        explanation - why the fix works, specific to this snippet
        caveat      - what the developer must verify manually (empty if none)
        model       - Groq model that produced the fix
    """
    resolved_id = _AUDIT_ALIASES.get(audit_id.lower(), audit_id.lower())
    system_prompt, user_prompt = _build_prompts(resolved_id, code_snippet, context)

    response = _groq.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        temperature=0.2,       # low = consistent, minimal hallucination risk
        max_tokens=1024,
        response_format={"type": "json_object"},  # Groq enforces valid JSON
    )

    raw = response.choices[0].message.content
    result = json.loads(raw)  # safe: response_format guarantees parseable JSON

    return {
        "audit_id":    resolved_id,
        "before":      code_snippet,
        "after":       result.get("fixed_code", code_snippet),
        "explanation": result.get("explanation", ""),
        "caveat":      result.get("caveat", ""),
        "model":       GROQ_MODEL,
    }


# ─────────────────────────────────────────────
# 4.  Top-level entry point  (agent calls this)
# ─────────────────────────────────────────────

def analyze_lighthouse(
    file_path: str,
    categories: Optional[list[str]] = None,
    locale: str = "en",
) -> str:
    """
    Full pipeline: run audit -> parse -> return reasoning summary.
    This is the single function the agent calls for analyze_lighthouse.
    """
    lhr = run_audit(file_path, categories, locale)
    return parse_lhr(lhr)


# ─────────────────────────────────────────────
# Smoke test  (python tools.py <file.html>)
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python tools.py <path/to/index.html>")
        sys.exit(1)

    print("-- Running audit --")
    summary = analyze_lighthouse(sys.argv[1])
    print(summary)

    print("\n-- Testing suggest_fix (Groq-powered) --")
    fix = suggest_fix(
        audit_id="image-alt",
        code_snippet='<img src="hero.jpg" className="banner w-full" />',
        context="Next.js 14, Tailwind CSS, TypeScript",
    )
    print(f"Before : {fix['before']}")
    print(f"After  : {fix['after']}")
    print(f"Why    : {fix['explanation']}")
    print(f"Caveat : {fix['caveat']}")
    print(f"Model  : {fix['model']}")