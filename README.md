# `jz` — Cross-Platform Terminal Productivity CLI

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![UI](https://img.shields.io/badge/TUI-Textual%20%2B%20Rich-brightgreen.svg)](https://textual.textualize.io/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> A sleek, minimalist terminal productivity application (Windows & macOS). Synchronize your live **Google Calendar** and **Canvas LMS** deadlines seamlessly inside your terminal with zero visual clutter.

---

```text
 ██╗███████╗  jz v0.1.0 · Terminal Productivity
 ██║  ███╔╝   alex.chen@gatech.edu [Default]
╚██║ ██████╗  Google Cal: Connected ●   Canvas: Connected ●
```

---

## 📑 Table of Contents

- [Overview & Aesthetics](#-overview--aesthetics)
- [Installation & Global Setup](#-installation--global-setup)
- [Connecting Live Accounts](#-connecting-live-accounts)
  - [Canvas LMS (iCal Feed or API Token)](#1-canvas-lms)
  - [Google Calendar (iCal Feed or OAuth2)](#2-google-calendar)
- [Terminal Layout & Modes](#-terminal-layout--modes)
- [CLI Commands Reference](#-cli-commands-reference)
- [Interactive Slash Commands](#-interactive-slash-commands)
- [File Tracking & Zero-Trace Uninstall](#-file-tracking--zero-trace-uninstall)
- [Project Architecture](#-project-architecture)
- [Development & Testing](#-development--testing)
- [License](#-license)

---

## 🎨 Overview & Aesthetics

`jz` is engineered for students and developers who live in the terminal and want instant visibility into their academic commitments and deadlines without opening browser tabs:

- **Distraction-Free Minimalist Design:** Transparent UI with crisp ANSI borders, zero background bars, and clean spacing.
- **Dynamic Two-Column Dashboard:**
  - **Today's Agenda:** Real-time Google Calendar schedule with status badges (`[Ongoing]`, `[In 15m]`, `[Done]`).
  - **Canvas Due Dates:** Sorted assignment countdowns (`Due tonight at 11:59 PM`, `Tomorrow`, `In 2 days`) and point values.
- **Intelligent Study Planner (`/plan`):** Analyzes free calendar gaps against impending submission deadlines to suggest dedicated study blocks.
- **One-Command Time-Blocking (`/block`):** Schedule focus sessions into Google Calendar directly from the prompt: `/block 2h CS 2110 Midterm`.
- **Honest Connection States:** Accurately reports `Connected ●` or `Disconnected ○`—no misleading mock data unless `--demo` mode is explicitly requested.

---

## 🚀 Installation & Global Setup

### 1. Clone & Install Globally

```bash
git clone https://github.com/jatgm/jz.git
cd jz
pip install -e .
```

This registers the `jz` executable globally on your system PATH:
- **Windows:** PowerShell and Command Prompt (`CMD`)
- **macOS / Linux:** Zsh and Bash

### 2. Verify Installation

```bash
jz --version
# Output: jz CLI v0.1.0
```

---

## ⚡ Connecting Live Accounts

`jz` supports both **instant 0-token setup** (via private iCal feeds) and **full API token/OAuth authentication**.

### 1. Canvas LMS

#### Method A: Calendar Feed (Recommended — 0 Token Required)
Every Canvas user has an auto-updating private calendar feed with no token generation required:
1. Open Canvas in your web browser.
2. Click **Calendar** in the left sidebar.
3. In the lower-right sidebar, click **Calendar Feed**.
4. Copy the `.ics` URL (e.g., `https://<school>.instructure.com/feeds/calendars/user_XXXX.ics`).
5. Link it in `jz`:
   ```bash
   jz connect canvas --url "https://<school>.instructure.com/feeds/calendars/user_XXXX.ics"
   ```
   Or inside the interactive prompt:
   ```text
   /connect canvas https://<school>.instructure.com/feeds/calendars/user_XXXX.ics
   ```

#### Method B: Personal Access Token
For full course enrollment queries and detailed assignment metadata:
1. In Canvas, go to **Account** -> **Settings**.
2. Scroll to **Approved Integrations** and click **+ New Access Token**.
3. Copy your generated token and run:
   ```bash
   jz connect canvas --url gatech.instructure.com --token <YOUR_TOKEN>
   ```
   Or inside the interactive prompt:
   ```text
   /connect canvas gatech.instructure.com <YOUR_TOKEN>
   ```

---

### 2. Google Calendar

#### Method A: Private iCal Address (Instant — 0 GCP Project Required)
1. Open [Google Calendar](https://calendar.google.com/) in your browser.
2. In the left panel, hover over your calendar, click `...` -> **Settings and sharing**.
3. Scroll down to **Integrate calendar** -> copy **Secret address in iCal format**.
4. Link it in `jz`:
   ```bash
   jz connect gcal --url "https://calendar.google.com/calendar/ical/.../basic.ics"
   ```
   Or inside the interactive prompt:
   ```text
   /connect gcal https://calendar.google.com/calendar/ical/.../basic.ics
   ```

#### Method B: Google OAuth 2.0 Credentials
1. Download your `credentials.json` from the [Google Cloud Console](https://console.cloud.google.com/) (Calendar API enabled).
2. Place it in `%APPDATA%\jz\credentials.json` (Windows) or `~/.config/jz/credentials.json` (macOS/Linux).
3. The app will automatically initiate a local browser loopback login and store OAuth tokens in `tokens.json`.

---

## 🖥️ Terminal Layout & Modes

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│  ██╗███████╗  jz v0.1.0 · alex.chen@gatech.edu [Default]                   │
│  ██║  ███╔╝   Google Cal: Connected ●   Canvas: Connected ●                │
│ ╚██║ ██████╗  Type /connect to link accounts · /help for shortcuts          │
├──────────────────────────────────────┬──────────────────────────────────────┤
│ 📅 Today's Agenda (4 events)          │ 📚 Canvas Due Dates (5 upcoming)      │
│ Time       Event Title       Status  │ Course    Assignment        Pts  Due │
│ 09:30 AM   CS 2110 Lecture   [Done]  │ [CS 2110] HW 4 Memory Alloc 100  Tmr │
│ 11:00 AM   MATH 3010 Linear  [Done]  │ [MATH]    Problem Set 5      50  2d  │
│ 02:00 PM   Senior Capstone   [In 1h] │ [PHYS]    WebAssign 06       40  3d  │
│ 04:30 PM   Office Hours      [In 3h] │ [CS 4400] Database Phase 2  150  5d  │
├──────────────────────────────────────┴──────────────────────────────────────┤
│ ┌─ Input ─────────────────────────────────────────────────────────────────┐ │
│ │ [Plan] > type /plan, /block 2h study, or ask for focus schedules...     │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│ ◉ Plan  (shift+tab to cycle modes: Plan · Command · Ask)                    │
│                                                                             │
│ ? help   / commands   @ context   q quit       Google: Connected ●  Canvas: Connected ● │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Prompt Modes (Cycle with `Shift+Tab` or `Tab`)
1. **◉ Plan Mode:** Default mode optimized for study scheduling. Type `/plan` to match calendar openings with deadlines, or `/block 2h CS 2110` to reserve calendar time.
2. **◉ Command Mode:** Directly run slash commands (`/today`, `/canvas`, `/cal`, `/sync`, `/connect`).
3. **◉ Ask Mode:** Natural language academic queries:
   - *"What is due today?"* -> Lists today's submission deadlines.
   - *"When is my next class?"* -> Highlights the next scheduled event.
   - *"Am I free at 2pm?"* -> Evaluates calendar availability.

---

## 💻 CLI Commands Reference

`jz` works both as an interactive TUI and as a fast shell CLI for terminal scripts:

| Command | Usage | Description |
|---|---|---|
| `jz` | `jz` | Launch full interactive Terminal UI |
| `jz today` | `jz today [--demo]` | Quick terminal summary of today's schedule and deadlines |
| `jz canvas` | `jz canvas [--demo]` | Print all upcoming Canvas assignments |
| `jz cal` | `jz cal [--days 7]` | Print upcoming Google Calendar schedule |
| `jz paths` | `jz paths` | Show all files and directories managed by `jz` |
| `jz uninstall` | `jz uninstall [--yes]` | Complete zero-trace purge of all configuration and data |
| `jz connect` | `jz connect [canvas\|gcal]` | Interactive connection wizard for live accounts |
| `jz sync` | `jz sync` | Test API connections and refresh caches |
| `jz config` | `jz config [--email ...]` | View or update local configuration settings |

---

## ⌨️ Interactive Slash Commands

Inside the `jz` interactive prompt:

| Slash Command | Description |
|---|---|
| `/today` | Switch to today's split view (Agenda + Canvas deadlines) |
| `/connect` | Open the interactive connection guide for Canvas & Google Calendar |
| `/sync` | Trigger a fresh background re-sync of Calendar and Canvas data |
| `/canvas` | Open an expanded table of all upcoming assignments grouped by course |
| `/cal` | 7-day schedule view |
| `/plan` | Scan free calendar slots against pending deadlines and suggest study blocks |
| `/block <time> <title>` | Quick time-blocking (e.g., `/block 2h CS 2110 HW` or `/block 45m Physics`) |
| `/demo` | Toggle preview demo mode on/off with realistic sample data |
| `/paths` | List all tracked files and directories |
| `/uninstall` | Instructions and command for clean zero-trace removal |
| `/help`, `?` | Open the interactive slash command reference sheet |
| `/clear` | Clear prompt feedback and reset view |
| `/quit`, `q` | Exit `jz` |

### Keybindings
- **`Shift+Tab` / `Tab`**: Cycle prompt modes (`Plan` ➔ `Command` ➔ `Ask`)
- **`Up` / `Down`**: Navigate command history in prompt
- **`Esc`**: Return to default dashboard view
- **`Ctrl+R` / `F5`**: Quick sync
- **`?`**: View command cheat sheet
- **`q` / `Ctrl+C`**: Quit application

---

## 📁 File Tracking & Zero-Trace Uninstall

`jz` strictly tracks every file and directory it creates, ensuring a clean system footprint.

### Inspect Tracked Storage
To view every file managed by `jz`:
```bash
jz paths
```

Output:
```text
                    jz — Managed Files & Storage Inventory
┌──────────────────────────┬──────────────┬──────────────┬────────────────────┐
│ Item Name                │ Status       │         Size │ Path               │
├──────────────────────────┼──────────────┼──────────────┼────────────────────┤
│ Configuration Directory  │ Exists       │       1473 B │ %APPDATA%\jz       │
│ Config File              │ Exists       │        232 B │ config.json        │
│ OAuth Tokens             │ Not created  │            — │ tokens.json        │
│ OAuth Credentials        │ Not created  │            — │ credentials.json   │
│ Calendar Cache           │ Not created  │            — │ cache_calendar.json│
│ Canvas Cache             │ Not created  │            — │ cache_canvas.json  │
│ Manifest File            │ Exists       │       1241 B │ manifest.json      │
└──────────────────────────┴──────────────┴──────────────┴────────────────────┘
```

Storage locations:
- **Windows:** `%APPDATA%\jz\` (`C:\Users\<User>\AppData\Roaming\jz\`)
- **macOS / Linux:** `~/.config/jz/` (or `$XDG_CONFIG_HOME/jz/`)

### Zero-Trace Uninstallation
To completely wipe all configuration, credentials, caches, and optionally remove the python package:
```bash
# Interactive uninstallation (prompts for confirmation)
jz uninstall

# Non-interactive complete purge
jz uninstall --yes
```

---

## 🏛️ Project Architecture

```text
jz/
├── pyproject.toml              # Package metadata & global `jz` script entry point
├── README.md                   # Full documentation & setup guides
├── .gitignore                  # Git ignore rules for virtual environments & tokens
├── tests/                      # Automated test suite (20 tests passed)
│   ├── test_cli_runner.py      # CLI Typer command tests
│   ├── test_config.py          # Path resolution & configuration tests
│   ├── test_services.py        # Calendar & Canvas logic, badge & countdown tests
│   ├── test_tracker.py         # File manifest & uninstallation tests
│   └── test_tui.py             # Textual TUI lifecycle & slash command tests
└── jz_cli/
    ├── __init__.py             # Version metadata
    ├── main.py                 # CLI entry point (Typer), subcommands & UTF-8 handler
    ├── config.py               # Cross-platform config & token persistence
    ├── tracker.py              # File tracking manifest & zero-trace uninstaller
    ├── services/
    │   ├── __init__.py
    │   ├── calendar_service.py # Google Calendar API, private iCal parsing, free slots
    │   └── canvas_service.py   # Canvas REST API, iCal feed parsing, countdown engine
    └── ui/
        ├── __init__.py
        ├── app.py              # Textual App root & slash command dispatcher
        ├── header.py           # Compact 3-line ANSI brand & session indicators
        ├── dashboard.py        # Two-column dashboard, /canvas, /cal, /plan & /connect
        └── prompt_input.py     # Bordered prompt input, mode switcher & transparent footer
```

---

## 🧪 Development & Testing

### Running the Test Suite
The project includes a comprehensive automated test suite covering CLI invocation, TUI event loops, service parsing, and file tracking:

```bash
pytest -v
```

Output:
```text
============================= 20 passed in 1.08s ==============================
```

---

## 📜 License
Distributed under the **MIT License**. Crafted for clean, distraction-free productivity.
