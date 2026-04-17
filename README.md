# 🏙️ Boston 311 Voice AI Platform

> Multi-agent civic intelligence platform built for the Boston 311 Hackathon.  
> Powered by Claude Opus · Boston Open Data · MCP-Connected · Equity-Aware

---

## What It Does

This platform puts a team of 9 AI agents to work on Boston's open civic data. Residents can report issues by voice or text, city departments get ranked dispatch priorities, and analysts get real equity gap measurements — all powered by live data from [data.boston.gov](https://data.boston.gov).

### The 9 Agents

| Agent | Emoji | Role |
|---|---|---|
| **Boston Orchestrator** | 🧠 | Routes questions to the right specialist |
| **Crime & Safety Agent** | 🚔 | Analyses BPD incident data by type, district, and trend |
| **311 Service Requests Agent** | 📞 | Tracks complaints, resolution times, and backlogs |
| **Housing & Property Agent** | 🏠 | Property assessments, permits, and market signals |
| **MBTA Transit Agent** | 🚇 | Ridership, reliability, and service alerts |
| **Building Permits Agent** | 🏗️ | Construction activity and development patterns |
| **Voice AI 311 Intake Agent** | 🎙️ | Guides residents through filing a 311 report, checks duplicates, sets expectations |
| **311 Hotspot & Priority Analyst** | 🗺️ | Ranks chronic problem locations by priority score for crew dispatch |
| **Equity & Accessibility Reporter** | ⚖️ | Compares response times across neighbourhoods weighted by disability and income data |

---

## Key Features

- **Duplicate detection** — checks for open cases on the same street before filing
- **Resolution time estimates** — tells residents how long their issue type typically takes
- **Hotspot scoring** — `Priority Score = report_count × avg_days_to_resolve`
- **Equity analysis** — flags neighbourhoods with the highest overdue rates cross-referenced against disability and income data
- **Multilingual intake** — Voice AI agent responds in English, Spanish, Portuguese, Haitian Creole, or Chinese
- **Live data** — all queries run against the real Boston DataStore in real time
- **Streaming UI** — tool calls appear live in the browser as the agent works

---

## Project Structure

```
311-Hackathon/
├── boston_agents.py   # All 9 agents, tools, and agentic loop
├── app.py             # Flask web server with streaming chat UI
├── web_server.py      # FastAPI backend (alternative server)
├── index.html         # Frontend for web_server.py
├── .env               # Your API key (never committed)
└── .gitignore         # Excludes .env and __pycache__
```

---

## Quickstart

### 1. Clone & install dependencies

```bash
git clone https://github.com/tylerjames18/311-Hackathon.git
cd 311-Hackathon
pip install anthropic requests flask python-dotenv
```

### 2. Add your Anthropic API key

Create a `.env` file in the project root:

```
ANTHROPIC_API_KEY=sk-ant-...
```

Get a key at [console.anthropic.com](https://console.anthropic.com).

### 3. Run the web UI

```bash
python app.py
```

Then open **http://localhost:5000** in your browser.

### 4. Or run from the terminal

```bash
# Interactive mode
python boston_agents.py

# Single query
python boston_agents.py --agent voice_intake --query "There's a pothole on Saratoga Street"
python boston_agents.py --agent hotspot_analyst
python boston_agents.py --agent equity_reporter
```

---

## Agent CLI Reference

```
--agent orchestrator     General-purpose civic data analysis (default)
--agent crime            Crime & safety incident analysis
--agent 311              Resident service request analysis
--agent housing          Property assessments and building permits
--agent transit          MBTA transit data and ridership
--agent permits          Construction permits and development activity
--agent voice_intake     Voice AI 311 intake and deduplication
--agent hotspot_analyst  Repeat-complaint hotspot ranking for crew dispatch
--agent equity_reporter  Neighbourhood equity & response-time gap analysis
```

---

## Data Sources

All data is live from [data.boston.gov](https://data.boston.gov) via the CKAN DataStore API.

| Dataset | Resource ID |
|---|---|
| 311 Service Requests 2025 | `9d7c2214-4709-478a-a2e8-fb2020a5bb94` |
| 311 Service Requests 2026 YTD | `1a0b420d-99f1-4887-9851-990b2a5a6e17` |
| Crime Incidents 2023–present | `b973d8cb-eeb2-4e7e-99da-c92938efc9c0` |
| 300+ additional datasets | Searchable via `search_datasets` tool |

---

## Example Questions to Try

**Voice Intake**
- *"I want to report a pothole on Saratoga Street in East Boston"*
- *"There's graffiti on the wall outside 45 Blue Hill Ave"*
- *"A car has been abandoned on my street for two weeks"*

**Hotspot Analyst**
- *"Show me the top repeat-complaint hotspots across Boston"*
- *"Generate a priority list for the Public Works department"*

**Equity Reporter**
- *"Which neighbourhoods are being underserved by 311?"*
- *"Show me the equity gap in city service delivery"*

**General**
- *"What are the top 5 neighbourhoods with the most 311 complaints?"*
- *"Compare crime rates between Back Bay and Dorchester"*
- *"Where is the most construction happening in Boston?"*

---

## Tech Stack

| Layer | Technology |
|---|---|
| AI Model | Claude Opus (`claude-opus-4-7`) |
| Agent Framework | Anthropic Python SDK — agentic tool-use loop |
| Data | Boston Open Data CKAN API |
| Web Server | Flask with Server-Sent Events (streaming) |
| Alt Backend | FastAPI + uvicorn |
| Frontend | Vanilla JS + marked.js (markdown rendering) |

---

## Built By

**Jude Ighomena** — Janna AI Research Labs  
Boston 311 Hackathon 2026
