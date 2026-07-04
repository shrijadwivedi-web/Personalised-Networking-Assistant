"""
Shared Frontend Helpers
--------------------------
Common utilities used by every page in the multipage Streamlit app
(app.py plus everything in pages/). Centralizing these here means the
BASE_URL/auth/session_state conventions only need to be defined once,
instead of copy-pasted into every page file.

Streamlit's multipage session_state is shared across all pages in a single
browser session -- setting st.session_state["access_token"] in app.py is
visible from pages/1_Profile.py without any extra plumbing. What each page
DOES need to do individually is guard against being viewed before login:
a user can click a page in the sidebar directly without visiting app.py
first, so every page calls require_login() at the top.
"""

import os

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# Configurable so this works both locally (default) and inside Docker,
# where the frontend container must reach the backend by its service name
# (see docker-compose.yml, which sets BACKEND_URL=http://backend:8000)
# rather than by localhost/127.0.0.1.
BASE_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")


def auth_headers() -> dict:
    """Build the Authorization header from the token stored in session_state."""
    token = st.session_state.get("access_token")
    return {"Authorization": f"Bearer {token}"} if token else {}


def is_logged_in() -> bool:
    return "access_token" in st.session_state


def logout() -> None:
    for key in ("access_token", "username", "themes", "suggestions",
                "confidence_scores", "confidence_explanations"):
        st.session_state.pop(key, None)


def friendly_network_error(exc: requests.RequestException) -> str:
    """
    Turn a raw requests exception into a message a non-technical user can
    act on, instead of a Python exception string. The most common failure
    during grading/demoing is simply "forgot to start the backend", so
    that case gets its own specific message rather than a generic one.
    Shared across every page so the wording stays consistent app-wide.
    """
    if isinstance(exc, requests.exceptions.ConnectionError):
        return (
            "Can't reach the backend API. Make sure it's running "
            f"(expected at {BASE_URL}) and try again."
        )
    if isinstance(exc, requests.exceptions.Timeout):
        return "The backend took too long to respond. Please try again."
    return "Something went wrong talking to the backend. Please try again."


def require_login() -> None:
    """
    Call at the top of every page except the Home page (which has its own
    login/register form). Stops rendering with a friendly message if the
    user reached this page directly without logging in first -- Streamlit's
    sidebar lets people jump straight to any page, bypassing app.py.
    """
    if not is_logged_in():
        page_header("🤝 Personalized Networking Assistant")
        st.info("Please log in from the **Home** page first.")
        st.stop()


def inject_custom_css() -> None:
    """
    Applies the SaaS-style polish that .streamlit/config.toml can't
    (Streamlit's theme config only covers colors/font, not spacing, card
    borders, or per-component layout). Call once near the top of every
    page, right after st.set_page_config().

    Deliberately targets Streamlit's documented data-testid attributes
    (data-testid="stButton" etc.) rather than the auto-generated
    st-emotion-cache-* class names. testid attributes are Streamlit's
    stable, semver-respecting styling hooks; the emotion-cache classes are
    implementation details that change across Streamlit releases and would
    make this CSS liable to silently stop working on an upgrade.
    """
    st.markdown(
        """
        <style>
        /* Comfortable page margins + max content width, closer to a
           SaaS dashboard than Streamlit's default edge-to-edge layout. */
        .block-container {
            max-width: 760px;
            padding-top: 2.5rem;
            padding-bottom: 3rem;
        }

        /* Buttons: flatter, slightly rounded, no heavy default shadow. */
        [data-testid="stButton"] button {
            border-radius: 8px;
            font-weight: 500;
            padding: 0.5rem 1.25rem;
            transition: opacity 0.15s ease;
        }
        [data-testid="stButton"] button:hover {
            opacity: 0.85;
        }
        [data-testid="stButton"] button:disabled {
            opacity: 0.5;
        }

        /* Text inputs / text areas / selects: consistent rounded borders
           and a bit more breathing room, card-like rather than the sharp
           default Streamlit look. */
        [data-testid="stTextInput"] input,
        [data-testid="stTextArea"] textarea,
        [data-testid="stSelectbox"] div[data-baseweb="select"] {
            border-radius: 8px;
        }

        /* Alerts (st.success/st.error/st.warning/st.info): rounded,
           consistent left-accent-bar look instead of Streamlit's flat
           default block, and no gradients per the SaaS aesthetic. */
        [data-testid="stAlert"] {
            border-radius: 8px;
            padding: 0.9rem 1rem;
        }

        /* Sidebar: tighter, consistent padding so caption/button/divider
           don't feel cramped against the sidebar edge. */
        [data-testid="stSidebar"] .block-container {
            padding-top: 2rem;
        }

        /* Form containers (st.form): a subtle card border, giving the
           login/register/profile forms a visually separated "card" rather
           than blending into the page background. */
        [data-testid="stForm"] {
            border: 1px solid #E5E7EB;
            border-radius: 12px;
            padding: 1.5rem 1.5rem 0.5rem 1.5rem;
        }

        /* Tabs (used on the login/register page): remove the default
           heavy underline styling in favor of a quieter, SaaS-style tab. */
        [data-testid="stTabs"] [data-baseweb="tab-list"] {
            gap: 1.5rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_header(title: str, subtitle: str = "") -> None:
    """
    Consistent page title treatment used across all pages, replacing
    bare st.title() calls. Keeps typography and spacing identical whether
    it's Home, Profile, History, etc., rather than each page's heading
    looking subtly different.
    """
    st.markdown(f"## {title}")
    if subtitle:
        st.caption(subtitle)
    st.write("")  # small vertical breathing room before page content


def render_sidebar_account() -> None:
    """Shared logged-in-as / log-out block, shown at the top of the sidebar
    on every page so a user is never more than one click from logging out."""
    with st.sidebar:
        st.caption(f"Signed in as **{st.session_state.get('username', '')}**")
        if st.button("Log Out", key="sidebar_logout", use_container_width=True):
            logout()
            st.rerun()
        st.markdown("---")
