# Lighthouse Agent – Setup & Usage Guide

## Description

This agent runs Lighthouse audits against a specified URL or a locally-hosted frontend. It analyzes Performance, Accessibility, SEO, and Best Practices results, then surfaces failures and generates suggested code fixes.

## How it works

- `start.bat` — one-click launcher that sets everything up and opens VS Code
- `app.py` — FastAPI + MCP server that exposes the audit tool to Copilot
- `tools.py` — runs headless Lighthouse and parses the results

---

## Prerequisites

Before running `start.bat` for the first time, you need two things installed on your machine.

### 1. Node.js

Download and install from: https://nodejs.org/ (use the LTS version)

> **Why?** Lighthouse is a Node.js tool. Without Node, it cannot be installed or run.

**Verify it worked** — open a terminal and run:
```
node -v
```
You should see a version number like `v20.x.x`. If you see `command not found`, Node is not on your PATH — reinstall and check the "Add to PATH" option during setup.

### 2. Python 3.10+

Download and install from: https://python.org/

> **Important:** During installation, check **"Add Python to PATH"**. Without this, `start.bat` cannot find Python.

**Verify it worked:**
```
python --version
```
You should see `Python 3.10.x` or higher.

---

## Getting Started

### Step 1 — Unzip the project

After extracting the ZIP, ensure the folder structure looks like this:


```
Lighthouse-Agent/
├── start.bat
├── app.py
├── tools.py
├── requirements.txt
├── .vscode/
│   └── mcp.json
└── .github/
```

> **Important:** Do NOT allow an extra nested folder like `Lighthouse-Agent/some-folder/.vscode`. The `.vscode` folder must be at the root level.

---

### Step 2 — Double-click `start.bat`

That's it. The script handles everything automatically:

<img width="1076" height="473" alt="Screenshot 2026-05-08 072951" src="https://github.com/user-attachments/assets/24c11aaf-13eb-46c4-8116-5a86fde87e93" />


| Step | What happens |
|------|-------------|
| Checks Node.js | Errors with a download link if missing |
| Checks Lighthouse | Installs it automatically via npm if missing |
| Checks Python | Errors with a download link if missing |
| Creates virtualenv | Only on first run |
| Installs dependencies | Runs `pip install -r requirements.txt` |
| Starts MCP server | Launches `app.py` in the background on port 8000 |
| Verifies server | Pings `/meta` to confirm it's running |
| Opens VS Code | Opens the project folder automatically |

You will see this when everything is ready:

<img width="1048" height="484" alt="Screenshot 2026-05-08 073023" src="https://github.com/user-attachments/assets/3ebc245b-c12c-4519-b6f5-e9779c02e786" />


```
=========================================
  All done! VS Code is opening.
  MCP server is running in background.
  Server logs: server.log
  Close this window to stop the server.
=========================================
```

> **Keep the `start.bat` window open** while you work. Closing it stops the MCP server.

---

### Step 3 — Add your frontend code

Copy your frontend project (React, Vite, etc.) into the project root:

```
Lighthouse-Agent/
├── your-frontend/    ← paste here
├── start.bat
├── app.py
├── ...
```

Start your frontend dev server (e.g. `npm run dev`) so it's running on a local port before auditing.

<img width="1620" height="530" alt="Screenshot 2026-05-08 073122" src="https://github.com/user-attachments/assets/ff1feaf3-bdab-488a-809d-d9a3952ccf56" />


---

### Step 4 — Verify the MCP server is connected in VS Code

Once VS Code opens, confirm that Copilot has picked up the MCP server:

1. Press `Ctrl + Shift + P` to open the Command Palette
2. Type `MCP: List Servers` and press Enter
3. You should see `lighthouse-architect` in the list with a **green dot** and status `Running`




```
MCP Servers
└── lighthouse-architect  ● Running
```

> If it shows `Stopped` then restart it
---

### Step 5 — Run a Lighthouse audit via Copilot

In VS Code's Copilot Chat, run:

```
/lighthouse-audit audit http://localhost:5173/
```

Replace the URL with whatever port your frontend runs on.

<img width="568" height="730" alt="Screenshot 2026-05-08 073151" src="https://github.com/user-attachments/assets/9b07ab1a-a640-4029-9762-b250a1979b3b" />

---

## What happens next

- Lighthouse audit runs via the MCP server
- Failures are detected across Performance, Accessibility, SEO, and Best Practices
- Fix suggestions are generated automatically using the knowledge base

<img width="384" height="654" alt="Screenshot 2026-05-08 073214" src="https://github.com/user-attachments/assets/4b808232-96fa-403e-9ba4-b87b18b9d19a" />


<img width="1548" height="598" alt="Screenshot 2026-05-08 073243" src="https://github.com/user-attachments/assets/96b69c20-4c3b-4792-9511-ca21869c889b" />


---

## Troubleshooting

### `start.bat` says Node.js is not installed
Install from https://nodejs.org/ — use the LTS version. During installation, make sure "Add to PATH" is checked. After installing, close and reopen any terminals, then run `start.bat` again.

### `start.bat` says Python is not installed
Install from https://python.org/ — during setup check **"Add Python to PATH"**. After installing, run `start.bat` again.

### `pip install` fails
This usually means a package in `requirements.txt` has a version conflict or a missing system dependency. Check `server.log` for the exact error. Try manually running:
```
venv\Scripts\activate
pip install -r requirements.txt
```
and read the error output carefully.

### Server did not start — `[ERROR] Server did not start. Check server.log for details`
Open `server.log` in the project root — it contains the full output from `app.py`. Common causes:
- Port 8000 is already in use by another process. Find and stop it, or change the port in `app.py` and `mcp.json`.
- A Python dependency failed to install. Re-run `start.bat` and check the pip output.

### MCP: List Servers shows `lighthouse-architect` as Stopped
The MCP config in `.vscode/mcp.json` points to `http://localhost:8000/mcp`. VS Code connects to it but the server isn't responding. This means `app.py` either didn't start or crashed. Check `server.log` in the project root for errors, then re-run `start.bat`.

If it's not listed at all, check that `.vscode/mcp.json` exists at the project root and that VS Code opened the correct folder (the one containing `start.bat` and `app.py`).

### VS Code opens but Copilot can't find the `lighthouse-audit` skill
- Check that `.vscode/mcp.json` is present at the root level
- Check that the MCP server is running — open a browser and visit `http://localhost:8000/meta`. You should see a JSON response.
- If the server is not running, check `server.log` for errors and re-run `start.bat`.

### Lighthouse audit fails with a Chrome error
Lighthouse launches headless Chrome internally. Make sure:
- Chrome or Chromium is installed on your machine
- You are not running in a restricted environment that blocks Chrome's `--no-sandbox` flag (common in some corporate setups)

### Audit runs but shows no results
Make sure your frontend dev server is actually running before auditing. Visit the URL in your browser first to confirm it loads, then run the audit.

---

## Notes

- `server.log` in the project root contains all MCP server output — check it first when debugging
- The `.lighthouse-tmp/` folder is created automatically and holds temporary Lighthouse output files
- The `venv/` folder is created on first run and can be deleted to force a clean reinstall

