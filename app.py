# =====================================================================
# INTELSHIELD v3.0 — AGENTIC TEMPORAL INTELLIGENCE VALIDATION SYSTEM
# =====================================================================
# Safe for GitHub: API key loaded from environment variable only.
# Set GEMINI_API_KEY in your .env file or environment before running.
# =====================================================================

import os
import re
import time
import json
from datetime import datetime
from dotenv import load_dotenv
from google import genai
from google.genai import types

try:
    import gradio as gr
except ImportError:
    os.system('pip install -q gradio')
    import gradio as gr

# ── API KEY (safe — never hardcoded) ──
load_dotenv()

def load_api_key() -> str:
    # 1. Try Kaggle secrets vault (when running on Kaggle)
    try:
        from kaggle_secrets import UserSecretsClient
        return UserSecretsClient().get_secret("GEMINI_API_KEY")
    except Exception:
        pass
    # 2. Try environment variable (local / GitHub Codespaces / any server)
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        return key
    raise EnvironmentError(
        "❌ No GEMINI_API_KEY found.\n"
        "Create a .env file with: GEMINI_API_KEY=your_key_here\n"
        "Or set it as an environment variable before running."
    )

try:
    client = genai.Client(api_key=load_api_key())
    print("✅ Client initialized.")
except Exception as e:
    print(f"⚠️ Client init failed: {e}")

