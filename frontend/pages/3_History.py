"""
History Page
--------------
Shows the current user's recent conversation history, fetched from the
backend (DB-backed, scoped to the logged-in user) via GET /history.
Surfaces the tone used and each suggestion's confidence score, matching
the extra fields the backend returns alongside the core generation data.

Each entry renders inside a collapsed st.expander rather than a long flat
list. With up to 5 entries, each carrying description/interests/themes/
suggestions/scores, a flat layout gets long fast -- expanders keep the
page scannable (skim the event + date, open the ones you actually want to
revisit) instead of forcing a scroll through everything every time.
"""

import requests
import streamlit as st

from common import BASE_URL, auth_headers, friendly_network_error, inject_custom_css, page_header, render_sidebar_account, require_login

st.set_page_config(page_title="History | Networking Assistant", page_icon=":material/history:")
inject_custom_css()

require_login()
render_sidebar_account()

page_header("🕘 Recent Conversation History", "Your 5 most recently generated conversations.")

history = []
try:
    with st.spinner("Loading your history..."):
        history_response = requests.get(f"{BASE_URL}/history", headers=auth_headers(), timeout=15)
    if history_response.status_code == 401:
        st.error("Your session has expired. Please log out and log back in.")
    else:
        history_response.raise_for_status()
        history = history_response.json()
except requests.RequestException as exc:
    st.error(friendly_network_error(exc))

if not history:
    st.info("No conversations generated yet. Head to Home to generate your first one.")
else:
    # Backend already returns most-recent-first.
    for entry in history:
        description = entry.get("description", "")
        created_at = entry.get("created_at", "")
        # Trim a long description so the collapsed expander label stays
        # on one line -- the full text is still shown inside once opened.
        label_description = description if len(description) <= 60 else description[:57] + "..."
        label = f"{label_description}"
        if created_at:
            label += f"  ·  {created_at}"

        with st.expander(label):
            st.markdown(f"**Event:** {description}")
            st.markdown(f"**Interests:** {', '.join(entry.get('interests', []))}")
            st.markdown(f"**Themes:** {', '.join(entry.get('themes', []))}")

            tone = entry.get("tone")
            if tone:
                st.markdown(f"**Tone:** {tone.capitalize()}")

            suggestions = entry.get("suggestions", [])
            scores = entry.get("confidence_scores", [])
            st.markdown("**Suggestions:**")
            for i, suggestion in enumerate(suggestions):
                if i < len(scores):
                    filled = "★" * scores[i]
                    empty = "☆" * (5 - scores[i])
                    st.markdown(f"- {suggestion} &nbsp; `{filled}{empty}`")
                else:
                    st.markdown(f"- {suggestion}")
