# `jz` — Terminal Productivity CLI

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![UI](https://img.shields.io/badge/TUI-Textual%20%2B%20Rich-brightgreen.svg)](https://textual.textualize.io/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)]()

> A sleek, minimalist terminal productivity application (Windows & macOS). Synchronize your live **Google Calendar** and **Canvas LMS** deadlines seamlessly inside your terminal with zero visual clutter.

---

```text
 ██╗███████╗  jz v0.1.0 · Academic & Dev Flow
 ██║  ███╔╝   alex.chen@gatech.edu [Default]
╚██║ ██████╗  Google Cal: Connected ●   Canvas: Connected ●
```

---

## ✨ Features

- **Clean, Minimalist Terminal UI:**
  - Compact 3-line ANSI logo and clean status indicators.
  - Transparent layout with no distracting gray bars or clutter.
  - Real, honest connection states: accurately indicates when services are connected or disconnected.
- **Two-Column Dashboard:**
  - **Today’s Agenda:** Google Calendar meetings and classes with relative time badges (`[Ongoing]`, `[In 15m]`, `[Done]`).
  - **Canvas Due Dates:** Upcoming assignments, course codes (e.g., `[CS 2110]`), point totals, and countdowns (e.g., `Due tonight at 11:59 PM`, `Due in 2 days`).
- **Interactive Prompt Box:**
  - Bordered text input with cycleable modes (`Plan`, `Command`, `Ask`).
  - Responsive text input with command history navigation (`Up` / `Down` arrows).
- **Clean Footer Bar:**
  - Quick shortcuts: `? help   / commands   @ context   q quit`.
  - Transparent, uncluttered status indicators.
- **Real Account Connections:**
  - **Canvas LMS:** Connect via Canvas Personal Access Token or direct Canvas Calendar iCal URL (instant, 0-token setup).
  - **Google Calendar:** Connect via private iCal URL or Google Cloud OAuth credentials.
- **Zero-Trace Uninstallation:**
  - Explicit file manifest tracking every file and directory created by `jz`.
  - Clean `jz uninstall` command that purges all configuration, tokens, and caches without leaving a trace.

---

## 🚀 Installation & Global Setup

### 1. Install Globally

```bash
git clone https://github.com/jatgm/jz.git
cd jz
pip install -e .
```

This registers the `jz` command globally on your system PATH:
- **Windows:** PowerShell and Command Prompt (`CMD`)
- **macOS / Linux:** Zsh and Bash

### 2. Launching

Launch the interactive Terminal UI:
```bash
jz
```

Or run fast non-interactive commands in your terminal:
```bash
# View today's schedule and deadlines directly in shell
jz today

# View upcoming Canvas assignments
jz canvas

# View 7-day Google Calendar schedule
jz cal

# Test integration connections
jz sync

# Check all tracked files and storage locations
jz paths
```

---

## ⚡ Connecting Live Accounts

### 1. Canvas LMS (Two Methods)

- **Method A: Canvas Calendar Feed (Easiest — 0 Token Required):**
  1. Open Canvas in your browser -> go to **Calendar**.
  2. Click **Calendar Feed** on the right sidebar and copy the `.ics` URL.
  3. In your shell, run:
     ```bash
     jz connect canvas --url "https://<your-school>.instructure.com/feeds/calendars/user_XXXX.ics"
     ```
     Or inside the interactive prompt:
     ```text
     /connect canvas https://<your-school>.instructure.com/feeds/calendars/user_XXXX.ics
     ```

- **Method B: Canvas API Access Token:**
  1. Go to Canvas -> **Account** -> **Settings** -> **+ New Access Token**.
  2. Run:
     ```bash
     jz connect canvas --url gatech.instructure.com --token <YOUR_TOKEN>
     ```

### 2. Google Calendar

- **Private iCal URL (Instant Setup):**
  1. Open Google Calendar in browser -> Settings for my calendars -> **Integrate Calendar**.
  2. Copy **Secret address in iCal format**.
  3. Run:
     ```bash
     jz connect gcal --url "https://calendar.google.com/calendar/ical/.../basic.ics"
     ```
     Or inside the interactive prompt:
     ```text
     /connect gcal https://calendar.google.com/calendar/ical/.../basic.ics
     ```

---

## 📁 File Tracking & Clean Uninstallation

`jz` strictly manages its storage and leaves 0 leftover files when uninstalled.

### Inspect Tracked Files
To see every file and directory `jz` manages on your system:
```bash
jz paths
```

Managed locations:
- **Windows:** `%APPDATA%\jz` (`config.json`, `tokens.json`, `manifest.json`, caches)
- **macOS / Linux:** `~/.config/jz`

### Clean Zero-Trace Uninstall
To completely remove all configuration, tokens, and data from your computer:
```bash
# Removes all files and directories, prompts for confirmation
jz uninstall

# Non-interactive uninstall with full purge
jz uninstall --yes
```

---

## ⌨️ Interactive Slash Commands & Shortcuts

Inside the `jz` interactive prompt:

| Command | Description |
|---|---|
| `/today` | Focus view on combined calendar events and Canvas deadlines for today |
| `/connect` | Open the interactive live account connection wizard |
| `/sync` | Trigger a fresh background re-sync of Calendar and Canvas data |
| `/canvas` | Open an expanded view of all upcoming assignments grouped by course |
| `/cal` | 7-day schedule view |
| `/plan` | Scan free calendar slots against pending Canvas deadlines and suggest study blocks |
| `/block <time> <title>` | Quick time-blocking (e.g. `/block 2h study for CS exam`) |
| `/demo` | Toggle preview demo mode with sample academic data |
| `/paths` | List all tracked files and directories |
| `/uninstall` | Instructions for clean removal |
| `/help`, `?` | Open the interactive slash command reference sheet |
| `/clear` | Clear prompt feedback and reset view |
| `/quit`, `q` | Exit `jz` |

### Keybindings
- **`Shift+Tab` / `Tab`**: Cycle prompt modes (`Plan` ➔ `Command` ➔ `Ask`)
- **`Up` / `Down`**: Navigate command history in prompt
- **`Esc`**: Return to default dashboard
- **`Ctrl+R` / `F5`**: Quick sync
- **`?`**: View command cheat sheet
- **`q` / `Ctrl+C`**: Quit application

---

## 📜 License
MIT License. Crafted for clean, distraction-free productivity.
