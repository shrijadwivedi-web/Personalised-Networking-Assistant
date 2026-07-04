"""
Personalized Networking Assistant - Streamlit Frontend (Home / Generate)
----------------------------------------------------------------------------
This is the entry point of a multipage Streamlit app. Streamlit
auto-detects the frontend/pages/ directory and adds every file in it to
the sidebar navigation automatically -- no routing code required. This
file is the "Home" page: it owns the login/registration gate (nothing else
renders until the user is authenticated) plus the core generate-starters
flow.

Every backend call (other than /auth/register and /auth/login themselves)
sends the user's JWT access token as a Bearer token in the Authorization
header, and the backend scopes all data (history, feedback, profile) to
that user.

Streamlit's execution model: the ENTIRE script re-runs top-to-bottom on
every user interaction. Anything that needs to persist across interactions
-- the access token, the generated suggestions, etc -- is stored in
st.session_state, which is shared across every page in this app. Note that
this state lives only for the current browser session: a hard page refresh
clears it and returns the user to the login screen. Making login persist
across refreshes would mean storing the token in a browser cookie, which
is a deliberate scope decision left out for now to keep the auth flow
simple and easy to reason about.
"""

import requests
import streamlit as st

from common import (
    BASE_URL,
    auth_headers,
    friendly_network_error,
    inject_custom_css,
    is_logged_in,
    page_header,
    render_sidebar_account,
)

st.set_page_config(page_title="Personalized Networking Assistant", page_icon="🤝")
inject_custom_css()

TONE_OPTIONS = ["casual", "formal", "witty"]


# ---------------------------------------------------------------------------
# Login / Registration gate -- nothing else renders until the user is
# authenticated, since every API endpoint below requires a valid token.
# ---------------------------------------------------------------------------
if not is_logged_in():
    page_header(
        "🤝 Personalized Networking Assistant",
        "Log in or create an account to get started.",
    )

    login_tab, register_tab = st.tabs(["Log In", "Register"])

    with login_tab:
        with st.form("login_form"):
            login_username = st.text_input(
                "Username", key="login_username", placeholder="e.g. jane_doe"
            )
            login_password = st.text_input(
                "Password", type="password", key="login_password", placeholder="••••••••"
            )
            submitted = st.form_submit_button("Log In", type="primary", use_container_width=True)

        if submitted:
            if not login_username or not login_password:
                st.warning("Please enter both a username and password.")
            else:
                try:
                    with st.spinner("Logging in..."):
                        response = requests.post(
                            f"{BASE_URL}/auth/login",
                            json={"username": login_username, "password": login_password},
                            timeout=15,
                        )
                    if response.status_code == 200:
                        st.session_state["access_token"] = response.json()["access_token"]
                        st.session_state["username"] = login_username
                        st.rerun()
                    elif response.status_code == 401:
                        st.error("Incorrect username or password.")
                    else:
                        detail = response.json().get("detail", "Login failed. Please try again.")
                        st.error(detail)
                except requests.RequestException as exc:
                    st.error(friendly_network_error(exc))

    with register_tab:
        with st.form("register_form"):
            reg_username = st.text_input(
                "Choose a username", key="reg_username", placeholder="e.g. jane_doe"
            )
            reg_password = st.text_input(
                "Choose a password (min 8 characters)",
                type="password",
                key="reg_password",
                placeholder="••••••••",
            )
            reg_submitted = st.form_submit_button("Register", type="primary", use_container_width=True)

        if reg_submitted:
            if not reg_username or not reg_password:
                st.warning("Please enter both a username and password.")
            elif len(reg_password) < 8:
                st.warning("Password must be at least 8 characters.")
            else:
                try:
                    with st.spinner("Creating your account..."):
                        response = requests.post(
                            f"{BASE_URL}/auth/register",
                            json={"username": reg_username, "password": reg_password},
                            timeout=15,
                        )
                    if response.status_code == 201:
                        st.success("Account created! Switch to the Log In tab to continue.")
                    elif response.status_code == 409:
                        st.error("That username is already taken. Please choose another.")
                    else:
                        detail = response.json().get("detail", "Registration failed. Please try again.")
                        st.error(detail)
                except requests.RequestException as exc:
                    st.error(friendly_network_error(exc))

    st.stop()  # Don't render anything below until the user is logged in.


# ---------------------------------------------------------------------------
# Main app -- only reachable once logged in.
# ---------------------------------------------------------------------------
render_sidebar_account()

