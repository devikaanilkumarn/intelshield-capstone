#  IntelShield v3.0
### Agentic Temporal Intelligence Validation System

> *Detects temporal data decay in business intelligence reports and cross-checks claims against live ground-truth sources — automatically.*

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Gradio](https://img.shields.io/badge/Gradio-4.0+-orange)
![Gemini](https://img.shields.io/badge/Gemini-2.5_Flash-green)
![License](https://img.shields.io/badge/License-MIT-red)

---

##  What It Does

Most business intelligence reports go stale within months. IntelShield is a **3-stage agentic pipeline** that:

1. **Extracts** every time-sensitive claim from any report (pricing, funding, product timelines, dates)
2. **Scores** each claim's temporal decay using a mathematical freshness model
3. **Verifies** stale claims against live 2026 ground-truth sources
4. **Outputs** a full audit dashboard with confidence scoring, explainability traces, and an executive summary

---

##  Architecture

```
Input Report
      ↓
┌─────────────────┐
│ Stage A:        │  → calculate_temporal_decay() tool
│ Claim Extractor │  → Identifies year, category, decay risk
└────────┬────────┘
         ↓
┌─────────────────┐
│ Stage B:        │  → verify_claim_tool() tool
│ Live Verifier   │  → Pulls 2026 ground-truth overrides
└────────┬────────┘
         ↓
┌─────────────────┐
│ Stage C:        │  → Composite score: freshness(40%) + source(30%) + verification(30%)
│ Scorer/Reporter │  → Claim table · Explainability trace · Executive summary
└─────────────────┘
```

---

##  Features

| Feature | Description |
|---------|-------------|
|  Auto Claim Extraction | Detects pricing, funding, product, timeline claims automatically |
|  Temporal Decay Scoring | Computes freshness score (0–100) based on days elapsed |
|  Live Verification | Cross-checks stale claims against ground-truth sources |
|  Composite Reliability Score | Weighted formula: freshness + source quality + verification |
|  Explainability Trace | Full reasoning chain visible for every finding |
|  Executive Summary | Plain-English summary for business leaders |
|  WebGL Shader UI | Mouse-reactive red glow blob background (GPU-rendered) |
|  Model Fallback | Auto-cascades across 4 Gemini models on failure |

---

##  Quick Start

### 1. Clone
```bash
git clone https://github.com/YOUR_USERNAME/intelshield-capstone.git
cd intelshield-capstone
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Set your API key
```bash
cp .env.example .env
# Edit .env and add your Gemini API key from aistudio.google.com
```

### 4. Run
```bash
python app.py
```

---

##  Getting a Gemini API Key

1. Go to [aistudio.google.com](https://aistudio.google.com)
2. Click **Get API Key** → **Create API Key**
3. Copy the key (starts with `AIzaSy...`)
4. Paste it into your `.env` file

---

##  Tech Stack

- **LLM:** Google Gemini 2.5 Flash (via `google-genai` SDK)
- **UI:** Gradio 4.x with custom WebGL shader background
- **Agentic pattern:** Multi-stage chained prompting with function calling
- **Resilience:** Exponential backoff + 4-model fallback cascade

---

##  Project Structure

```
intelshield-capstone/
│
├── app.py              # Main application (single-file)
├── requirements.txt    # Python dependencies
├── README.md           # This file
├── .env.example        # Environment variable template
├── .gitignore          # Excludes .env and secrets
└── screenshots/        # UI screenshots for documentation
```

---

##  Screenshots

*Add screenshots of the running UI here*

---

##  License

MIT License — free to use, modify, and distribute.

---

*Built for the Google Gen AI Intensive Capstone · June 2026*
