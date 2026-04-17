#!/usr/bin/env python3
"""
Boston Data Hub — Web UI
Run:  python app.py
Open: http://localhost:5000
"""

from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

import os, sys, json, builtins, threading, queue

try:
    from flask import Flask, Response, request, stream_with_context
except ImportError:
    print("❌  Run: pip install flask")
    sys.exit(1)

import boston_agents as hub

app = Flask(__name__)

# ── Inline HTML/CSS/JS ────────────────────────────────────────────────────────

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Boston Data Hub</title>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
     background:#f0f2f5;color:#1a1a2e;height:100vh;display:flex;flex-direction:column}

/* Header */
header{background:#0d1b4b;color:#fff;padding:12px 24px;
       display:flex;align-items:center;gap:12px;flex-shrink:0;box-shadow:0 2px 8px #0003}
header h1{font-size:1.1rem;font-weight:700}
header span{font-size:.78rem;color:#9db4e0;margin-left:4px}

/* Layout */
.layout{display:flex;flex:1;overflow:hidden}

/* Sidebar */
aside{width:250px;background:#fff;border-right:1px solid #e2e8f0;
      overflow-y:auto;flex-shrink:0;padding:8px 0}
.sidebar-label{font-size:.67rem;font-weight:700;color:#94a3b8;
               text-transform:uppercase;letter-spacing:.8px;padding:10px 14px 4px}
.agent-card{display:flex;align-items:flex-start;gap:9px;padding:10px 14px;
            cursor:pointer;transition:background .15s;border-left:3px solid transparent}
.agent-card:hover{background:#f7f9fc}
.agent-card.active{background:#eef3ff;border-left-color:#3b5bdb}
.agent-card .emoji{font-size:1.25rem;flex-shrink:0;line-height:1.5}
.agent-card .name{font-size:.82rem;font-weight:600;color:#1a1a2e}
.agent-card .desc{font-size:.71rem;color:#64748b;margin-top:2px;line-height:1.35}

/* Main chat */
main{flex:1;display:flex;flex-direction:column;overflow:hidden}
#messages{flex:1;overflow-y:auto;padding:20px 24px;display:flex;flex-direction:column;gap:16px}

/* Bubbles */
.bubble{max-width:820px}
.bubble.user{align-self:flex-end}
.bubble.user .body{background:#3b5bdb;color:#fff;border-radius:16px 16px 4px 16px;
                   padding:10px 16px;font-size:.9rem;line-height:1.55;white-space:pre-wrap}
.bubble.agent{align-self:flex-start;width:100%}
.bubble.agent .body{background:#fff;border:1px solid #e2e8f0;
                    border-radius:4px 16px 16px 16px;padding:14px 18px;
                    font-size:.9rem;line-height:1.65}
.meta{font-size:.72rem;color:#94a3b8;margin-bottom:5px}

/* Markdown inside agent bubble */
.bubble.agent .body h1,.bubble.agent .body h2,.bubble.agent .body h3{margin:.55em 0 .25em}
.bubble.agent .body p{margin-bottom:.5em}
.bubble.agent .body ul,.bubble.agent .body ol{padding-left:1.4em;margin-bottom:.5em}
.bubble.agent .body li{margin-bottom:.2em}
.bubble.agent .body code{background:#f1f5f9;border-radius:3px;padding:1px 5px;font-size:.82em}
.bubble.agent .body pre{background:#0f172a;color:#e2e8f0;border-radius:8px;
                         padding:12px;overflow-x:auto;font-size:.79rem;margin-bottom:.6em}
.bubble.agent .body pre code{background:none;padding:0;color:inherit}
.bubble.agent .body table{border-collapse:collapse;width:100%;margin-bottom:.6em;font-size:.82rem}
.bubble.agent .body th,.bubble.agent .body td{border:1px solid #e2e8f0;padding:5px 10px;text-align:left}
.bubble.agent .body th{background:#f8fafc;font-weight:600}
.bubble.agent .body blockquote{border-left:3px solid #3b5bdb;padding-left:12px;
                                color:#475569;margin:.4em 0}

/* Tool log */
details.tool-log{margin-top:10px}
details.tool-log summary{font-size:.75rem;color:#64748b;cursor:pointer;user-select:none;
                          list-style:none;display:flex;align-items:center;gap:5px}
details.tool-log summary:hover{color:#3b5bdb}
.log-wrap{margin-top:6px;background:#f8fafc;border-radius:8px;padding:8px 10px;
          max-height:220px;overflow-y:auto}
.log-line{font-family:"SF Mono",Consolas,monospace;font-size:.74rem;
          color:#475569;padding:1px 0;white-space:pre-wrap;word-break:break-all}
.log-line.tool-call{color:#7c3aed;font-weight:600}
.log-line.ok{color:#059669}

/* Spinner */
.spinner{display:inline-flex;gap:5px;align-items:center;padding:6px 2px}
.dot{width:7px;height:7px;border-radius:50%;background:#94a3b8;
     animation:bounce .9s infinite ease-in-out}
.dot:nth-child(2){animation-delay:.15s}
.dot:nth-child(3){animation-delay:.3s}
@keyframes bounce{0%,80%,100%{transform:scale(.6)}40%{transform:scale(1)}}

/* Input bar */
.input-bar{padding:14px 24px;background:#fff;border-top:1px solid #e2e8f0;
           display:flex;gap:10px;flex-shrink:0;align-items:flex-end}
.badge{font-size:.78rem;color:#64748b;white-space:nowrap;align-self:center;flex-shrink:0}
#input{flex:1;padding:10px 14px;border:1px solid #cbd5e1;border-radius:10px;
       font-size:.9rem;outline:none;resize:none;font-family:inherit;
       min-height:44px;max-height:120px;overflow-y:auto;
       transition:border-color .15s;line-height:1.5}
#input:focus{border-color:#3b5bdb}
#send{padding:10px 22px;background:#3b5bdb;color:#fff;border:none;border-radius:10px;
      font-size:.9rem;font-weight:600;cursor:pointer;transition:background .15s;
      white-space:nowrap;flex-shrink:0;height:44px}
#send:hover{background:#2f4ac0}
#send:disabled{background:#94a3b8;cursor:not-allowed}
</style>
</head>
<body>

<header>
  <div>
    <h1>🏙️ Boston Data Hub</h1>
    <span>Boston 311 Voice AI Platform · MCP-Connected · Equity-Aware</span>
  </div>
</header>

<div class="layout">
  <aside>
    <div class="sidebar-label">Agents</div>
    <div id="agent-list"></div>
  </aside>
  <main>
    <div id="messages"></div>
    <div class="input-bar">
      <span class="badge" id="badge"></span>
      <textarea id="input" placeholder="Ask a question about Boston civic data…" rows="1"></textarea>
      <button id="send">Send</button>
    </div>
  </main>
</div>

<script>
const AGENTS = AGENTS_JSON_PLACEHOLDER;
let activeAgent = "orchestrator";

// ── Sidebar ──────────────────────────────────────────────────────────────────
function renderSidebar() {
  const list = document.getElementById("agent-list");
  list.innerHTML = "";
  Object.entries(AGENTS).forEach(([key, a]) => {
    const el = document.createElement("div");
    el.className = "agent-card" + (key === activeAgent ? " active" : "");
    el.innerHTML =
      `<div class="emoji">${a.emoji}</div>` +
      `<div><div class="name">${a.name}</div><div class="desc">${a.description}</div></div>`;
    el.addEventListener("click", () => {
      activeAgent = key;
      renderSidebar();
      document.getElementById("badge").textContent = `${a.emoji} ${a.name}`;
      document.getElementById("input").placeholder = `Ask the ${a.name}…`;
    });
    list.appendChild(el);
  });
}
renderSidebar();
// Init badge
const init = AGENTS[activeAgent];
document.getElementById("badge").textContent = `${init.emoji} ${init.name}`;

// ── Helpers ──────────────────────────────────────────────────────────────────
const messages = document.getElementById("messages");
const inputEl  = document.getElementById("input");
const sendBtn  = document.getElementById("send");

function scrollBottom() { messages.scrollTop = messages.scrollHeight; }

function escHtml(s) {
  return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}

function addBubble(role, innerHtml, meta) {
  const wrap = document.createElement("div");
  wrap.className = "bubble " + role;
  if (meta) {
    const m = document.createElement("div");
    m.className = "meta"; m.textContent = meta;
    wrap.appendChild(m);
  }
  const body = document.createElement("div");
  body.className = "body";
  body.innerHTML = innerHtml;
  wrap.appendChild(body);
  messages.appendChild(wrap);
  scrollBottom();
  return body;
}

// ── Send ─────────────────────────────────────────────────────────────────────
function send() {
  const q = inputEl.value.trim();
  if (!q || sendBtn.disabled) return;
  inputEl.value = "";

  addBubble("user", escHtml(q));

  const agent = AGENTS[activeAgent];
  const agentBody = addBubble(
    "agent",
    '<div class="spinner"><div class="dot"></div><div class="dot"></div><div class="dot"></div></div>',
    `${agent.emoji} ${agent.name}`
  );

  sendBtn.disabled = true;
  inputEl.disabled = true;

  const logs = [];
  let hasResult = false;

  const url = "/stream?" + new URLSearchParams({ query: q, agent: activeAgent });
  const es = new EventSource(url);

  es.onmessage = (e) => {
    const msg = JSON.parse(e.data);
    if (msg.type === "log") {
      logs.push(msg.text);
    } else if (msg.type === "result") {
      hasResult = true;
      const md = marked.parse(msg.text);
      let logHtml = "";
      if (logs.length) {
        const lines = logs
          .map(l => {
            const cls = l.includes("🔧") ? "tool-call" : l.includes("✓") ? "ok" : "";
            return `<div class="log-line ${cls}">${escHtml(l)}</div>`;
          })
          .join("");
        logHtml = `<details class="tool-log">
          <summary>🔧 ${logs.length} tool call${logs.length > 1 ? "s" : ""} — expand to see</summary>
          <div class="log-wrap">${lines}</div>
        </details>`;
      }
      agentBody.innerHTML = md + logHtml;
      scrollBottom();
    } else if (msg.type === "error") {
      agentBody.innerHTML =
        `<span style="color:#dc2626">⚠️ ${escHtml(msg.text)}</span>`;
    } else if (msg.type === "done") {
      es.close();
      sendBtn.disabled = false;
      inputEl.disabled = false;
      inputEl.focus();
    }
  };

  es.onerror = () => {
    if (!hasResult) {
      agentBody.innerHTML =
        `<span style="color:#dc2626">⚠️ Connection error — is ANTHROPIC_API_KEY set?</span>`;
    }
    es.close();
    sendBtn.disabled = false;
    inputEl.disabled = false;
  };
}

sendBtn.addEventListener("click", send);
inputEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
});
</script>
</body>
</html>"""

# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    agents_json = json.dumps({
        k: {"name": v["name"], "emoji": v["emoji"], "description": v["description"]}
        for k, v in hub.AGENT_REGISTRY.items()
    })
    return HTML.replace("AGENTS_JSON_PLACEHOLDER", agents_json)


@app.route("/stream")
def stream():
    query     = request.args.get("query", "").strip()
    agent_key = request.args.get("agent", "orchestrator")
    if agent_key not in hub.AGENT_REGISTRY:
        agent_key = "orchestrator"
    if not query:
        return Response('data: {"type":"done"}\n\n', mimetype="text/event-stream")

    event_queue: "queue.Queue[dict | None]" = queue.Queue()

    def patched_print(*args, **kwargs):
        text = " ".join(str(a) for a in args)
        event_queue.put({"type": "log", "text": text})

    def worker():
        old = builtins.print
        builtins.print = patched_print
        try:
            result = hub.run_agent(query, agent_key, verbose=True)
            event_queue.put({"type": "result", "text": result})
        except Exception as exc:
            event_queue.put({"type": "error", "text": str(exc)})
        finally:
            builtins.print = old
            event_queue.put(None)

    threading.Thread(target=worker, daemon=True).start()

    def generate():
        while True:
            item = event_queue.get()
            if item is None:
                yield 'data: {"type":"done"}\n\n'
                break
            yield f"data: {json.dumps(item)}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


if __name__ == "__main__":
    print("\n🏙️  Boston Data Hub — Web UI")
    print("   Open: http://localhost:5000\n")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("⚠️  ANTHROPIC_API_KEY not set — set it before sending queries\n")
    app.run(host="0.0.0.0", port=5000, threaded=True, debug=False)
