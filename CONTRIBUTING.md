# Contributing

## Setup

```bash
git clone https://github.com/kairav7220/deep-agent.git
cd deep-agent
python -m venv .venv
.venv\Scripts\activate    # Windows
pip install -r requirements.txt
```

## Development

- Fork the repo, create a feature branch.
- Test agents individually: `python research_agent.py "your topic"` or `python job_agent.py`
- Test full UI: `streamlit run app.py`
- Ensure `.env` is in `.gitignore` before committing.

## PR Guidelines

- One feature/fix per PR.
- If adding a new agent, follow the existing `TypedDict` + `StateGraph` pattern.
- Include a CLI usage example in the PR description.
- Update `requirements.txt` if adding dependencies.
