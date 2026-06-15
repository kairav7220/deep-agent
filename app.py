"""Streamlit UI — research + job search."""

import streamlit as st
from research_agent import build_research_graph
from job_agent import build_job_graph

st.set_page_config(page_title="DeepAgent", page_icon=":zap:", layout="wide")
st.markdown("# :zap: DeepAgent")

tab1, tab2 = st.tabs([":microscope: Research Agent", ":briefcase: Job Search Agent"])

with tab1:
    col_q, col_e = st.columns([3, 1])
    with col_q:
        question = st.text_input("Research topic", placeholder="e.g. What is LangGraph?")
    with col_e:
        research_email = st.text_input("Email report to", placeholder="your@email.com")

    if st.button("Research", type="primary") and question:
        with st.status("Researching...", expanded=True) as status:
            agent = build_research_graph()
            result = agent.invoke({"question": question, "revision_count": 0, "recipient_email": research_email, "email_sent": False})
            status.update(label="Done!", state="complete", expanded=False)

        st.markdown("### Report")
        st.markdown(result["draft"])
        st.download_button("Download Report", data=result["draft"], file_name="research_report.md", mime="text/markdown")

        with st.expander("Critique & Revisions"):
            st.markdown(result.get("critique", "No critique"))

        if research_email and result.get("email_sent"):
            st.success(f":white_check_mark: Sent to {research_email}")
        elif research_email:
            st.error(":no_entry: Email failed — check server/credentials")

with tab2:
    col1, col2 = st.columns([3, 2])
    with col1:
        query = st.text_input("Role & Location", placeholder="e.g. Data Scientist in Bangalore")
        skills = st.text_area("Your Skills", placeholder="e.g. Python, SQL, TensorFlow", height=80)
    with col2:
        experience = st.text_input("Experience", placeholder="e.g. 4 years")
        salary = st.text_input("Salary", placeholder="e.g. 18-22 LPA")
        work_mode = st.selectbox("Work Mode", ["Any", "Remote", "Hybrid", "On-site"])
        recipient_email = st.text_input("Email results to", placeholder="your@email.com")

    if st.button("Find Jobs", type="primary") and query:
        with st.status("Working...", expanded=True) as status:
            agent = build_job_graph()
            result = agent.invoke({
                "query": query,
                "skills": skills or "Not specified",
                "experience": experience or "Not specified",
                "work_mode": work_mode,
                "salary": salary or "Not specified",
                "recipient_email": recipient_email,
                "raw_jobs": [],
                "shortlisted": [],
                "cover_letters": "",
                "email_sent": False,
            })
            status.update(label="Done!", state="complete", expanded=False)

        st.markdown("### Shortlisted")
        for j in result["shortlisted"]:
            with st.container(border=True):
                st.markdown(f"**{j.get('title', '?')}**")
                url = j.get("url", "")
                if url and url != "#":
                    st.markdown(f":link: [View Job]({url})")
                reason = j.get("reason", "")
                if reason:
                    st.caption(reason)

        st.markdown("### Cover Letters")
        st.markdown(result["cover_letters"])

        if result.get("email_sent"):
            st.success(f":white_check_mark: Sent to {recipient_email}")
        elif recipient_email:
            st.error(":no_entry: Email failed — check server/credentials")
