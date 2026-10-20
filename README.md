# `jz` — Terminal Productivity CLI

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![UI](https://img.shields.io/badge/TUI-Textual%20%2B%20Rich-brightgreen.svg)](https://textual.textualize.io/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)]()

> A sleek, cross-platform CLI productivity application (Windows & macOS) inspired by the minimalist developer aesthetic of **Cursor Agent**, **Antigravity CLI**, and **Claude Code**. Synchronize your **Google Calendar** and **Canvas LMS** deadlines seamlessly inside your terminal.

---

```text
   ██╗███████╗
   ██║╚══███╔╝   ⚡ jz CLI v0.1.0 · Cross-Platform Terminal Productivity
   ██║  ███╔╝    Connected: student@university.edu  [Profile: Default]
██ ██║ ███╔╝     Workspace: D:/Projects/jz
╚████║███████╗   Integrations: Google Calendar ●  Canvas LMS ●
 ╚═══╝╚══════╝
```

---

## ✨ Features

- **Sleek Aesthetic:**
  - Modern ASCII/pixel logo rendered in vibrant ANSI gradients.
  - Session metadata block with connected account, active profile, and workspace path.
  - Notice & tips banner (bordered with a solid vertical yellow/cyan bar, dismissible with `Esc`).
- **Dynamic Two-Column Dashboard:**
  - **Today’s Agenda:** Google Calendar meetings and classes with relative time badges (`[Ongoing]`, `[In 15m]`, `[Done]`, `[At 04:30 PM]`).
  - **Canvas Due Dates:** Upcoming assignments, course codes (e.g., `[CS 2110]`), point totals, and countdowns (e.g., `Due tonight at 11:59 PM`, `Due in 2 days`).
- **Interactive Prompt Box:**
  - Distinct colored outline box with Cursor's neon/green rounded border.
  - Mode toggle indicator directly beneath:
    - `◉ Plan (shift+tab to cycle modes)`
    - `◉ Command (shift+tab to cycle modes)`
    - `◉ Ask (shift+tab to cycle modes)`
  - Responsive text input with command history navigation (`Up` / `Down` arrows).
- **Footer Status Bar:**
  - Quick shortcuts: `? for help  ·  / commands  ·  @ context  ·  ! shell  ·  q quit`.
  - Right-aligned live sync indicator: `Google Cal: Synced ●  ·  Canvas: Synced ●  ·  Status: Idle`.
- **Intelligent Study Planner (`/plan`):**
  - Scans free calendar slots and correlates them with pending Canvas deadlines to suggest dedicated study blocks.
- **Quick Time-Blocking (`/block`):**
  - Schedule focus blocks into Google Calendar directly from the prompt: `/block 2h CS 2110 HW`.
- **Graceful Fallback / Demo Mode:**
  - Works immediately out of the box with realistic student demo data if credentials have not been configured yet!

---

## 🚀 Installation & Global Setup

### 1. Clone & Install Globally

```bash
git clone https://github.com/user/jz.git
cd jz
pip install -e .
```

This registers the `jz` command globally on your system PATH:
- **Windows:** PowerShell and Command Prompt (`CMD`)
- **macOS / Linux:** Zsh and Bash

### 2. Launching

To launch the full interactive Terminal UI:
```bash
jz
```

You can also run quick non-interactive CLI commands directly from your shell:
```bash
# View today's schedule and deadlines directly in terminal
jz today

# View upcoming Canvas assignments
jz canvas

# View 7-day Google Calendar schedule
jz cal

# Check sync status
jz sync

# View or update configuration
jz config
```

---

## ⌨️ Interactive Slash Commands & Shortcuts

Inside the `jz` interactive prompt:

| Command | Description |
|---|---|
| `/today` | Focus view on combined calendar events and Canvas deadlines for today |
| `/sync` | Trigger a background re-sync of Calendar and Canvas data |
| `/canvas` | Open an expanded view of all upcoming assignments grouped by course |
| `/cal` | 7-day schedule view |
| `/plan` | Scan free calendar slots against pending Canvas deadlines and suggest study blocks |
| `/block <time> <title>` | Quick time-blocking (e.g. `/block 2h study for CS exam`) |
| `/config` | Open the interactive configuration wizard |
| `/set-canvas <url> <token>` | Quick command to save Canvas LMS endpoint and API token |
| `/set-email <email>` | Set user email |
| `/help`, `?` | Open the interactive slash command reference sheet |
| `/clear` | Clear prompt feedback and reset view |
| `/quit`, `q` | Exit `jz` |

### Keybindings
- **`Shift+Tab` / `Tab`**: Cycle prompt modes (`Plan` ➔ `Command` ➔ `Ask`)
- **`Up` / `Down`**: Navigate command history in prompt
- **`Esc`**: Dismiss tips banner or return to default dashboard
- **`Ctrl+R` / `F5`**: Trigger background sync
- **`?`**: View command cheat sheet
- **`q` / `Ctrl+C`**: Quit application

---

## 🔐 Integrations & Authentication

### A. Google Calendar API (OAuth2)
1. Tokens are persisted securely at:
   - **Windows:** `%APPDATA%\jz\tokens.json`
   - **macOS / Linux:** `~/.config/jz/tokens.json`
2. Place your Google Cloud OAuth2 Client Secret JSON at `%APPDATA%\jz\credentials.json` (or `~/.config/jz/credentials.json`).
3. Running local authentication uses `InstalledAppFlow.run_local_server` to authenticate via loopback in your browser.

### B. Canvas LMS API
1. Generate a Personal Access Token in Canvas:
   - Navigate to your institution's Canvas (`Account` ➔ `Settings` ➔ `+ New Access Token`).
2. Configure it in `jz` using either:
   - In the TUI prompt: `/set-canvas https://canvas.instructure.com <YOUR_TOKEN>`
   - In your shell: `jz config --canvas-url https://canvas.instructure.com --canvas-token <YOUR_TOKEN>`
3. Configuration is saved locally in:
   - **Windows:** `%APPDATA%\jz\config.json`
   - **macOS / Linux:** `~/.config/jz/config.json`

---

## 📁 Project Architecture

```text
jz/
├── pyproject.toml              # Package metadata & global `jz` script entry point
├── README.md                   # Setup & user documentation
├── .gitignore
└── jz_cli/
    ├── __init__.py             # Version and package info
    ├── main.py                 # CLI entry point (Typer), subcommands & routing
    ├── config.py               # Cross-platform config & token persistence
    ├── services/
    │   ├── __init__.py
    │   ├── calendar_service.py # Google Calendar API client, time-blocking & free slots
    │   └── canvas_service.py   # Canvas LMS REST API client & countdown calculations
    └── ui/
        ├── __init__.py
        ├── app.py              # Root Textual App & event loop coordinator
        ├── header.py           # Modern ASCII logo, session metadata & notice banner
        ├── dashboard.py        # Split today view, canvas view, week cal & study planner
        └── prompt_input.py     # Neon-bordered prompt box, mode switcher & footer
```

---

## 📜 License
MIT License. Crafted with clean architecture for high-velocity student and developer workflows.
