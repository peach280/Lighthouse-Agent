"""
tools.py — Siemens Lighthouse Architect backend (Agentic edition)
Three functions the agent calls via tool invocation:
  - run_audit(file_path, categories)  →  raw LHR dict
  - parse_lhr(lhr)                    →  compact reasoning summary string

"""

import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv


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

    
    local_tmp = Path(__file__).parent / ".lighthouse-tmp"
    local_tmp.mkdir(exist_ok=True)
    output_path = str(local_tmp / f"lhr-{os.getpid()}.json")
   
    chrome_profile = local_tmp / "chrome-profile"

  
    chrome_flags = (
        "--headless --no-sandbox --disable-gpu "
        "--disable-dev-shm-usage "
        f"--user-data-dir={str(chrome_profile)}"
    )
 
    cmd = (
        f'lighthouse "{url}"'
        f' --output=json'
        f' --output-path="{output_path}"'
        f' --only-categories={",".join(categories)}'
        f' --locale={locale}'
        f' --preset=desktop'
        f' "--chrome-flags={chrome_flags}"'
        f' --quiet'
        f' --no-enable-error-reporting'
    )
 
    result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
 
    if result.returncode != 0:
        raise RuntimeError(
            f"Lighthouse exited {result.returncode}:\n{result.stderr.strip()}"
        )
 
    with open(output_path, encoding="utf-8") as f:
        lhr = json.load(f)
 
    os.unlink(output_path)
    return lhr




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


#  parse_lhr

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




# agent calls this


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



# Smoke test 


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python tools.py <path/to/index.html>")
        sys.exit(1)

    print("-- Running audit --")
    summary = analyze_lighthouse(sys.argv[1])
    print(summary)

    