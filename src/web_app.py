"""Interactive FastAPI Web Application & Dashboard for Freight Tiger Assistant."""

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pathlib import Path
import pandas as pd
from typing import Optional

from src.assistant import ShippingCostAssistant
from src.config import DEFAULT_OUTPUT_PATH

app = FastAPI(title="Freight Tiger Smart Shipping Cost Assistant", version="1.0.0")

# Initialize assistant
assistant = ShippingCostAssistant()

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    """Serve a small icon so browsers do not log a missing favicon."""
    svg_icon = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
        <rect width="64" height="64" rx="12" fill="#F7931E"/>
        <path d="M12 20h27v7H12zm0 11h20v7H12zm0 11h27v7H12zM43 27h8l7 8v14H43z"
              fill="#fff"/>
    </svg>"""
    return Response(content=svg_icon, media_type="image/svg+xml")

@app.get("/api/results")
def get_results(all_weeks: bool = False):
    """Return analyzed results in JSON format."""
    df = assistant.analyze(include_all_weeks=all_weeks)
    return JSONResponse(content=df.to_dict(orient="records"))

@app.get("/api/ask")
def ask_question(q: str = Query(..., description="Plain-English question")):
    """Answer natural language questions about shipping costs."""
    answer = assistant.ask(q)
    return {
        "question": q,
        "answer": answer,
        "token_summary": assistant.tracker.summary()
    }

@app.get("/api/token-report")
def get_token_report():
    """Return token and cost audit log."""
    return assistant.tracker.summary()

@app.get("/", response_class=HTMLResponse)
def index():
    """Render interactive web dashboard."""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Freight Tiger | Smart Shipping Cost Assistant</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
        <style>
            :root {
                --primary: #F7931E;
                --primary-dark: #D47B0E;
                --secondary: #1F2937;
                --bg: #F9FAFB;
                --card-bg: #FFFFFF;
                --border: #E5E7EB;
                --text: #111827;
                --text-muted: #6B7280;
                --danger: #EF4444;
                --success: #10B981;
            }
            * { box-sizing: border-box; margin: 0; padding: 0; }
            body { font-family: 'Inter', sans-serif; background-color: var(--bg); color: var(--text); line-height: 1.5; padding: 24px; }
            .container { max-width: 1200px; margin: 0 auto; }
            header { display: flex; align-items: center; justify-content: space-between; padding-bottom: 20px; border-bottom: 2px solid var(--border); margin-bottom: 24px; }
            .logo-group { display: flex; align-items: center; gap: 12px; }
            .badge { background: #FEF3C7; color: #92400E; padding: 4px 10px; border-radius: 9999px; font-size: 12px; font-weight: 600; }
            .title { font-size: 24px; font-weight: 700; color: var(--secondary); }
            .subtitle { font-size: 14px; color: var(--text-muted); }
            
            .grid { display: grid; grid-template-columns: 2fr 1fr; gap: 24px; margin-bottom: 24px; }
            .card { background: var(--card-bg); border-radius: 12px; border: 1px solid var(--border); padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
            .card-title { font-size: 16px; font-weight: 600; margin-bottom: 16px; display: flex; align-items: center; justify-content: space-between; }
            
            /* Table */
            .table-container { overflow-x: auto; max-height: 520px; }
            table { width: 100%; border-collapse: collapse; font-size: 13px; text-align: left; }
            th { position: sticky; top: 0; background: #F3F4F6; padding: 10px 12px; font-weight: 600; border-bottom: 2px solid var(--border); color: #374151; }
            td { padding: 10px 12px; border-bottom: 1px solid var(--border); vertical-align: top; }
            tr:hover { background-color: #F9FAFB; }
            .tag { display: inline-block; padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: 600; }
            .tag-yes { background: #FEE2E2; color: #991B1B; }
            .tag-justified { background: #D1FAE5; color: #065F46; }
            .tag-normal { background: #E5E7EB; color: #374151; }
            
            /* Chat / Q&A Box */
            .chat-container { display: flex; flex-direction: column; height: 480px; }
            .chat-history { flex: 1; overflow-y: auto; padding: 12px; background: #F9FAFB; border-radius: 8px; border: 1px solid var(--border); margin-bottom: 12px; }
            .chat-msg { margin-bottom: 12px; padding: 10px 14px; border-radius: 8px; font-size: 13px; }
            .chat-user { background: #E0E7FF; color: #3730A3; align-self: flex-end; margin-left: 20px; }
            .chat-bot { background: #FFFFFF; border: 1px solid var(--border); color: var(--text); margin-right: 20px; }
            .chat-input-group { display: flex; gap: 8px; }
            input[type="text"] { flex: 1; padding: 10px 14px; border: 1px solid var(--border); border-radius: 8px; font-size: 14px; outline: none; }
            input[type="text"]:focus { border-color: var(--primary); ring: 2px solid #FED7AA; }
            button { background: var(--primary); color: white; border: none; padding: 10px 18px; border-radius: 8px; font-weight: 600; cursor: pointer; transition: background 0.2s; }
            button:hover { background: var(--primary-dark); }
            
            /* Metrics strip */
            .metrics-strip { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }
            .metric-box { background: var(--card-bg); border: 1px solid var(--border); border-radius: 10px; padding: 16px; }
            .metric-val { font-size: 22px; font-weight: 700; color: var(--secondary); }
            .metric-label { font-size: 12px; color: var(--text-muted); font-weight: 500; }
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <div class="logo-group">
                    <div>
                        <div class="title">Freight Tiger | Smart Cost Assistant</div>
                        <div class="subtitle">Autonomous Corridor Cost Tracking & RAG Grounded Reasoning</div>
                    </div>
                </div>
                <div>
                    <span class="badge">Evaluation & Demo Mode</span>
                </div>
            </header>

            <div class="metrics-strip" id="metricsStrip">
                <div class="metric-box">
                    <div class="metric-val" id="totalShipments">2,940</div>
                    <div class="metric-label">Shipment Records Ingested</div>
                </div>
                <div class="metric-box">
                    <div class="metric-val" id="totalRoutes">7</div>
                    <div class="metric-label">Monitored Corridors (Short/Med/Long)</div>
                </div>
                <div class="metric-box">
                    <div class="metric-val" id="totalFlagged">Loading...</div>
                    <div class="metric-label">Anomalies Detected (2024-2025)</div>
                </div>
                <div class="metric-box">
                    <div class="metric-val" id="llmCost">$0.0000</div>
                    <div class="metric-label">Token Run Cost (Open-Source Rate)</div>
                </div>
            </div>

            <div class="grid">
                <div class="card">
                    <div class="card-title">
                        <span>Corridor Anomalies & Verification Ledger</span>
                        <div>
                            <label style="font-size: 12px; font-weight: normal; margin-right: 8px;">
                                <input type="checkbox" id="showAllWeeksToggle" onchange="loadTable()"> Show All Weeks
                            </label>
                            <button onclick="loadTable()" style="padding: 4px 10px; font-size: 12px;">Refresh</button>
                        </div>
                    </div>
                    <div class="table-container">
                        <table>
                            <thead>
                                <tr>
                                    <th>Route</th>
                                    <th>Week Of</th>
                                    <th>₹ / Tonne-Km</th>
                                    <th>vs. History (8-Wk)</th>
                                    <th>vs. Peers</th>
                                    <th>Status</th>
                                    <th>Note</th>
                                    <th>Grounded Reason</th>
                                </tr>
                            </thead>
                            <tbody id="resultsBody">
                                <tr><td colspan="8" style="text-align: center;">Loading corridor metrics...</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>

                <div class="card">
                    <div class="card-title">
                        <span>Natural Language Assistant (Stretch Goal)</span>
                    </div>
                    <div class="chat-container">
                        <div class="chat-history" id="chatHistory">
                            <div class="chat-msg chat-bot">
                                Hello! I'm your Freight Tiger Shipping Cost Assistant. Ask me anything about our routes, cost rises, or context notes (e.g., <i>"Why did Chennai-Bangalore get pricier in March?"</i> or <i>"What happened on Delhi-Jaipur in Nov 2024?"</i>).
                            </div>
                        </div>
                        <div class="chat-input-group">
                            <input type="text" id="chatInput" placeholder="Ask a question about route costs..." onkeydown="if(event.key==='Enter') sendQuestion()">
                            <button onclick="sendQuestion()">Ask</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            async function loadTable() {
                const showAll = document.getElementById('showAllWeeksToggle').checked;
                const tbody = document.getElementById('resultsBody');
                tbody.innerHTML = '<tr><td colspan="8" style="text-align: center;">Analyzing shipments...</td></tr>';
                
                try {
                    const res = await fetch('/api/results?all_weeks=' + showAll);
                    const data = await res.json();
                    
                    document.getElementById('totalFlagged').innerText = data.filter(r => r.flagged !== 'No').length;
                    
                    tbody.innerHTML = '';
                    data.forEach(row => {
                        const tr = document.createElement('tr');
                        let tagClass = 'tag-normal';
                        if (row.flagged === 'Yes') tagClass = 'tag-yes';
                        else if (row.flagged.includes('justified')) tagClass = 'tag-justified';
                        
                        tr.innerHTML = `
                            <td><strong>${row.route}</strong></td>
                            <td>${row.week_of}</td>
                            <td>₹${row.cost_per_tonne_km}</td>
                            <td>${row.vs_own_history}</td>
                            <td>${row.vs_similar_routes}</td>
                            <td><span class="tag ${tagClass}">${row.flagged}</span></td>
                            <td>${row.matched_note_id || '-'}</td>
                            <td style="max-width: 300px; font-size: 12px;">${row.reason}</td>
                        `;
                        tbody.appendChild(tr);
                    });
                } catch(e) {
                    tbody.innerHTML = '<tr><td colspan="8" style="color: red; text-align: center;">Failed to load data</td></tr>';
                }
            }

            async function sendQuestion() {
                const input = document.getElementById('chatInput');
                const query = input.value.trim();
                if (!query) return;

                const history = document.getElementById('chatHistory');
                
                // Add user message
                const userMsg = document.createElement('div');
                userMsg.className = 'chat-msg chat-user';
                userMsg.innerText = query;
                history.appendChild(userMsg);
                input.value = '';
                history.scrollTop = history.scrollHeight;

                // Add loading bot message
                const botMsg = document.createElement('div');
                botMsg.className = 'chat-msg chat-bot';
                botMsg.innerText = 'Analyzing corridor history and notes...';
                history.appendChild(botMsg);
                history.scrollTop = history.scrollHeight;

                try {
                    const res = await fetch('/api/ask?q=' + encodeURIComponent(query));
                    const data = await res.json();
                    botMsg.innerText = data.answer;
                } catch(e) {
                    botMsg.innerText = 'Sorry, encountered an error processing your query.';
                }
                history.scrollTop = history.scrollHeight;
            }

            // Initial load
            loadTable();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)
