"""
Fact Check Page
------------------
Standalone Wikipedia lookup tool, independent of the generation flow on
the Home page. Wraps POST /fact-check, which itself wraps
app/services/fact_checker.py.

Note: app/services/fact_checker.py always returns HTTP 200 with a summary
string, even when the topic isn't found on Wikipedia -- it substitutes a
fixed fallback message ("Sorry, we couldn't find reliable information on
that topic right now.") rather than raising an error. This page checks for
that exact fallback string so a not-found result is shown as a neutral
message rather than a misleading green "success" box. This does couple the
two files on that string's exact wording; it's a small enough surface that
duplicating it here (versus importing the backend module into the
frontend, which runs as a separate container with its own dependencies)
is the more practical tradeoff.
"""

import requests
import streamlit as st

from common import BASE_URL, auth_headers, friendly_network_error, inject_custom_css, page_header, render_sidebar_account, require_login

st.set_page_config(page_title="Fact Check | Networking Assistant", page_icon=":material/fact_check:")
inject_custom_css()

require_login()
render_sidebar_account()

page_header(
    "🔍 Quick Fact Check",
    "Look up a topic on Wikipedia before bringing it up in conversation.",
)

# Kept in sync with app/services/fact_checker.py's FALLBACK_MESSAGE.
NOT_FOUND_MESSAGE = "Sorry, we couldn't find reliable information on that topic right now."

fact_query = st.text_input("Topic to verify", placeholder="e.g. blockchain in healthcare")

if st.button("Check Fact", type="primary", use_container_width=True):
    if not fact_query.strip():
        st.warning("Please enter a topic to check.")
    else:
        try:
            with st.spinner("Looking this up on Wikipedia..."):
                response = requests.post(
                    f"{BASE_URL}/fact-check",
                    json={"query": fact_query},
                    headers=auth_headers(),
                    timeout=15,
                )
            if response.status_code == 401:
                st.error("Your session has expired. Please log out and log back in.")
            elif response.status_code == 429:
                st.error("Too many fact-checks in a row. Please wait a moment and try again.")
            else:
                response.raise_for_status()
                summary = response.json()["summary"]
                if summary.strip() == NOT_FOUND_MESSAGE:
                    st.info(summary)
                else:
                    st.success(summary)
        except requests.RequestException as exc:
            st.error(friendly_network_error(exc))
        except (KeyError, ValueError):
            st.error("Received an unexpected response from the backend. Please try again.")
