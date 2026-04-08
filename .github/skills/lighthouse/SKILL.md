---
name: lighthouse-audit
type: hybrid
description: "Identifies UI performance regressions and generates surgical JSX fixes to resolve Lighthouse failures."
knowledge-base:
  - .github/knowledge/architecture/lighthouse-standards.md
mcp-tools:
  - mcp_analyze_lighthouse
  - mcp_suggest_fix
produces: "performance_summary.json + code_remediation.tsx"
---

# Lighthouse Audit Skill
This skill identifies performance, accessibility, and SEO regressions. 
It provides surgical JSX fixes to resolve audit failures, ensuring 
compliance with Siemens Healthineers UI standards.