page_header(
    "🤝 Personalized Networking Assistant",
    "Fill in an event and your interests below. For results tailored to "
    "your role and goals, fill out your **Profile** page too.",
)

# ---------------------------------------------------------------------------
# Input section + main generation flow
# ---------------------------------------------------------------------------
st.markdown("#### Generate conversation starters")

event_description = st.text_area(
    "Event description",
    placeholder="e.g. A conference on using AI to design more sustainable cities",
    height=100,
)
user_interests = st.text_input(
    "Your interests (comma-separated)",
    placeholder="e.g. climate change, urban planning",
)
tone = st.selectbox(
    "Tone",
    TONE_OPTIONS,
    index=0,
    format_func=str.capitalize,
    help="Changes the voice of the generated starters. Try switching this "
         "and regenerating to see the difference.",
)

generate_clicked = st.button("Generate Starters", type="primary", use_container_width=True)

if generate_clicked:
    if not event_description.strip() or not user_interests.strip():
        st.warning("Please fill in both the event description and your interests.")
    else:
        # Clean up "AI, blockchain , healthcare" -> ["AI", "blockchain", "healthcare"]
        interests_list = [i.strip() for i in user_interests.split(",") if i.strip()]

        with st.spinner("Generating personalized conversation starters..."):
            try:
                response = requests.post(
                    f"{BASE_URL}/generate-conversation",
                    json={
                        "description": event_description,
                        "interests": interests_list,
                        "tone": tone,
                    },
                    headers=auth_headers(),
                    timeout=60,
                )
                if response.status_code == 401:
                    st.error("Your session has expired. Please log out and log back in.")
                elif response.status_code == 429:
                    st.error("You're generating too quickly. Please wait a moment and try again.")
                else:
                    response.raise_for_status()
                    data = response.json()
                    st.session_state["themes"] = data["themes"]
                    st.session_state["suggestions"] = data["suggestions"]
                    st.session_state["confidence_scores"] = data["confidence_scores"]
                    st.session_state["confidence_explanations"] = data["confidence_explanations"]
            except requests.RequestException as exc:
                st.error(friendly_network_error(exc))
            except (KeyError, ValueError):
                # The backend responded but not with the shape we expect --
                # surfacing the raw parse error would be a stack trace with
                # no clear next step for the user, so give one instead.
                st.error("Received an unexpected response from the backend. Please try again.")

# Results + feedback section -- only rendered once suggestions exist in
# session_state, otherwise this section would flash empty on every load.
if "suggestions" in st.session_state:
    st.markdown("---")

    st.markdown("#### Detected themes")
    if st.session_state["themes"]:
        st.write(", ".join(st.session_state["themes"]))
    else:
        st.caption("No specific themes were detected for this description.")

    st.markdown("#### Suggested conversation starters")
    if not st.session_state["suggestions"]:
        st.info("No suggestions were generated. Try rephrasing your event description.")

    scores = st.session_state.get("confidence_scores", [])
    explanations = st.session_state.get("confidence_explanations", [])

    for i, suggestion in enumerate(st.session_state["suggestions"]):
        with st.container(border=True):
            st.markdown(f"**{i + 1}.** {suggestion}")

            # Confidence score tag, shown as filled/empty stars plus the
            # one-line reason from app/services/scorer.py.
            if i < len(scores):
                filled = "★" * scores[i]
                empty = "☆" * (5 - scores[i])
                reason = explanations[i] if i < len(explanations) else ""
                st.caption(f"{filled}{empty} — {reason}")

            # Unique keys (using the loop index) are required -- without them
            # Streamlit can't tell buttons in a loop apart and feedback clicks
            # could be misattributed to the wrong suggestion.
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("👍 Helpful", key=f"like_{i}", use_container_width=True):
                    try:
                        requests.post(
                            f"{BASE_URL}/feedback",
                            json={"suggestion": suggestion, "action": "like"},
                            headers=auth_headers(),
                            timeout=10,
                        ).raise_for_status()
                        st.success("Thanks for the feedback!")
                    except requests.RequestException as exc:
                        st.error(friendly_network_error(exc))
            with col2:
                if st.button("👎 Not helpful", key=f"dislike_{i}", use_container_width=True):
                    try:
                        requests.post(
                            f"{BASE_URL}/feedback",
                            json={"suggestion": suggestion, "action": "dislike"},
                            headers=auth_headers(),
                            timeout=10,
                        ).raise_for_status()
                        st.success("Thanks for the feedback!")
                    except requests.RequestException as exc:
                        st.error(friendly_network_error(exc))
