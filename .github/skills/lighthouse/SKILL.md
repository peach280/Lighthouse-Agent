---
name: lighthouse-audit
type: hybrid
description: >
  Runs a Lighthouse audit against a URL or HTML file, surfaces failing/warning
  scores across performance, accessibility, SEO, and best-practices categories,
  and applies surgical JSX/HTML fixes directly to the flagged source files.
  Use when: checking Lighthouse scores, fixing CLS/LCP/TBT regressions,
  resolving accessibility violations (alt text, color contrast, ARIA),
  validating UI against Siemens Healthineers performance standards,
  or remediating any Lighthouse audit failure.
knowledge-base:
  - .github/knowledge/architecture/lighthouse-standards.md
  - .github/knowledge/architecture/lighthouse-audit-context.md
mcp-server: lighthouse-architect
mcp-tools:
  - analyze_lighthouse   # runs headless Lighthouse → returns parsed FAIL/WARN summary
produces:
  - performance_summary.json
  - code_remediation.tsx
---

# Lighthouse Audit Skill

## Purpose

A **hybrid skill** backed by the **`lighthouse-architect` MCP server** at `http://localhost:8000`.

Single invocation — one command does everything:
1. Audits the target URL via MCP
2. Displays the score card in chat
3. Generates fixes using KB context
4. Applies fixes directly to the flagged source files

---

##  Critical Wiring Rule

**Do NOT run Lighthouse via shell, pwsh, or CLI commands directly.**
**Do NOT call any external API for fix generation — generate fixes yourself using the KB.**

| Action | How |
|---|---|
| Audit a URL or file | Call `analyze_lighthouse` MCP tool |
| Generate a fix | Use `lighthouse-audit-context.md` KB + your own reasoning |
| Apply a fix | Edit the source file directly at the flagged path and line |

---

## Step-by-Step Execution

### Step 1 — Call `analyze_lighthouse` via MCP
Always run this first.
```json
{
  "target": "<url or file path from user>",
  "categories": ["performance", "accessibility", "seo", "best-practices"]
}
```
The summary includes:
- Category scores
- Failing audit IDs
- Offending code snippets
- Source file paths and line numbers for each violation

---

### Step 2 — Display score card in chat
Immediately after `analyze_lighthouse` returns, display this before anything else:

```
 Lighthouse Audit — <target>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Scores
  Performance   : XX/100
  Accessibility : XX/100
  SEO           : XX/100
  Best Practices: XX/100

 Blockers (must fix before merge)
  - <blocker or "None">

  Failures
  - <audit_id> : <snippet> (<file>:<line>)

 Warnings
  - <audit_id> : <value>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Do NOT proceed until this is visible in chat.

---

### Step 3 — Validate against KB thresholds
Check `.github/knowledge/architecture/lighthouse-standards.md`:
```
CLS  > 0.1   → BLOCKER (clinical safety)
LCP  > 2.5s  → BLOCKER
A11y < 100   → BLOCKER (patient-facing dashboards)
```
Mark each blocker clearly in the score card.

---

### Step 4 — Generate fixes using KB
For each FAIL, load `.github/knowledge/architecture/lighthouse-audit-context.md`
and use the guidance for that audit_id to generate the correct fix.

Do NOT call any MCP tool. Do NOT call any external API.
You already have everything needed:
- The failing `audit_id`
- The offending snippet from the audit summary
- The fix guidance from the KB
- The source file path and line number

---

### Step 5 — Apply fixes directly to source files
For each fix generated in Step 4:
1. Open the source file at the path flagged in the audit summary
2. Replace the `before` snippet with the `after` snippet surgically
3. Only touch the exact lines flagged — preserve all surrounding code
4. If file path is missing from audit summary, show the fix as manual

After all edits, report:
```
 Fixed X violations in Y files:
  - src/components/Dashboard.tsx  (color-contrast line 42, 67)
  - src/pages/index.tsx           (meta-description)

  Manual fixes required:
  - <audit_id>: file path not available in audit summary
```

---

## Knowledge Base

| File | Purpose |
|---|---|
| `lighthouse-standards.md` | Compliance thresholds — CLS, LCP, Accessibility |
| `lighthouse-audit-context.md` | Fix guidance per audit_id — causes, solutions, code examples |

---

## Invocation

Single command — always does audit + score display + fix:
```
/lighthouse-audit http://localhost:5173
```

Specific category only:
```
/lighthouse-audit http://localhost:5173 accessibility
```

---

## Error Handling

| Condition | Behaviour |
|---|---|
| Target unreachable | Tell user to check dev server is running on the correct port |
| `lighthouse-architect` MCP server offline | Tell user to run `python app.py` |
| `audit_id` not in KB | Use Copilot's own knowledge to generate the fix |
| File path missing from audit summary | Report as manual fix with before/after shown in chat |

---

## Compliance Gate

```
CLS  > 0.1   → BLOCKER  (clinical safety — must fix before merge)
LCP  > 2.5s  → BLOCKER
A11y < 100   → BLOCKER  (patient-facing dashboards)
```

Blockers must appear at the top of the score card before any fixes are shown.