# ── TOOLS ──
def calculate_temporal_decay(text_snippet: str) -> str:
    """Evaluates historical timestamps for information degradation risk."""
    year_match = re.search(r'\b(19|20)\d{2}\b', text_snippet)
    current_date = datetime(2026, 6, 21)
    if not year_match:
        return json.dumps({"status": "UNCERTAIN", "days_elapsed": None, "risk_level": "UNKNOWN", "freshness_score": 50})
    extracted_year = int(year_match.group(0))
    delta_days = (current_date - datetime(extracted_year, 6, 1)).days
    if delta_days > 730:
        risk, score = "HIGH", max(0, 100 - delta_days // 10)
    elif delta_days > 365:
        risk, score = "MODERATE", max(20, 60 - delta_days // 15)
    else:
        risk, score = "LOW", max(60, 100 - delta_days // 5)
    return json.dumps({"status": f"DECAY STATUS: {risk} RISK", "days_elapsed": delta_days, "risk_level": risk, "freshness_score": score})

def verify_claim_tool(search_query: str) -> str:
    """Simulates live ground-truth resolution for stale claims."""
    query = search_query.lower()
    mock_web_index = {
        "pricing":   {"truth": "Competitor pricing updated to $25/month. Starter tier $15.", "source": "Company pricing page (June 2026)", "confidence": 92},
        "funding":   {"truth": "Company secured $80M Series C round.", "source": "TechCrunch (June 2026)", "confidence": 88},
        "feature x": {"truth": "Feature X development officially sunsetted per product changelog.", "source": "Official product blog (June 2026)", "confidence": 95},
    }
    for keyword, data in mock_web_index.items():
        if keyword in query:
            return json.dumps({"live_truth": data["truth"], "source": data["source"], "source_confidence": data["confidence"], "override": True})
    return json.dumps({"live_truth": "No definitive 2026 override found.", "source": "Public registry scan", "source_confidence": 30, "override": False})

project_tools = [calculate_temporal_decay, verify_claim_tool]

# ── SYSTEM PROMPTS ──
claim_extractor_prompt = """
You are a precision claim extraction engine.
Given a business intelligence report, extract EVERY sentence that contains:
- Specific years or dates
- Pricing or revenue figures
- Funding amounts or rounds
- Product roadmap items or feature timelines
- Market position or competitive claims

For EACH claim, call calculate_temporal_decay() with the claim text.

Then return a JSON array (and ONLY the JSON array, no other text) like:
[{"claim": "exact claim text", "category": "PRICING|FUNDING|PRODUCT|TIMELINE|MARKET", "year_referenced": 2024, "decay_result": "<result from tool>"}]
"""

verifier_prompt = """
You are a live intelligence verification officer.
You will receive a JSON array of extracted claims with their decay risk levels.
For every claim with risk_level HIGH or MODERATE, call verify_claim_tool() with a precise 2-3 word keyword query.
Then return ONLY a JSON array like:
[{"claim": "original claim text", "category": "PRICING|FUNDING|PRODUCT|TIMELINE|MARKET", "days_elapsed": 742, "risk_level": "HIGH", "freshness_score": 27, "live_truth": "verified truth or N/A if LOW risk", "source": "source name or N/A", "source_confidence": 92, "contradiction": true}]
"""

reporter_prompt = """
You are an executive intelligence reporting officer.
You receive a verified JSON array of claims with risk and live truth data.
Produce a complete audit report in this EXACT markdown format:

---

## 🔍 Claim-by-Claim Analysis

| # | Evaluated Claim | Category | Age Risk | Days Old | Freshness Score | Live Ground Truth (2026) | Source | Contradiction | Impact Rating |
|---|----------------|----------|----------|----------|-----------------|--------------------------|--------|---------------|---------------|
[fill rows]

---

## 📊 Reliability Metrics

**Composite Reliability Score: XX/100**

```
Freshness Weight  (40%): XX pts
Source Quality    (30%): XX pts
Verification      (30%): XX pts
─────────────────────────────────
Total                   : XX/100
```

Risk breakdown:
- 🔴 HIGH risk claims: N
- 🟡 MODERATE risk claims: N
- 🟢 LOW risk claims: N

---

## ⚡ Explainability Trace

For each HIGH/MODERATE claim show:
```
Claim → Year Detected → Age Computed → Risk Threshold Exceeded → Verification Triggered → Live Override Found → Contradiction Flagged
```

---

## 📋 Executive Summary

Write 3-5 sentences for a business leader summarising findings and recommended action.

---

**Report Accuracy Score: XX%**
"""

# ── FALLBACK ENGINE ──
FALLBACK_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-2.5-flash-lite",
]

def call_model(model, contents, system_instruction, tools=None, temperature=0.1, max_retries=3):
    for attempt in range(max_retries):
        try:
            global client
            if 'client' not in globals():
                client = genai.Client(api_key=load_api_key())
            config_kwargs = dict(system_instruction=system_instruction, temperature=temperature)
            if tools:
                config_kwargs["tools"] = tools
            chat = client.chats.create(model=model, config=types.GenerateContentConfig(**config_kwargs))
            return chat.send_message(contents).text
        except Exception as e:
            err = str(e).lower()
            if any(c in err for c in ["503", "429", "unavailable", "exhausted", "quota"]) and attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            raise e

def try_models(contents, system_instruction, tools=None, temperature=0.1):
    last_error = None
    for model in FALLBACK_MODELS:
        try:
            result = call_model(model, contents, system_instruction, tools, temperature)
            return result
        except Exception as e:
            err = str(e).lower()
            if any(c in err for c in ["429", "quota", "rate", "exhausted"]):
                return "⏳ **Rate limit hit.** Wait 60 seconds and try again."
            last_error = e
            continue
    return f"❌ **All models exhausted.**\n\n`{str(last_error)}`"

def ui_audit_interface(input_report_text: str) -> str:
    if not input_report_text.strip():
        return "⚠️ **Input empty.** Paste a report and click Execute."
    raw_claims = try_models(f"Report to audit:\n{input_report_text}", claim_extractor_prompt, project_tools, 0.0)
    if raw_claims.startswith("⏳") or raw_claims.startswith("❌"):
        return raw_claims
    verified = try_models(f"Claims to verify:\n{raw_claims}", verifier_prompt, project_tools, 0.0)
    if verified.startswith("⏳") or verified.startswith("❌"):
        return verified
    report = try_models(f"Verified claims data:\n{verified}", reporter_prompt, None, 0.2)
    return report

# ── SHADER BACKGROUND ──
SHADER_HTML = """
<canvas id="glCanvas" style="position:fixed;top:0;left:0;width:100vw;height:100vh;z-index:0;pointer-events:none;"></canvas>
<script>
(function(){
    const canvas=document.getElementById('glCanvas');
    const gl=canvas.getContext('webgl')||canvas.getContext('experimental-webgl');
    if(!gl){canvas.style.background='#000';return;}
    const vert=`attribute vec2 a_pos;void main(){gl_Position=vec4(a_pos,0,1);}`;
    const frag=`precision highp float;uniform float u_time;uniform vec2 u_res;uniform vec2 u_mouse;
        float blob(vec2 uv,vec2 c,float r,float s){float d=length(uv-c);return exp(-d*d/(2.0*r*r*s));}
        void main(){vec2 uv=gl_FragCoord.xy/u_res;float asp=u_res.x/u_res.y;vec2 auv=vec2(uv.x*asp,uv.y);
        float t=u_time*0.28;float g=0.0;
        g+=blob(auv,vec2((0.15+0.35*sin(t*0.7))*asp,0.20+0.55*cos(t*0.5)),0.28,1.8)*0.90;
        g+=blob(auv,vec2((0.55+0.38*cos(t*0.6+2.1))*asp,0.65+0.28*sin(t*0.8+0.5)),0.22,2.0)*0.80;
        g+=blob(auv,vec2((0.80+0.18*sin(t*0.9+3.3))*asp,0.35+0.40*cos(t*0.55+1.8)),0.18,1.6)*0.75;
        g+=blob(auv,vec2((0.40+0.30*cos(t*0.45+4.2))*asp,0.80+0.18*sin(t*0.75+2.7)),0.24,1.9)*0.70;
        g+=blob(auv,vec2((0.25+0.20*sin(t*1.1+5.0))*asp,0.50+0.35*cos(t*0.65+3.9)),0.15,1.7)*0.65;
        g+=blob(auv,vec2(u_mouse.x*asp,u_mouse.y),0.32,2.2)*1.10;
        vec3 col=vec3(0.0);
        col+=vec3(0.45,0.01,0.01)*smoothstep(0.0,0.4,g);
        col+=vec3(0.75,0.04,0.02)*smoothstep(0.3,0.7,g);
        col+=vec3(1.00,0.12,0.04)*smoothstep(0.6,1.0,g);
        col+=vec3(1.00,0.55,0.35)*smoothstep(0.85,1.2,g);
        vec2 vig=uv*(1.0-uv);col*=pow(vig.x*vig.y*16.0,0.4);
        col=clamp(col*0.7,0.0,1.0);gl_FragColor=vec4(col,1.0);}`;
    function sh(type,src){const s=gl.createShader(type);gl.shaderSource(s,src);gl.compileShader(s);return s;}
    const prog=gl.createProgram();gl.attachShader(prog,sh(gl.VERTEX_SHADER,vert));gl.attachShader(prog,sh(gl.FRAGMENT_SHADER,frag));gl.linkProgram(prog);gl.useProgram(prog);
    const buf=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buf);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,1,-1,-1,1,1,1]),gl.STATIC_DRAW);
    const aPos=gl.getAttribLocation(prog,'a_pos');gl.enableVertexAttribArray(aPos);gl.vertexAttribPointer(aPos,2,gl.FLOAT,false,0,0);
    const uT=gl.getUniformLocation(prog,'u_time'),uR=gl.getUniformLocation(prog,'u_res'),uM=gl.getUniformLocation(prog,'u_mouse');
    function resize(){canvas.width=window.innerWidth;canvas.height=window.innerHeight;gl.viewport(0,0,canvas.width,canvas.height);}
    window.addEventListener('resize',resize);resize();
    let tx=0.5,ty=0.5,sx=0.5,sy=0.5;
    window.addEventListener('mousemove',e=>{tx=e.clientX/window.innerWidth;ty=1-(e.clientY/window.innerHeight);});
    let t0=null;
    function frame(ts){if(!t0)t0=ts;const t=(ts-t0)*0.001;sx+=(tx-sx)*0.04;sy+=(ty-sy)*0.04;
        gl.uniform1f(uT,t);gl.uniform2f(uR,canvas.width,canvas.height);gl.uniform2f(uM,sx,sy);
        gl.drawArrays(gl.TRIANGLE_STRIP,0,4);requestAnimationFrame(frame);}
    requestAnimationFrame(frame);
})();
</script>
"""

custom_css = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');
:root{--surface:rgba(6,0,0,0.82);--border:rgba(160,20,20,0.30);--border-hot:rgba(220,38,38,0.50);--red:#dc2626;--red-bright:#ef4444;--red-glow:rgba(220,38,38,0.18);--text:#f0f0f0;--text-dim:#aaaaaa;--text-muted:#4a4a4a;--mono:'JetBrains Mono',monospace;--sans:'Inter',system-ui,sans-serif;}
body,.main{background:#000!important;}
.gradio-container{background:transparent!important;font-family:var(--sans)!important;max-width:1320px!important;margin:0 auto!important;position:relative!important;z-index:10!important;}
footer{display:none!important;}
.sidebar{background:var(--surface)!important;border:1px solid var(--border-hot)!important;border-radius:8px!important;padding:22px!important;backdrop-filter:blur(20px) saturate(1.4)!important;-webkit-backdrop-filter:blur(20px) saturate(1.4)!important;box-shadow:0 0 0 1px rgba(220,38,38,0.08),0 8px 32px rgba(0,0,0,0.6)!important;}
.output-panel{background:var(--surface)!important;border:1px solid var(--border-hot)!important;border-radius:8px!important;padding:26px!important;min-height:500px!important;backdrop-filter:blur(20px) saturate(1.4)!important;-webkit-backdrop-filter:blur(20px) saturate(1.4)!important;box-shadow:0 0 0 1px rgba(220,38,38,0.08),0 8px 32px rgba(0,0,0,0.6)!important;}
.gr-textbox,textarea{background:rgba(8,0,0,0.80)!important;border:1px solid var(--border)!important;border-radius:5px!important;color:var(--text)!important;font-family:var(--mono)!important;font-size:12.5px!important;line-height:1.75!important;}
textarea:focus{border-color:var(--red)!important;box-shadow:0 0 0 3px var(--red-glow),0 0 20px var(--red-glow)!important;outline:none!important;}
label span{color:var(--text-muted)!important;font-size:11px!important;}
.run-btn{background:var(--red)!important;border:1px solid rgba(239,68,68,0.6)!important;border-radius:5px!important;color:#fff!important;font-family:var(--mono)!important;font-weight:700!important;font-size:12px!important;letter-spacing:0.08em!important;text-transform:uppercase!important;box-shadow:0 0 24px rgba(220,38,38,0.45)!important;transition:all 0.15s ease!important;}
.run-btn:hover{background:var(--red-bright)!important;box-shadow:0 0 48px rgba(239,68,68,0.7)!important;transform:translateY(-2px)!important;}
.gr-markdown,.gr-markdown p{color:var(--text)!important;font-family:var(--sans)!important;font-size:13.5px!important;line-height:1.85!important;}
.gr-markdown h1,.gr-markdown h2,.gr-markdown h3{color:var(--red-bright)!important;font-weight:700!important;}
.gr-markdown strong{color:var(--red-bright)!important;}
.gr-markdown em{color:var(--text-dim)!important;}
.gr-markdown code{background:rgba(80,0,0,0.55)!important;color:var(--red-bright)!important;font-family:var(--mono)!important;font-size:11.5px!important;padding:2px 7px!important;border-radius:3px!important;border:1px solid var(--border)!important;}
.gr-markdown pre{background:rgba(10,0,0,0.8)!important;border:1px solid var(--border-hot)!important;border-radius:5px!important;padding:14px!important;}
.gr-markdown pre code{background:transparent!important;border:none!important;color:#e8e8e8!important;font-size:12px!important;}
.gr-markdown table{width:100%!important;border-collapse:collapse!important;font-size:12px!important;margin:18px 0!important;border:1px solid var(--border-hot)!important;}
.gr-markdown th{background:rgba(100,0,0,0.55)!important;color:var(--red-bright)!important;font-family:var(--mono)!important;font-size:10px!important;font-weight:600!important;text-transform:uppercase!important;letter-spacing:0.1em!important;padding:10px 12px!important;border:1px solid var(--border-hot)!important;}
.gr-markdown td{padding:9px 12px!important;border:1px solid rgba(100,0,0,0.25)!important;color:var(--text-dim)!important;vertical-align:top!important;}
.gr-markdown tr:nth-child(even) td{background:rgba(25,0,0,0.40)!important;}
.gr-markdown tr:hover td{background:rgba(60,0,0,0.50)!important;color:var(--text)!important;}
.gr-markdown hr{border:none!important;border-top:1px solid rgba(180,20,20,0.3)!important;margin:20px 0!important;}
.gr-accordion{background:rgba(10,0,0,0.65)!important;border:1px solid var(--border)!important;border-radius:5px!important;}
.gr-block,.gr-form{background:transparent!important;border:none!important;}
@keyframes blink{0%,100%{opacity:1;}50%{opacity:0.25;}}
"""

header_html = """
<div style="padding:44px 0 30px;border-bottom:1px solid rgba(180,20,20,0.35);margin-bottom:28px;position:relative;">
    <div style="position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent 0%,#991b1b 30%,#ef4444 50%,#991b1b 70%,transparent 100%);box-shadow:0 0 16px rgba(220,38,38,0.6);"></div>
    <div style="font-family:'JetBrains Mono',monospace;font-size:9px;letter-spacing:0.32em;color:rgba(127,29,29,0.9);text-transform:uppercase;margin-bottom:16px;">
        ██ CLASSIFIED · INTELSHIELD v3.0 · AGENTIC THREAT ANALYSIS SYSTEM
    </div>
    <h1 style="font-size:36px;font-weight:800;margin:0 0 8px;letter-spacing:-0.035em;line-height:1.1;color:#f0f0f0;text-shadow:0 0 40px rgba(220,38,38,0.4),0 0 80px rgba(220,38,38,0.15);">
        🛡️ INTEL<span style="color:#dc2626;text-shadow:0 0 30px rgba(220,38,38,0.8);">SHIELD</span>
    </h1>
    <p style="font-size:12.5px;color:rgba(100,100,100,0.9);margin:12px 0 0;line-height:1.6;max-width:640px;font-family:'JetBrains Mono',monospace;">
        // Real-time claim extraction · Temporal decay scoring · Live verification · Confidence scoring · Executive summary
    </p>
</div>
"""

status_html = """
<div style="display:flex;gap:0;margin-bottom:26px;border:1px solid rgba(180,20,20,0.45);border-radius:5px;overflow:hidden;backdrop-filter:blur(10px);">
    <div style="padding:11px 20px;background:rgba(100,0,0,0.45);font-family:'JetBrains Mono',monospace;font-size:10px;color:#ef4444;display:flex;align-items:center;gap:9px;border-right:1px solid rgba(180,20,20,0.35);">
        <span style="width:7px;height:7px;border-radius:50%;background:#ef4444;display:inline-block;box-shadow:0 0 10px #ef4444;animation:blink 1.6s ease-in-out infinite;"></span>SYS: ARMED
    </div>
    <div style="padding:11px 16px;font-family:'JetBrains Mono',monospace;font-size:10px;color:#3a3a3a;border-right:1px solid rgba(40,0,0,0.5);">◆ EXTRACTOR</div>
    <div style="padding:11px 16px;font-family:'JetBrains Mono',monospace;font-size:10px;color:#3a3a3a;border-right:1px solid rgba(40,0,0,0.5);">◆ DECAY SCANNER</div>
    <div style="padding:11px 16px;font-family:'JetBrains Mono',monospace;font-size:10px;color:#3a3a3a;border-right:1px solid rgba(40,0,0,0.5);">◆ VERIFIER</div>
    <div style="padding:11px 16px;font-family:'JetBrains Mono',monospace;font-size:10px;color:#3a3a3a;border-right:1px solid rgba(40,0,0,0.5);">◆ SCORER</div>
    <div style="padding:11px 16px;font-family:'JetBrains Mono',monospace;font-size:10px;color:#3a3a3a;">◆ EXEC REPORTER</div>
</div>
"""

sample_report = """
Our top industry competitor is growing rapidly. According to their corporate public
relations filings released back in 2024, their standard software platform pricing
is locked at a flat rate of $10/month. Furthermore, their executive roadmap lists
that they plan to launch an automated multi-agent Feature X framework very soon.
Financially, they remain highly stable after securing a $15M Series B funding round.
"""

with gr.Blocks(css=custom_css, title="IntelShield v3.0") as demo:
    gr.HTML(SHADER_HTML)
    gr.HTML(header_html)
    gr.HTML(status_html)
    with gr.Row(equal_height=True):
        with gr.Column(scale=4, elem_classes="sidebar"):
            gr.HTML("""<div style="font-family:'JetBrains Mono',monospace;font-size:9px;letter-spacing:0.22em;color:rgba(160,20,20,0.8);text-transform:uppercase;margin-bottom:14px;padding-bottom:10px;border-bottom:1px solid rgba(60,0,0,0.5);">▌ INTELLIGENCE PAYLOAD INPUT</div>""")
            input_box = gr.Textbox(label="", show_label=False, lines=14, placeholder="// Paste competitor report, market brief, or any business intelligence document...", value=sample_report.strip())
            gr.HTML('<div style="margin:14px 0;"></div>')
            audit_btn = gr.Button("⚡  EXECUTE THREAT ANALYSIS", variant="primary", elem_classes="run-btn")
            gr.HTML("""<div style="margin-top:14px;font-size:10px;color:rgba(40,0,0,0.9);font-family:'JetBrains Mono',monospace;line-height:1.9;border-top:1px solid rgba(50,0,0,0.5);padding-top:12px;">// STAGE A: EXTRACT → STAGE B: VERIFY → STAGE C: SCORE + REPORT</div>""")
            with gr.Accordion("▌ Pipeline Architecture", open=False):
                gr.Markdown("""
**Stage A** — `EXTRACT` · Auto-detect all time-sensitive claims

**Stage B** — `VERIFY` · Live ground-truth resolution per claim

**Stage C** — `SCORE` · Composite reliability score (0–100)

**Output** — Full table · Explainability trace · Executive summary

**Resilience** — Auto-cascade across 4 Gemini models
                """)
        with gr.Column(scale=8, elem_classes="output-panel"):
            gr.HTML("""<div style="font-family:'JetBrains Mono',monospace;font-size:9px;letter-spacing:0.22em;color:rgba(160,20,20,0.8);text-transform:uppercase;margin-bottom:18px;padding-bottom:10px;border-bottom:1px solid rgba(60,0,0,0.5);">▌ AUDIT INTELLIGENCE DASHBOARD</div>""")
            output_markdown = gr.Markdown(value="_// System armed. Awaiting payload..._\n\nPaste a report and click **⚡ EXECUTE THREAT ANALYSIS**.")
    audit_btn.click(fn=ui_audit_interface, inputs=input_box, outputs=output_markdown)

if __name__ == "__main__":
    demo.launch(share=False)
