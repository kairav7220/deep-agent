"""Job search agent — LangGraph, 4 nodes (search, filter, cover_letter, email)."""

import os, json, re, smtplib, ssl, requests
from typing import TypedDict
from email.message import EmailMessage
from dotenv import load_dotenv

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_mistralai import ChatMistralAI
from tavily import TavilyClient

load_dotenv()

tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
model = ChatMistralAI(model="mistral-small-latest", temperature=0.3)

SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")


class JobState(TypedDict):
    query: str
    skills: str
    experience: str
    work_mode: str
    salary: str
    recipient_email: str
    raw_jobs: list
    shortlisted: list
    cover_letters: str
    email_sent: bool


SITE_NAMES = r"naukri|shine|indeed|timesjobs|monster|builtin|careerbuilder|glassdoor|simplyhired|ziprecruiter"

def _filter_page(title: str, url: str) -> bool:
    if re.search(r"(salary\s+|skills\s+for|interview)", title, re.I):
        return True
    site_in_title = re.search(SITE_NAMES, title, re.I)
    site_in_url = re.search(SITE_NAMES, url, re.I)
    if re.search(r"(jobs?\s+(in|at|near|for)|vacanc|openings?\s+in)", title, re.I) and (site_in_title or site_in_url):
        return True
    if re.search(r"(/search/|/jobs-in-|/job-search)", url, re.I):
        return True
    if re.search(r"(instagram|facebook|twitter|x\.com|youtube|tiktok)", url, re.I):
        return True
    return False


def _serpapi_jobs(q: str) -> list:
    try:
        r = requests.get("https://serpapi.com/search", params={
            "engine": "google_jobs", "q": q, "api_key": SERPAPI_KEY
        }, timeout=15)
        data = r.json()
    except Exception:
        return []

    jobs = []
    for j in data.get("jobs_results", []):
        title = j.get("title", "")
        company = j.get("company_name", "")
        location = j.get("location", "")
        desc = j.get("description", "")[:1500]
        via = j.get("via", "")
        apply_links = [a.get("link", "") for a in j.get("apply_options", []) if a.get("link")]
        url = apply_links[0] if apply_links else ""
        if not url:
            continue
        display_title = f"{title} at {company}, {location}" if company else title
        jobs.append({"title": display_title, "description": desc, "url": url, "source": f"Google Jobs ({via})"})
    return jobs


def search_node(state: JobState) -> dict:
    terms = " ".join(state["skills"].split(",")[:3]) if state["skills"] else ""
    q = f"{state['query']} {terms}".strip()
    q_short = state["query"].strip()

    jobs, seen = [], set()

    tavily_resp = tavily.search(query=q, search_depth="advanced", max_results=10, include_raw_content=True)
    for r in tavily_resp.get("results", []):
        url = r.get("url", "")
        title = r.get("title", "")
        if url in seen:
            continue
        seen.add(url)
        if _filter_page(title, url):
            continue
        jobs.append({"title": title, "description": (r.get("content", "") or "")[:1500], "url": url, "source": "Tavily"})

    serpapi_results = _serpapi_jobs(q_short)
    for j in serpapi_results:
        if j["url"] not in seen:
            seen.add(j["url"])
            if _filter_page(j["title"], j["url"]):
                continue
            jobs.append(j)

    return {"raw_jobs": jobs}


def filter_node(state: JobState) -> dict:
    lines = []
    for i, j in enumerate(state["raw_jobs"]):
        lines.append(f"--- Job {i+1} ---\nTitle: {j['title']}\nURL: {j['url']}\n{j['description'][:600]}")
    jobs_text = "\n\n".join(lines)

    msg = model.invoke([
        SystemMessage(content="You are a job fitment analyst. Pick top 3 matching ALL criteria. REJECT: aggregator list pages, salary pages, personal LinkedIn profiles, wrong city. Only pick specific individual job postings from companies. Explain why each matches. Return ONLY valid JSON: [{\"title\": \"...\", \"url\": \"...\", \"reason\": \"...\"}]"),
        HumanMessage(content=f"Candidate:\n- Skills: {state['skills']}\n- Experience: {state['experience']}\n- Work mode: {state['work_mode']}\n- Salary: {state['salary']}\n- Location: {state['query']}\n\nJobs:\n{jobs_text}\n\nPick top 3 matching ALL criteria (especially location). REJECT profiles, list pages, salary pages. Return JSON."),
    ])

    raw = msg.content.strip()
    cleaned = raw.removeprefix("```json").removesuffix("```").strip()

    try:
        shortlisted = json.loads(cleaned)
    except json.JSONDecodeError:
        url_map = {j["url"]: j["title"] for j in state["raw_jobs"]}
        shortlisted = []
        for m in re.finditer(r'"url"\s*:\s*"([^"]+)"', raw):
            if m.group(1) in url_map:
                shortlisted.append({"title": url_map[m.group(1)], "url": m.group(1), "reason": ""})
        if not shortlisted:
            shortlisted = [{"title": j["title"], "url": j["url"], "reason": ""} for j in state["raw_jobs"][:3]]

    return {"shortlisted": shortlisted}


