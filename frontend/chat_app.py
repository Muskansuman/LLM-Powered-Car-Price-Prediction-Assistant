from __future__ import annotations

import os

import httpx
import streamlit as st

TIMEOUT = 60.0

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
        # [::1]:8501 — bracketed IPv6
        if raw.startswith("["):
            end = raw.find("]")
            if end == -1:
                return None
            host_part = raw[: end + 1]
        elif ":" in raw:
            # 192.168.1.5:8501 or localhost:8501 (last : separates port)
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


st.set_page_config(page_title="Car Price Chat", page_icon="🚗", layout="centered")

DEMO_PASSWORD = _resolve_demo_password()
if "demo_unlocked" not in st.session_state:
    st.session_state.demo_unlocked = False

if DEMO_PASSWORD and not st.session_state.demo_unlocked:
    st.title("🚗 Car Price Chat")
    st.info(
        "This demo is **password-protected**. Share the public link widely, "
        "but only give the password to people you trust."
    )
    with st.form("demo_login"):
        entered = st.text_input("Demo password", type="password")
        submitted = st.form_submit_button("Continue")
        if submitted:
            if entered == DEMO_PASSWORD:
                st.session_state.demo_unlocked = True
                st.rerun()
            else:
                st.error("Incorrect password.")
    st.stop()

# Refresh each run so LAN / hostname tracking stays correct
st.session_state.api_base_url = resolve_api_base()
st.session_state.api_key = resolve_api_key()

st.title("🚗 Car Price Chat")
st.caption("Tell me about your car in plain English and I'll estimate its price.")


def _init_state():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "session_id" not in st.session_state:
        st.session_state.session_id = None
    if "last_meta" not in st.session_state:
        st.session_state.last_meta = None


_init_state()


with st.sidebar:
    st.header("About")
    st.caption(f"**Backend:** `{st.session_state.api_base_url}`")
    if DEMO_PASSWORD and st.button("Lock demo (require password again)"):
        st.session_state.demo_unlocked = False
        st.session_state.messages = []
        st.session_state.session_id = None
        st.session_state.last_meta = None
        st.rerun()
    if st.button("Reset conversation"):
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

    if st.session_state.last_meta:
        st.divider()
        meta = st.session_state.last_meta
        st.markdown("**Last call**")
        st.metric("Latency", f"{meta.get('latency_ms', 0):.0f} ms")
        st.write(f"Provider: `{meta.get('provider')}`")
        st.write(f"Model: `{meta.get('model')}`")
        if meta.get("predicted_price") is not None:
            st.metric("Predicted price", meta["formatted_price"])
        if meta.get("missing_fields"):
            st.warning("Still missing: " + ", ".join(meta["missing_fields"]))
        if meta.get("assumptions"):
            with st.expander("Assumptions made"):
                for a in meta["assumptions"]:
                    st.write(f"- {a}")
        if meta.get("extracted_features"):
            with st.expander("Extracted features"):
                st.json(meta["extracted_features"])

    with st.expander("Connection help"):
        st.markdown(
            "Open this app with the **same hostname** your API uses "
            f"(API runs on port **{_default_api_port()}**). "
            "Example: if the UI is `http://192.168.1.10:8501`, the API should be "
            f"`http://192.168.1.10:{_default_api_port()}`.\n\n"
            "Cloud deploy: set **API_BASE_URL** (or Streamlit secret `[api] base_url`) once."
        )


for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


if not st.session_state.messages:
    with st.chat_message("assistant"):
        st.markdown(
            "Hi! Tell me about the car you'd like to value. For example:\n\n"
            "> *I have a 2015 Maruti Swift, ran about 70k km, petrol, second owner, manual.*"
        )


prompt = st.chat_input("Describe your car...")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
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
                err = f"Backend error ({exc.response.status_code}): {detail}"
                st.error(err)
                st.session_state.messages.append({"role": "assistant", "content": err})
                st.stop()
            except Exception as exc:
                err = f"Could not reach backend: {exc}"
                st.error(err)
                st.session_state.messages.append({"role": "assistant", "content": err})
                st.stop()

        st.session_state.session_id = data["session_id"]
        st.session_state.last_meta = data
        st.markdown(data["reply"])
        st.session_state.messages.append({"role": "assistant", "content": data["reply"]})
        st.rerun()
