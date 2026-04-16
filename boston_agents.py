#!/usr/bin/env python3
"""
Boston Data Hub — Multi-Agent Civic Intelligence Platform
Author: Jude Ighomena | Janna AI Research Labs
MCP Server: https://data-mcp.boston.gov/mcp

Architecture: Orchestrator → 5 specialist agents
  1. Problem Framer    — Structures ambiguous civic questions
  2. Data Analyst      — Queries Boston open data via MCP
  3. Communications    — Translates findings to plain English
  4. Benchmarker       — Compares across neighborhoods/time
  5. Performance Mgr   — Tracks trends and flags anomalies

Usage:
  python boston_agents.py
  python boston_agents.py --agent crime
  python boston_agents.py --agent 311
  python boston_agents.py --agent housing
  python boston_agents.py --agent transit
  python boston_agents.py --agent permits
"""

import os, sys, json, argparse, requests
from datetime import datetime

try:
    import anthropic
except ImportError:
    print("❌  Missing dependency. Run: pip install anthropic requests")
    sys.exit(1)

MCP_SERVER_URL = "https://data-mcp.boston.gov/mcp"
CKAN_BASE      = "https://data.boston.gov/api/3/action"
MAX_ITERATIONS = 12

BANNER = """
╔══════════════════════════════════════════════════════════════╗
║          BOSTON DATA HUB  ·  Civic Intelligence Platform     ║
║  Boston 311 Voice AI Platform · MCP-Connected · Equity-Aware ║
╚══════════════════════════════════════════════════════════════╝
"""