def cover_letter_node(state: JobState) -> dict:
    parts = []
    for j in state["shortlisted"]:
        parts.append(f"--- {j.get('title', 'Role')} ---\n{j.get('reason', '')}\nLink: {j.get('url', '#')}")
    jobs_text = "\n\n".join(parts)

    msg = model.invoke([
        SystemMessage(content="You write cover letters. Never use brackets or placeholders. Write the actual letter as if it will be sent immediately."),
        HumanMessage(content=f"Skills: {state['skills']}\nExperience: {state['experience']}\n\nJobs:\n{jobs_text}\n\nWrite one paragraph per job. No greetings/signoffs/addresses. Just the body paragraph. No brackets."),
    ])

    return {"cover_letters": msg.content}


def email_node(state: JobState) -> dict:
    to_address = state.get("recipient_email", "").strip()
    if not to_address:
        return {"email_sent": False}

    jobs_md = ""
    for j in state["shortlisted"]:
        url = j.get("url", "#")
        title = j.get("title", "?")
        reason = j.get("reason", "")
        jobs_md += f"\n## {title}\n🔗 {url}\n{reason}\n"

    body = f"Here are your shortlisted jobs and cover letters:\n\n{jobs_md}\n\n---\n\n{state['cover_letters']}"

    for port, use_ssl in [(587, False), (465, True)]:
        try:
            if use_ssl:
                ctx = ssl.create_default_context()
                with smtplib.SMTP_SSL(SMTP_SERVER, port, context=ctx) as server:
                    server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
                    msg = EmailMessage()
                    msg["Subject"] = f"Job Applications - {state['query']}"
                    msg["From"] = EMAIL_ADDRESS
                    msg["To"] = to_address
                    msg.set_content(body)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(SMTP_SERVER, port) as server:
                    server.starttls()
                    server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
                    msg = EmailMessage()
                    msg["Subject"] = f"Job Applications - {state['query']}"
                    msg["From"] = EMAIL_ADDRESS
                    msg["To"] = to_address
                    msg.set_content(body)
                    server.send_message(msg)
            print(f"Email sent to {to_address} via port {port}")
            return {"email_sent": True}
        except Exception as e:
            print(f"Port {port} failed: {e}")
            continue

    return {"email_sent": False}


def build_job_graph() -> StateGraph:
    g = StateGraph(JobState)
    g.add_node("search", search_node)
    g.add_node("filter", filter_node)
    g.add_node("cover_letter", cover_letter_node)
    g.add_node("email", email_node)
    g.set_entry_point("search")
    g.add_edge("search", "filter")
    g.add_edge("filter", "cover_letter")
    g.add_edge("cover_letter", "email")
    g.add_edge("email", END)
    return g.compile()


if __name__ == "__main__":
    agent = build_job_graph()
    r = agent.invoke({
        "query": "Data Analyst jobs in Gurgaon",
        "skills": "Python, SQL, PostgreSQL, TensorFlow, scikit-learn",
        "experience": "5 years",
        "work_mode": "Hybrid",
        "salary": "20 LPA",
        "recipient_email": "kumari174676@gmail.com",
        "raw_jobs": [],
        "shortlisted": [],
        "cover_letters": "",
        "email_sent": False,
    })

    print("\n=== SHORTLISTED ===\n")
    for j in r["shortlisted"]:
        print(f"  {j.get('title', '?')}\n  {j.get('url', 'no link')}\n  {j.get('reason', '')}\n")

    print("\n=== COVER LETTERS ===\n")
    print(r["cover_letters"])

    if r.get("email_sent"):
        print(f"\nEmail sent to {r['recipient_email']}")
    else:
        print("\nEmail not sent")
