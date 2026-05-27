from __future__ import annotations

import os

import httpx
import streamlit as st

TIMEOUT = 60.0

APP_NAME = "AutoValuator AI"
APP_TAGLINE = "Intelligent used-car price estimation"
APP_DESCRIPTION = (
    "Describe your vehicle in natural language. Our ML model predicts market value "
    "and explains the result with contextual insights."
)

LOGO_SVG = """
<svg width="44" height="44" viewBox="0 0 44 44" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect width="44" height="44" rx="10" fill="#1e3a5f"/>
  <path d="M10 26h24l-2.5-7H12.5L10 26z" stroke="#93c5fd" stroke-width="1.5" fill="none"/>
  <circle cx="15" cy="27" r="2.5" fill="#2563eb" stroke="#93c5fd" stroke-width="1"/>
  <circle cx="29" cy="27" r="2.5" fill="#2563eb" stroke="#93c5fd" stroke-width="1"/>
  <path d="M14 19h16" stroke="#60a5fa" stroke-width="1.5" stroke-linecap="round"/>
</svg>
"""

CUSTOM_CSS = """
<style>
    #MainMenu, footer, header {visibility: hidden;}
    .block-container {padding-top: 1.5rem; max-width: 820px;}
    .app-header {
        display: flex;
        align-items: center;
        gap: 1rem;
        padding: 1.25rem 0 0.5rem 0;
        border-bottom: 1px solid rgba(148, 163, 184, 0.15);
        margin-bottom: 1.25rem;
    }
    .app-title {
        font-size: 1.65rem;
        font-weight: 700;
        letter-spacing: -0.02em;
        color: #f1f5f9;
        margin: 0;
        line-height: 1.2;
    }
    .app-tagline {
        font-size: 0.95rem;
        color: #94a3b8;
        margin: 0.15rem 0 0 0;
    }
    .app-desc {
        font-size: 0.875rem;
        color: #64748b;
        margin: 1rem 0 0.5rem 0;
        line-height: 1.5;
    }
    div[data-testid="stSidebar"] {
        background-color: #121820;
        border-right: 1px solid rgba(148, 163, 184, 0.1);
    }
    div[data-testid="stSidebar"] h1, div[data-testid="stSidebar"] h2, div[data-testid="stSidebar"] h3 {
        font-size: 0.95rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        color: #94a3b8 !important;
    }
    .sidebar-brand {
        font-size: 1.1rem;
        font-weight: 700;
        color: #e2e8f0;
        margin-bottom: 0.25rem;
    }
    .example-box {
        background: rgba(37, 99, 235, 0.08);
        border: 1px solid rgba(37, 99, 235, 0.2);
        border-radius: 8px;
        padding: 0.85rem 1rem;
        font-size: 0.9rem;
        color: #cbd5e1;
        font-style: italic;
    }
</style>
"""


def _secret_get(section: str, key: str):
    try:
        return st.secrets[section][key]
    except Exception:
        return None


def _default_api_port() -> int:
    return int(os.getenv("API_PORT", "8000"))


def _infer_api_base_from_request() -> str | None:
    """Use the same host you used to open Streamlit, only change the port (phone/LAN friendly)."""
    try:
        ctx = getattr(st, "context", None)
        if ctx is None:
            return None
        headers = getattr(ctx, "headers", None)
        if not headers:
            return None
        raw = headers.get("Host") or headers.get("host")
        if not raw:
            return None
        raw = raw.strip()
        if raw.startswith("["):
            end = raw.find("]")
            if end == -1:
                return None
            host_part = raw[: end + 1]
        elif ":" in raw:
            maybe_host, maybe_port = raw.rsplit(":", 1)
            host_part = maybe_host if maybe_port.isdigit() else raw
        else:
            host_part = raw

        api_port = _default_api_port()
        return f"http://{host_part}:{api_port}"
    except Exception:
        return None


def resolve_api_base() -> str:
    """Explicit deploy URL wins; else same-host inference; else localhost."""
    for v in (
        os.getenv("API_BASE_URL"),
        os.getenv("STREAMLIT_API_BASE_URL"),
        _secret_get("api", "base_url"),
    ):
        if v:
            return str(v).rstrip("/")
    inferred = _infer_api_base_from_request()
    if inferred:
        return inferred
    return f"http://127.0.0.1:{_default_api_port()}"


def resolve_api_key() -> str:
    for v in (os.getenv("API_KEY"), _secret_get("api", "api_key")):
        if v:
            return str(v)
    return "demo-key"


def _resolve_demo_password() -> str | None:
    for v in (os.getenv("DEMO_PASSWORD"), _secret_get("demo", "password")):
        if v and str(v).strip():
            return str(v).strip()
    return None