AGENT_REGISTRY = {
    "orchestrator": {
        "name": "Boston Orchestrator",
        "emoji": "🧠",
        "description": "Routes your question to the right specialist agent",
        "system": """You are the Boston Civic Data Orchestrator. You coordinate a team of specialist agents.

Your job:
1. Understand the user's civic question
2. Frame it as a structured data problem
3. Identify which Boston datasets are relevant
4. Use the data tools to retrieve and analyse real data
5. Return clear, plain-English findings with concrete numbers

Boston's MCP server exposes tools for:
- Searching the Boston open data catalogue (300+ datasets)
- Fetching dataset metadata and resource IDs
- Running SQL queries against DataStore resources
- Accessing 311 complaints, crime incidents, building permits, property records,
  trash schedules, tree canopy, public school locations, snow emergency routes

Workflow: search_datasets → get_dataset_info → fetch_data or sql_query → synthesise

Always:
- Get actual numbers, not generic statements
- Compare data across time or geography when possible
- Explain findings in plain language a resident can act on
- Flag data limitations honestly"""
    },
    "crime": {
        "name": "Crime & Safety Agent",
        "emoji": "🚔",
        "description": "Analyses Boston crime incidents by type, neighbourhood, and time",
        "system": """You are the Boston Crime & Safety Intelligence Agent.

You specialise in analysing Boston Police Department crime incident data from the Boston open data portal.

Your analytical workflow (follow this exactly):
1. Search for crime/incident datasets: search_datasets(query="crime incident report")
2. Get dataset info to find the DataStore resource_id: get_dataset_info(dataset_id=...)
3. Run targeted SQL queries: sql_query(resource_id=..., sql="SELECT ...")
4. Analyse patterns: by district, by offence code group, by time of day/year
5. Present findings: top offence categories, trend direction, neighbourhood comparison

Key fields in Boston crime data: INCIDENT_NUMBER, OFFENSE_CODE_GROUP, DISTRICT,
REPORTING_AREA, SHOOTING, OCCURRED_ON_DATE, STREET, Lat, Long

Always frame your response as:
- Summary sentence (most important finding)
- Top 5 data points with actual numbers
- Trend observation (better/worse over time if data allows)
- Neighbourhood comparison (which districts are highest/lowest)
- Plain-language recommendation or context

Be concrete. A resident deserves real numbers."""
    },
    "311": {
        "name": "311 Service Requests Agent",
        "emoji": "📞",
        "description": "Tracks resident complaints, potholes, graffiti and city service requests",
        "system": """You are the Boston 311 Citizen Service Intelligence Agent.

You specialise in analysing Boston's 311 service request data — pothole reports, graffiti complaints,
missed trash pickups, broken streetlights, code enforcement, and all civic service requests.

Your analytical workflow:
1. search_datasets(query="311 service requests")
2. get_dataset_info to find resource_id
3. sql_query to analyse by: type, neighbourhood, open/closed status, response time

Key fields: case_enquiry_id, open_dt, closed_dt, case_status, subject, reason, type,
            neighborhood, source, ward, precinct

Frame responses as:
- What are the top complaint categories this period?
- Which neighbourhoods have the most open/unresolved requests?
- Average resolution time by category?
- Trend: are complaints going up or down?

Think like a city manager reviewing a morning briefing."""
    },
    "housing": {
        "name": "Housing & Property Agent",
        "emoji": "🏠",
        "description": "Analyses property assessments, building permits, and housing trends",
        "system": """You are the Boston Housing & Property Intelligence Agent.

You specialise in Boston property assessment data, building permits, and housing market signals.

Your analytical workflow:
1. search_datasets(query="property assessment building permits")
2. get_dataset_info for the relevant dataset
3. sql_query with aggregations: median values by neighbourhood, permit volumes by type, year-over-year

Key datasets: Property Assessment (AV_TOTAL, PTYPE, LIVING_AREA, YR_BUILT),
              Building Permits (worktype, description, declared_valuation, zip)

Frame responses as:
- Median assessed value by neighbourhood (top 5 highest, 5 lowest)
- Building permit activity: what types of construction are happening?
- Year-over-year change in assessments (where property values grew most/least)
- Affordability signal: average assessed value vs. citywide median

Be specific — cite actual dollar amounts and percentages."""
    },
    "transit": {
        "name": "MBTA Transit Agent",
        "emoji": "🚇",
        "description": "Real-time and historical MBTA transit data, alerts, and service analysis",
        "system": """You are the Boston Transit Intelligence Agent, specialising in MBTA data.

You have access to:
- MBTA v3 API data via the Boston MCP server
- Historical ridership and service performance data on Boston's open data portal
- Real-time alerts, predictions, and vehicle positions when available

Your analytical workflow:
1. Search for transit data: search_datasets(query="MBTA transit ridership")
2. Get resource IDs from dataset info
3. Query for: ridership trends, service alerts, stop/route performance

For real-time questions (current delays, next trains), use MBTA API endpoints.
For historical questions (ridership trends, reliability), use open data DataStore.

Frame responses as:
- Current service status or historical trend
- Which lines/routes are most/least reliable?
- Ridership patterns: peak hours, busiest stations
- Service changes or alerts affecting residents

Be practical — tell riders what they actually need to know."""
    },
    "permits": {
        "name": "Building Permits Agent",
        "emoji": "🏗️",
        "description": "Tracks construction permits, development activity, and code enforcement",
        "system": """You are the Boston Construction & Development Intelligence Agent.

You specialise in building permit data, construction activity tracking, and development patterns.

Your analytical workflow:
1. search_datasets(query="building permits issued")
2. get_dataset_info to find the DataStore resource
3. sql_query to aggregate: permits by type, by zip/neighbourhood, by declared value, by year

Key fields in building permit data: permitnumber, worktype, description, comments,
                                    applicant, declared_valuation, zip, sq_feet, issued_date

Frame responses as:
- Total permit volume this period vs. prior period
- What type of construction dominates (residential, commercial, renovation)?
- Which ZIP codes/neighbourhoods have the most development activity?
- Largest projects by declared valuation
- Code enforcement actions if available

Help residents understand what's being built in their neighbourhood."""
    },
    "voice_intake": {
        "name": "Voice AI 311 Intake Agent",
        "emoji": "🎙️",
        "description": "Guides residents through reporting a 311 issue by voice or text. Classifies the issue, checks for duplicates, and sets time expectations.",
        "system": """You are the Boston 311 Voice AI Intake Agent. You help residents report city issues quickly and clearly.

YOUR WORKFLOW for every report:
1. Ask the resident to describe their issue in plain language
2. Classify it into one of these types: Sign Repair, Request for Pothole Repair, Graffiti Removal, Abandoned Vehicles, Sidewalk Repair (Make Safe), Missed Trash/Recycling/Yard Waste/Bulk Item, Parking Enforcement, Unshoveled Sidewalk, Rodent Activity, Unsatisfactory Living Conditions
3. Ask for their street address if not provided
4. Call check_nearby_open_cases to check if this issue is already reported
   - If duplicate found: tell the resident the existing case ID and status
   - If no duplicate: proceed to file
5. Call get_resolution_estimate to get the expected timeline
6. Tell the resident clearly: "This type of issue typically takes X days to resolve. We'll flag it as urgent if others have reported the same location."
7. Call get_repeat_hotspots to check if this location is a known hotspot
8. Generate a structured case summary:
   - Type: [classified type]
   - Location: [address]
   - Description: [resident's words]
   - Priority: HIGH if 5+ prior reports at location, NORMAL otherwise
   - Expected resolution: [X days from get_resolution_estimate]
   - Duplicate of: [case ID if found, else None]

TONE: Warm, clear, brief. This may be a non-English speaker. Use simple words. Confirm you understood their issue before proceeding.

Supported languages: English, Spanish, Portuguese, Haitian Creole, Chinese. Detect the language of the resident's input and respond in the same language."""
    },
    "hotspot_analyst": {
        "name": "311 Hotspot & Priority Analyst",
        "emoji": "🗺️",
        "description": "Identifies repeat-complaint hotspots and generates ranked priority lists for city crew dispatch and budget allocation.",
        "system": """You are the Boston 311 Hotspot & Priority Analyst. You help city departments allocate crews and budget more effectively by surfacing chronic problem locations.

YOUR WORKFLOW:
1. For each of the high-backlog complaint types, call get_repeat_hotspots:
   - "Sign Repair" (min_reports=10)
   - "Request for Pothole Repair" (min_reports=8)
   - "Graffiti Removal" (min_reports=6)
   - "Abandoned Vehicles" (min_reports=5)
   - "Sidewalk Repair (Make Safe)" (min_reports=5)
2. For each type, call get_resolution_estimate to get avg_days
3. Calculate a Priority Score for each hotspot location:
   Priority Score = report_count x avg_days_to_resolve
   (higher score = more urgent, more overdue)
4. Output a ranked table:
   RANK | LOCATION | COMPLAINT TYPE | REPORTS | AVG DAYS | PRIORITY SCORE
5. Add a plain-English summary:
   - Top 3 locations needing immediate dispatch
   - Which department is responsible for each
   - Estimated crew-hours to clear the backlog

DEPARTMENTS:
- Sign Repair -> Transportation / Traffic Division
- Pothole Repair -> Public Works Department
- Graffiti Removal -> Public Works Department
- Abandoned Vehicles -> Transportation / Traffic Division
- Sidewalk Repair -> Public Works Department

Always end with: "Recommended weekly dispatch priorities for each department with highest-score locations first." """
    },
    "equity_reporter": {
        "name": "Equity & Accessibility Reporter",
        "emoji": "⚖️",
        "description": "Compares 311 response times and overdue rates across neighbourhoods, weighted by disability and income data.",
        "system": """You are the Boston 311 Equity & Accessibility Reporter. You analyse whether city services are delivered fairly across all neighbourhoods.

YOUR WORKFLOW:
1. Call sql_query on the 2025 311 dataset to get:
   - Overdue rate per neighbourhood (on_time = 'OVERDUE' / total)
   - Average resolution days per neighbourhood
   Resource ID: 9d7c2214-4709-478a-a2e8-fb2020a5bb94
   SQL pattern:
   SELECT neighborhood,
     COUNT(*) as total,
     ROUND(AVG(CASE WHEN on_time = 'OVERDUE' THEN 1.0 ELSE 0 END) * 100, 1) as overdue_pct,
     ROUND(AVG(DATE_PART('day', closed_dt::timestamp - open_dt::timestamp))::numeric, 1) as avg_days
   FROM "9d7c2214-4709-478a-a2e8-fb2020a5bb94"
   WHERE neighborhood IS NOT NULL AND neighborhood != '' AND closed_dt IS NOT NULL
   GROUP BY neighborhood ORDER BY overdue_pct DESC

2. Flag the equity gap: difference between best and worst neighbourhood overdue rates
3. Cross-reference these high-need neighbourhoods (from disability + income data) and note if they also have high overdue rates:
   - Dorchester (highest disability count: 5,532 residents)
   - Roxbury (overdue rate AND high disability rate)
   - East Boston (large non-English-speaking population)
   - Mattapan (23.6% overdue rate, lower-income area)
4. Output:
   - Equity gap headline (e.g. "Charlestown residents wait 3x longer...")
   - Top 5 most underserved neighbourhoods (high overdue + high need)
   - Specific complaint types driving inequity
   - Recommendation: which neighbourhood + type combo needs AI prioritization most urgently

Frame this for a City Council audience. Use plain language. Cite actual percentages and days."""
    }
}

