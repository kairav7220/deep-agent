<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&height=200&section=header&text=DeepAgent&fontSize=50&fontAlignY=35&desc=Multi-agent%20AI%20Toolkit%20%E2%80%94%20Research%20%2B%20Job%20Search&descAlignY=55" />
</p>

<p align="center">
  <a href="https://deep-agent-pwjbnjxvu8wbvn8etxdgfz.streamlit.app/" target="_blank">
    <img src="https://img.shields.io/badge/Live_Demo-Streamlit-FF4B4B?logo=streamlit&logoColor=white" alt="Live Demo"/>
  </a>
</p>

<p align="center">
  <a href="#features">Features</a> ·
  <a href="#architecture">Architecture</a> ·
  <a href="#quick-start">Quick Start</a> ·
  <a href="#usage">Usage</a> ·
  <a href="#project-structure">Structure</a> ·
  <a href="#comparison">Comparison</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11-blue?logo=python&logoColor=white" alt="Python 3.11"/>
  <img src="https://img.shields.io/badge/LangGraph-Agentic-blueviolet" alt="LangGraph"/>
  <img src="https://img.shields.io/badge/Tavily-Search-orange" alt="Tavily"/>
  <img src="https://img.shields.io/badge/SerpAPI-Jobs-green" alt="SerpAPI"/>
  <img src="https://img.shields.io/badge/Gemini%202.5%20Flash-LLM-yellow" alt="Gemini 2.5 Flash"/>
  <img src="https://img.shields.io/badge/Mistral-LLM-blue" alt="Mistral"/>
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License"/>
</p>

---

Two autonomous LangGraph agents — one for research, one for job search. Both can email results.

## Features

- **Research Agent** — Tavily web search → draft report → AI critique → revision loop → email
- **Job Search Agent** — Tavily + SerpAPI job search → AI shortlist → cover letters → email
- **Revision Loop** — Research agent critiques its own draft and re-researches up to 2 times
- **Dual Search** — Job agent queries Tavily (web) + SerpAPI (Google Jobs) simultaneously
- **Smart Filtering** — Regex-based noise removal (aggregators, social media, salary pages)
- **Email Delivery** — Both agents send results via SMTP (Gmail)

## Architecture

```mermaid
flowchart LR
  UI["Streamlit UI"] --> Research["Research Agent"]
  UI --> Job["Job Search Agent"]
  
  subgraph Research["Research Agent"]
    R1["Research Node<br/>(Tavily search)"] --> R2["Draft Node<br/>(Gemini 2.5 Flash)"]
    R2 --> R3["Critique Node<br/>(Mistral)"]
    R3 -->|"APPROVED?"| R4["Email Node"]
    R3 -->|"Revise"| R1
  end
  
  subgraph Job["Job Search Agent"]
    J1["Search Node<br/>(Tavily + SerpAPI)"]
    J1 --> J2["Filter Node<br/>(Mistral)"]
    J2 --> J3["Cover Letter Node<br/>(Mistral)"]
    J3 --> J4["Email Node"]
  end
```

| Component | Research Agent | Job Search Agent |
|---|---|---|
| **Search** | Tavily | Tavily + SerpAPI (Google Jobs) |
| **Generator** | Gemini 2.5 Flash | Mistral Small |
| **Critic** | Mistral Small | — |
| **Loop** | Up to 2 revisions (conditional) | Linear |
| **Output** | Markdown report + email | Shortlist + cover letters + email |

## Quick Start

```bash
git clone https://github.com/kairav7220/deep-agent.git
cd deep-agent
pip install -r requirements.txt
```

Set your API keys in `.env`:

```env
TAVILY_API_KEY="tvly-..."
SERPAPI_KEY="..."
GOOGLE_API_KEY="AIza..."
MISTRAL_API_KEY="..."
EMAIL_ADDRESS="your@gmail.com"
EMAIL_PASSWORD="app-password"
```

```bash
streamlit run app.py
```

## Usage

```bash
streamlit run app.py   # Launch UI
python research_agent.py "What is LangGraph?"  # CLI mode
python job_agent.py                            # CLI mode
```

## Comparison

| Feature | DeepAgent | Basic LangGraph Agent | Manual Research |
|---|---|---|---|
| Agents | 2 (research + job) | 1 | — |
| Search Sources | Tavily + SerpAPI | Single | Manual |
| Self-Critique Loop | ✅ Up to 2 revisions | ❌ | — |
| Email Reports | ✅ SMTP | ❌ | — |
| Cover Letters | ✅ AI-generated | ❌ | — |
| Smart Job Filtering | ✅ Regex + LLM | ❌ | — |
| UI | ✅ Streamlit | ❌ CLI only | — |

## Project Structure

```
deep-agent/
├── app.py               # Streamlit UI (research + job tabs)
├── research_agent.py    # LangGraph research agent (4 nodes + revision loop)
├── job_agent.py         # LangGraph job search agent (4 nodes)
├── requirements.txt     # Python dependencies
├── CONTRIBUTING.md      # Contribution guide
├── llms.txt             # AI assistant context
├── .gitignore
└── LICENSE              # MIT
```

## License

MIT © [kairav7220](https://github.com/kairav7220)

---

<p align="center">
  Built with <a href="https://langchain-ai.github.io/langgraph">LangGraph</a> ·
  <a href="https://tavily.com">Tavily</a> ·
  <a href="https://serpapi.com">SerpAPI</a> ·
  <a href="https://ai.google.dev/gemini-api">Gemini</a> ·
  <a href="https://mistral.ai">Mistral</a>
</p>
