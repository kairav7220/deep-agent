"""Research agent — LangGraph, 4 nodes (research, draft, critique, email)."""

import os, json, smtplib
from typing import TypedDict, Annotated, Literal
from email.message import EmailMessage
from dotenv import load_dotenv

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_mistralai import ChatMistralAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from tavily import TavilyClient

load_dotenv()

tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.3)
critic_model = ChatMistralAI(model="mistral-small-latest", temperature=0.3)

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")


class ResearchState(TypedDict):
    question: str
    search_results: str
    draft: str
    critique: str
    revision_count: int
    sources: list
    recipient_email: str
    email_sent: bool


MAX_REVISIONS = 2


def research_node(state: ResearchState) -> dict:
    response = tavily.search(
        query=state["question"],
        search_depth="advanced",
        max_results=8,
        include_raw_content=True,
    )
    sources = []
    results = []
    for r in response.get("results", []):
        sources.append({"title": r.get("title", ""), "url": r.get("url", "")})
        results.append(r.get("content", ""))

    return {
        "search_results": "\n\n".join(results),
        "sources": sources,
    }


def draft_node(state: ResearchState) -> dict:
    sources_text = "\n".join(
        f"[{i+1}] {s['title']}: {s['url']}"
        for i, s in enumerate(state["sources"])
    )

    msg = critic_model.invoke([
        SystemMessage(content="""You are a research writer. Write a comprehensive report.
Structure: overview, key concepts, analysis, conclusion.
Use the search results as evidence. Cite sources as [1], [2] etc.
Write in clear markdown."""),
        HumanMessage(content=f"""Topic: {state['question']}

Research findings:
{state['search_results']}

Sources:
{sources_text}

Write the report."""),
    ])

    return {"draft": msg.content}


def critique_node(state: ResearchState) -> dict:
    msg = critic_model.invoke([
        SystemMessage(content="""You are an editor. Critique this report for:
1. Missing details or shallow sections
2. Clarity and structure
3. Evidence strength

Be specific. If it's good, say "APPROVED"."""),
        HumanMessage(content=f"""Original question: {state['question']}

Report:
{state['draft']}

Critique:"""),
    ])

    return {"critique": msg.content, "revision_count": state["revision_count"] + 1}


def should_continue(state: ResearchState) -> Literal["research", "draft", "email"]:
    if "APPROVED" in state["critique"].upper():
        return "email"
    if state["revision_count"] >= MAX_REVISIONS:
        return "email"
    return "research"


def email_node(state: ResearchState) -> dict:
    to_address = state.get("recipient_email", "").strip()
    if not to_address:
        return {"email_sent": False}

    sources_text = "\n".join(
        f"[{i+1}] {s['title']}: {s['url']}"
        for i, s in enumerate(state["sources"])
    )
    body = f"Research Report: {state['question']}\n\n{state['draft']}\n\nSources:\n{sources_text}"

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            msg = EmailMessage()
            msg["Subject"] = f"Research Report - {state['question']}"
            msg["From"] = EMAIL_ADDRESS
            msg["To"] = to_address
            msg.set_content(body)
            server.send_message(msg)
        return {"email_sent": True}
    except Exception as e:
        print(f"Email send failed: {e}")
        return {"email_sent": False}


def build_research_graph() -> StateGraph:
    graph = StateGraph(ResearchState)

    graph.add_node("research", research_node)
    graph.add_node("draft", draft_node)
    graph.add_node("critique", critique_node)
    graph.add_node("email", email_node)

    graph.set_entry_point("research")
    graph.add_edge("research", "draft")
    graph.add_edge("draft", "critique")
    graph.add_conditional_edges("critique", should_continue, {
        "research": "research",
        "draft": "draft",
        "email": "email",
    })
    graph.add_edge("email", END)

    return graph.compile()


if __name__ == "__main__":
    import sys

    question = " ".join(sys.argv[1:]) or "What is LangGraph?"
    print(f"Researching: {question}\n")

    agent = build_research_graph()
    result = agent.invoke({"question": question, "revision_count": 0})

    print(result["draft"])

    with open("final_report.md", "w", encoding="utf-8") as f:
        f.write(result["draft"])

    print("\n--- Saved to final_report.md ---")
