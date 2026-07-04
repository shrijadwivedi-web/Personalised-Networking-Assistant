"""
Profile Page
--------------
Lets a logged-in user set the role/industry/networking-goal fields that
personalize generated conversation starters (see app/services/
topic_generator.py, which folds these into the prompt sent to the hosted
conversation-generation model when present).

This is a one-time-ish setup form: it loads the user's current profile
from GET /profile on page load, pre-fills the form with whatever's already
saved, and PUTs only the changed values back on submit.
"""

import requests
import streamlit as st

from common import (
    BASE_URL,
    auth_headers,
    friendly_network_error,
    inject_custom_css,
    page_header,
    render_sidebar_account,
    require_login,
)

st.set_page_config(page_title="Profile | Networking Assistant", page_icon=":material/person:")
inject_custom_css()

require_login()
render_sidebar_account()

page_header(
    "👤 Your Profile",
    "This information is optional, but the more you fill in, the more "
    "tailored your generated conversation starters will be.",
)

# Load current profile values once per page visit so the form starts
# pre-filled rather than empty every time the user comes back to this page.
current_profile = {}
try:
    with st.spinner("Loading your profile..."):
        profile_response = requests.get(f"{BASE_URL}/profile", headers=auth_headers(), timeout=15)
    if profile_response.status_code == 401:
        st.error("Your session has expired. Please log out and log back in.")
    else:
        profile_response.raise_for_status()
        current_profile = profile_response.json()
except requests.RequestException as exc:
    st.error(friendly_network_error(exc))

with st.form("profile_form"):
    role = st.text_input(
        "Your role",
        value=current_profile.get("role") or "",
        placeholder="e.g. Backend developer",
    )
    industry = st.text_input(
        "Your industry",
        value=current_profile.get("industry") or "",
        placeholder="e.g. Fintech",
    )
    networking_goal = st.text_area(
        "What are you hoping to get out of networking right now?",
        value=current_profile.get("networking_goal") or "",
        placeholder="e.g. Looking to meet potential co-founders and early hires",
    )
    submitted = st.form_submit_button("Save Profile", type="primary", use_container_width=True)

if submitted:
    try:
        with st.spinner("Saving your profile..."):
            response = requests.put(
                f"{BASE_URL}/profile",
                json={"role": role, "industry": industry, "networking_goal": networking_goal},
                headers=auth_headers(),
                timeout=15,
            )
        if response.status_code == 401:
            st.error("Your session has expired. Please log out and log back in.")
        else:
            response.raise_for_status()
            st.success("Profile saved. Head to Home to generate starters using it.")
    except requests.RequestException as exc:
        st.error(friendly_network_error(exc))