def _render_header():
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="app-header">
            <div>{LOGO_SVG}</div>
            <div>
                <p class="app-title">{APP_NAME}</p>
                <p class="app-tagline">{APP_TAGLINE}</p>
            </div>
        </div>
        <p class="app-desc">{APP_DESCRIPTION}</p>
        """,
        unsafe_allow_html=True,
    )


st.set_page_config(
    page_title=APP_NAME,
    page_icon="📊",
    layout="centered",
    initial_sidebar_state="expanded",
)

DEMO_PASSWORD = _resolve_demo_password()
if "demo_unlocked" not in st.session_state:
    st.session_state.demo_unlocked = False

if DEMO_PASSWORD and not st.session_state.demo_unlocked:
    _render_header()
    st.info("This demo is password-protected. Enter the access key to continue.")
    with st.form("demo_login"):
        entered = st.text_input("Access key", type="password")
        submitted = st.form_submit_button("Continue", use_container_width=True)
        if submitted:
            if entered == DEMO_PASSWORD:
                st.session_state.demo_unlocked = True
                st.rerun()
            else:
                st.error("Invalid access key.")
    st.stop()

st.session_state.api_base_url = resolve_api_base()
st.session_state.api_key = resolve_api_key()

_render_header()


def _init_state():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "session_id" not in st.session_state:
        st.session_state.session_id = None
    if "last_meta" not in st.session_state:
        st.session_state.last_meta = None


_init_state()


with st.sidebar:
    st.markdown(f'<p class="sidebar-brand">{APP_NAME}</p>', unsafe_allow_html=True)
    st.caption("ML + LLM valuation assistant")
    st.divider()

    st.subheader("Session")
    if st.button("New conversation", use_container_width=True):
        sid = st.session_state.session_id
        if sid:
            try:
                httpx.delete(
                    f"{st.session_state.api_base_url}/chat/{sid}",
                    headers={"api-key": st.session_state.api_key},
                    timeout=10.0,
                )
            except Exception:
                pass
        st.session_state.messages = []
        st.session_state.session_id = None
        st.session_state.last_meta = None
        st.rerun()

    if DEMO_PASSWORD and st.button("Lock session", use_container_width=True):
        st.session_state.demo_unlocked = False
        st.session_state.messages = []
        st.session_state.session_id = None
        st.session_state.last_meta = None
        st.rerun()

    if st.session_state.last_meta:
        st.divider()
        st.subheader("Last prediction")
        meta = st.session_state.last_meta
        if meta.get("predicted_price") is not None:
            st.metric("Estimated price", meta["formatted_price"])
        st.metric("Response time", f"{meta.get('latency_ms', 0):.0f} ms")
        st.caption(f"Model: {meta.get('model', '—')} · {meta.get('provider', '—')}")
        if meta.get("missing_fields"):
            st.warning("Missing: " + ", ".join(meta["missing_fields"]))
        if meta.get("assumptions"):
            with st.expander("Assumptions"):
                for a in meta["assumptions"]:
                    st.write(f"· {a}")
        if meta.get("extracted_features"):
            with st.expander("Extracted features"):
                st.json(meta["extracted_features"])

    st.divider()
    st.subheader("System")
    st.caption(f"API endpoint")
    st.code(st.session_state.api_base_url, language=None)


for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


if not st.session_state.messages:
    with st.chat_message("assistant"):
        st.markdown(
            "Welcome. Provide vehicle details such as make, model, year, fuel type, "
            "kilometers driven, and ownership history."
        )
        st.markdown(
            '<div class="example-box">'
            "Example: I have a 2015 Maruti Swift, petrol, 60,000 km, first owner, manual transmission."
            "</div>",
            unsafe_allow_html=True,
        )


prompt = st.chat_input("Enter vehicle details...")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Analyzing..."):
            try:
                resp = httpx.post(
                    f"{st.session_state.api_base_url}/chat",
                    headers={"api-key": st.session_state.api_key},
                    json={
                        "message": prompt,
                        "session_id": st.session_state.session_id,
                    },
                    timeout=TIMEOUT,
                )
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPStatusError as exc:
                detail = exc.response.text
                err = f"Service error ({exc.response.status_code}): {detail}"
                st.error(err)
                st.session_state.messages.append({"role": "assistant", "content": err})
                st.stop()
            except Exception as exc:
                err = f"Unable to reach valuation service: {exc}"
                st.error(err)
                st.session_state.messages.append({"role": "assistant", "content": err})
                st.stop()

        st.session_state.session_id = data["session_id"]
        st.session_state.last_meta = data
        st.markdown(data["reply"])
        st.session_state.messages.append({"role": "assistant", "content": data["reply"]})
        st.rerun()