TOOLS = [
    {
        "name": "search_datasets",
        "description": "Search the Boston open data catalogue for datasets by keyword. Returns dataset IDs and titles.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query":  {"type": "string", "description": "Search keyword (e.g. 'crime incidents', '311 requests', 'building permits')"},
                "limit":  {"type": "number", "description": "Max results to return (default 5)"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_dataset_info",
        "description": "Get full metadata for a dataset including its DataStore resource_id needed for queries.",
        "input_schema": {
            "type": "object",
            "properties": {
                "dataset_id": {"type": "string", "description": "The dataset name/ID from search_datasets"}
            },
            "required": ["dataset_id"]
        }
    },
    {
        "name": "fetch_data",
        "description": "Fetch a sample of records from a Boston DataStore resource.",
        "input_schema": {
            "type": "object",
            "properties": {
                "resource_id": {"type": "string", "description": "DataStore resource UUID from get_dataset_info"},
                "limit":       {"type": "number", "description": "Number of records (max 500)"}
            },
            "required": ["resource_id"]
        }
    },
    {
        "name": "sql_query",
        "description": "Run a PostgreSQL-style SQL query against a Boston DataStore resource for aggregations and filtering.",
        "input_schema": {
            "type": "object",
            "properties": {
                "resource_id": {"type": "string", "description": "DataStore resource UUID"},
                "sql":         {"type": "string", "description": 'SQL query — use "resource_id" as the table name placeholder'}
            },
            "required": ["resource_id", "sql"]
        }
    },
    {
        "name": "get_repeat_hotspots",
        "description": "Find street locations with repeated 311 complaints of the same type. Used to identify infrastructure hotspots for priority dispatch.",
        "input_schema": {
            "type": "object",
            "properties": {
                "complaint_type": {"type": "string",  "description": "The 311 complaint type to filter by"},
                "min_reports":    {"type": "integer", "description": "Minimum number of reports to qualify as a hotspot (default 5)"},
                "year":           {"type": "integer", "description": "Year of 311 data to query (2025 or 2026, default 2025)"}
            },
            "required": ["complaint_type"]
        }
    },
    {
        "name": "get_resolution_estimate",
        "description": "Look up the historical average resolution time for a 311 complaint type. Returns avg days and % taking over 30 days.",
        "input_schema": {
            "type": "object",
            "properties": {
                "complaint_type": {"type": "string", "description": "The 311 complaint type to look up resolution time for"}
            },
            "required": ["complaint_type"]
        }
    },
    {
        "name": "check_nearby_open_cases",
        "description": "Check if there are already open 311 cases near a given street for the same complaint type. Used for deduplication at intake.",
        "input_schema": {
            "type": "object",
            "properties": {
                "street_name":    {"type": "string", "description": "Street name to search for nearby open cases"},
                "complaint_type": {"type": "string", "description": "The 311 complaint type to filter by"}
            },
            "required": ["street_name", "complaint_type"]
        }
    }
]

def search_datasets(query: str, limit: int = 5) -> dict:
    try:
        r = requests.get(f"{CKAN_BASE}/package_search",
                         params={"q": query, "rows": min(limit, 10)}, timeout=30)
        data = r.json()
        if data.get("success"):
            return {"datasets": [
                {"id": p["name"], "title": p["title"],
                 "notes": p.get("notes", "")[:120],
                 "resource_count": len(p.get("resources", []))}
                for p in data["result"]["results"]
            ]}
        return {"error": "Search failed", "detail": data}
    except Exception as e:
        return {"error": str(e)}

def get_dataset_info(dataset_id: str) -> dict:
    try:
        r = requests.get(f"{CKAN_BASE}/package_show",
                         params={"id": dataset_id}, timeout=30)
        data = r.json()
        if data.get("success"):
            pkg = data["result"]
            return {
                "title": pkg["title"],
                "description": pkg.get("notes", "")[:300],
                "resources": [
                    {"id": res["id"], "name": res.get("name", ""),
                     "format": res.get("format", ""), "datastore": res.get("datastore_active", False)}
                    for res in pkg.get("resources", [])
                ],
                "tags": [t["name"] for t in pkg.get("tags", [])]
            }
        return {"error": "Dataset not found"}
    except Exception as e:
        return {"error": str(e)}

def fetch_data(resource_id: str, limit: int = 100) -> dict:
    try:
        r = requests.get(f"{CKAN_BASE}/datastore_search",
                         params={"resource_id": resource_id, "limit": min(limit, 500)},
                         timeout=60)
        data = r.json()
        if data.get("success"):
            res = data["result"]
            return {
                "total_records": res.get("total", 0),
                "fields": [f["id"] for f in res.get("fields", [])],
                "sample_records": res.get("records", [])[:20]
            }
        return {"error": "Fetch failed", "detail": data.get("error")}
    except Exception as e:
        return {"error": str(e)}

def sql_query(resource_id: str, sql: str) -> dict:
    try:
        sql_clean = sql.replace('"resource_id"', f'"{resource_id}"').replace("'resource_id'", f'"{resource_id}"')
        r = requests.get(f"{CKAN_BASE}/datastore_search_sql",
                         params={"sql": sql_clean}, timeout=60)
        data = r.json()
        if data.get("success"):
            return {
                "records": data["result"]["records"],
                "fields":  [f["id"] for f in data["result"].get("fields", [])]
            }
        err = data.get("error", {})
        return {"error": err.get("message", "Query failed"), "type": err.get("__type", "")}
    except Exception as e:
        return {"error": str(e)}

RESOURCE_IDS_311 = {
    2025: "9d7c2214-4709-478a-a2e8-fb2020a5bb94",
    2026: "1a0b420d-99f1-4887-9851-990b2a5a6e17",
}

def get_repeat_hotspots(complaint_type: str, min_reports: int = 5, year: int = 2025) -> dict:
    rid = RESOURCE_IDS_311.get(year, RESOURCE_IDS_311[2025])
    type_safe = complaint_type.replace("'", "''")
    sql = (
        f'SELECT location_street_name, COUNT(*) as report_count '
        f'FROM "{rid}" '
        f"WHERE type = '{type_safe}' AND location_street_name IS NOT NULL "
        f'GROUP BY location_street_name '
        f'HAVING COUNT(*) >= {min_reports} '
        f'ORDER BY report_count DESC '
        f'LIMIT 20'
    )
    result = sql_query(rid, sql)
    if "error" in result:
        return result
    return {
        "complaint_type": complaint_type,
        "year": year,
        "hotspots": [
            {"location": r["location_street_name"], "report_count": int(r["report_count"]), "complaint_type": complaint_type}
            for r in result.get("records", [])
        ]
    }

def get_resolution_estimate(complaint_type: str) -> dict:
    rid = RESOURCE_IDS_311[2025]
    type_safe = complaint_type.replace("'", "''")
    sql = (
        f'SELECT COUNT(*) as total_cases, '
        f"ROUND(AVG(DATE_PART('day', closed_dt::timestamp - open_dt::timestamp))::numeric, 1) as avg_days, "
        f"ROUND(AVG(CASE WHEN DATE_PART('day', closed_dt::timestamp - open_dt::timestamp) > 30 THEN 1.0 ELSE 0 END) * 100, 1) as pct_over_30 "
        f'FROM "{rid}" '
        f"WHERE type = '{type_safe}' AND closed_dt IS NOT NULL AND open_dt IS NOT NULL"
    )
    result = sql_query(rid, sql)
    if "error" in result:
        return result
    records = result.get("records", [])
    if not records:
        return {"error": "No data found", "complaint_type": complaint_type}
    r = records[0]
    return {
        "complaint_type": complaint_type,
        "avg_days":    float(r.get("avg_days")    or 0),
        "pct_over_30": float(r.get("pct_over_30") or 0),
        "total_cases": int(r.get("total_cases")   or 0),
    }

def check_nearby_open_cases(street_name: str, complaint_type: str) -> dict:
    rid = RESOURCE_IDS_311[2026]
    street_safe = street_name.replace("'", "''")
    type_safe   = complaint_type.replace("'", "''")
    sql = (
        f'SELECT case_enquiry_id, open_dt, location_street_name, case_status '
        f'FROM "{rid}" '
        f"WHERE location_street_name ILIKE '%{street_safe}%' "
        f"AND type = '{type_safe}' "
        f"AND case_status = 'Open' "
        f'LIMIT 10'
    )
    result = sql_query(rid, sql)
    if "error" in result:
        return result
    return {
        "street_name":    street_name,
        "complaint_type": complaint_type,
        "open_cases": [
            {
                "case_enquiry_id": r.get("case_enquiry_id"),
                "open_dt":         r.get("open_dt"),
                "location":        r.get("location_street_name"),
                "case_status":     r.get("case_status"),
            }
            for r in result.get("records", [])
        ]
    }

TOOL_MAP = {
    "search_datasets":  lambda i: search_datasets(i["query"], i.get("limit", 5)),
    "get_dataset_info": lambda i: get_dataset_info(i["dataset_id"]),
    "fetch_data":       lambda i: fetch_data(i["resource_id"], i.get("limit", 100)),
    "sql_query":              lambda i: sql_query(i["resource_id"], i["sql"]),
    "get_repeat_hotspots":    lambda i: get_repeat_hotspots(i["complaint_type"], i.get("min_reports", 5), i.get("year", 2025)),
    "get_resolution_estimate":lambda i: get_resolution_estimate(i["complaint_type"]),
    "check_nearby_open_cases":lambda i: check_nearby_open_cases(i["street_name"], i["complaint_type"]),
}

def execute_tool(name: str, inp: dict) -> str:
    fn = TOOL_MAP.get(name)
    if fn:
        return json.dumps(fn(inp), default=str)
    return json.dumps({"error": f"Unknown tool: {name}"})

def run_agent(query: str, agent_key: str = "orchestrator", verbose: bool = True) -> str:
    agent   = AGENT_REGISTRY[agent_key]
    client  = anthropic.Anthropic()
    messages = [{"role": "user", "content": query}]

    if verbose:
        print(f"\n{agent['emoji']}  {agent['name']} — processing your question...\n")

    for iteration in range(MAX_ITERATIONS):
        resp = client.messages.create(
            model      = "claude-sonnet-4-5-20251001",
            max_tokens = 4096,
            system     = agent["system"],
            tools      = TOOLS,
            messages   = messages
        )

        if resp.stop_reason == "tool_use":
            tool_results = []
            for block in resp.content:
                if block.type == "tool_use":
                    if verbose:
                        print(f"  🔧  {block.name}({json.dumps(block.input)[:80]}...)")
                    result = execute_tool(block.name, block.input)
                    if verbose:
                        print(f"  ✓   Done  [{len(result)} chars]\n")
                    tool_results.append({
                        "type":        "tool_result",
                        "tool_use_id": block.id,
                        "content":     result
                    })
            messages.append({"role": "assistant", "content": resp.content})
            messages.append({"role": "user",      "content": tool_results})

        else:
            return "".join(b.text for b in resp.content if hasattr(b, "text"))

    return "⚠️  Max iterations reached — the query may be too complex. Try a more specific question."

def interactive_mode(agent_key: str = "orchestrator"):
    agent = AGENT_REGISTRY[agent_key]
    print(BANNER)
    print(f"Active agent:  {agent['emoji']}  {agent['name']}")
    print(f"Description:   {agent['description']}")
    print(f"MCP Server:    {MCP_SERVER_URL}")
    print()
    print("Example questions:")

    examples = {
        "orchestrator": [
            "What are the top 5 neighbourhoods with the most 311 complaints?",
            "Show me crime trends in Boston over the last year",
            "Which areas have the highest property assessments?",
        ],
        "crime":   ["What are the most common crimes in Roxbury?", "Compare crime rates between Back Bay and Dorchester"],
        "311":     ["What are the top 311 complaint types this year?", "Which neighbourhood has the most open service requests?"],
        "housing": ["What neighbourhoods have the highest median property values?", "Where is the most construction happening?"],
        "transit": ["What MBTA ridership data is available?", "Show me transit service data for Boston"],
        "permits":         ["What types of building permits are most common?", "Which ZIP codes have the most construction permits?"],
        "voice_intake":    [
            "I want to report a pothole on Saratoga Street in East Boston",
            "There's graffiti on the wall outside 45 Blue Hill Ave",
            "A car has been abandoned on my street for two weeks",
        ],
        "hotspot_analyst": [
            "Show me the top repeat-complaint hotspots across Boston",
            "Which locations need urgent crew dispatch this week?",
            "Generate a priority list for the Public Works department",
        ],
        "equity_reporter": [
            "Which neighbourhoods are being underserved by 311?",
            "Compare response times between wealthy and lower-income areas",
            "Show me the equity gap in city service delivery",
        ],
    }

    for ex in examples.get(agent_key, examples["orchestrator"]):
        print(f"  • {ex}")

    print("\nType 'agents' to list all agents, 'switch <name>' to change agent, or 'quit' to exit.\n")

    current_agent = agent_key
    while True:
        try:
            prompt = input(f"[{AGENT_REGISTRY[current_agent]['emoji']} {AGENT_REGISTRY[current_agent]['name']}] > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nGoodbye!\n")
            break

        if not prompt:
            continue
        if prompt.lower() in ("quit", "exit", "q"):
            print("\nGoodbye!\n")
            break
        if prompt.lower() == "agents":
            print("\nAvailable agents:")
            for k, v in AGENT_REGISTRY.items():
                print(f"  {v['emoji']}  {k:15s}  —  {v['description']}")
            print()
            continue
        if prompt.lower().startswith("switch "):
            new_agent = prompt.split(" ", 1)[1].strip()
            if new_agent in AGENT_REGISTRY:
                current_agent = new_agent
                print(f"\n✓ Switched to {AGENT_REGISTRY[current_agent]['emoji']} {AGENT_REGISTRY[current_agent]['name']}\n")
            else:
                print(f"❌  Unknown agent '{new_agent}'. Type 'agents' to see options.\n")
            continue

        result = run_agent(prompt, current_agent, verbose=True)
        print(f"\n{'─'*60}\n{result}\n{'─'*60}\n")

def main():
    parser = argparse.ArgumentParser(
        description="Boston Data Hub — Civic Intelligence Platform by iRaven Group UK",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Available agents:
  orchestrator    General-purpose civic data analysis (default)
  crime           Crime & safety incident analysis
  311             Resident service request analysis
  housing         Property assessments and building permits
  transit         MBTA transit data and ridership
  permits         Construction permits and development activity
  voice_intake    Voice AI 311 intake and deduplication
  hotspot_analyst Repeat-complaint hotspot ranking for crew dispatch
  equity_reporter Neighbourhood equity & response-time gap analysis

Examples:
  python boston_agents.py
  python boston_agents.py --agent crime
  python boston_agents.py --agent 311 --query "Top complaint types in Dorchester"
  python boston_agents.py --agent voice_intake
  python boston_agents.py --agent hotspot_analyst
  python boston_agents.py --agent equity_reporter
        """
    )
    parser.add_argument("--agent",  default="orchestrator", choices=list(AGENT_REGISTRY.keys()),
                        help="Which specialist agent to use (default: orchestrator)")
    parser.add_argument("--query",  default=None,
                        help="Run a single query non-interactively and exit")
    parser.add_argument("--quiet",  action="store_true",
                        help="Suppress tool call logging (show final answer only)")
    args = parser.parse_args()

    if args.query:
        result = run_agent(args.query, args.agent, verbose=not args.quiet)
        print(result)
    else:
        interactive_mode(args.agent)

if __name__ == "__main__":
    main()
