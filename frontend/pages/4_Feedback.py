"""
Feedback Page
---------------
Shows the current user's recent like/dislike feedback, fetched from
GET /feedback-history. Adds a small like-vs-dislike count chart on top of
the raw list, giving an at-a-glance summary of how well suggestions have
been landing.
"""

import pandas as pd
import requests
import streamlit as st

from common import BASE_URL, auth_headers, friendly_network_error, inject_custom_css, page_header, render_sidebar_account, require_login

st.set_page_config(page_title="Feedback | Networking Assistant", page_icon=":material/forum:")
inject_custom_css()

require_login()
render_sidebar_account()

page_header("📊 Recent Feedback", "How your generated suggestions have been landing.")

feedback_entries = []
try:
    with st.spinner("Loading your feedback..."):
        feedback_response = requests.get(
            f"{BASE_URL}/feedback-history", headers=auth_headers(), timeout=15
        )
    if feedback_response.status_code == 401:
        st.error("Your session has expired. Please log out and log back in.")
    else:
        feedback_response.raise_for_status()
        feedback_entries = feedback_response.json()
except requests.RequestException as exc:
    st.error(friendly_network_error(exc))

if not feedback_entries:
    st.info("No feedback submitted yet. Rate a suggestion on the Home page to see it here.")
else:
    like_count = sum(1 for e in feedback_entries if e.get("action") == "like")
    dislike_count = sum(1 for e in feedback_entries if e.get("action") == "dislike")

    st.markdown("#### Like vs. dislike")
    chart_data = pd.DataFrame(
        {"count": [like_count, dislike_count]}, index=["👍 Like", "👎 Dislike"]
    )
    st.bar_chart(chart_data)

    st.markdown("#### Recent ratings")
    for entry in feedback_entries:
        icon = "👍" if entry.get("action") == "like" else "👎"
        with st.container(border=True):
            st.markdown(f"{icon} {entry.get('suggestion', '')}")
            st.caption(entry.get("created_at", ""))
