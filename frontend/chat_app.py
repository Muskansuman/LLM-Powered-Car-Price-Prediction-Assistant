from __future__ import annotations

import os
import time
from datetime import datetime

import httpx
import streamlit as st

TIMEOUT = 60.0

APP_NAME = "AutoValuator AI"
APP_TAGLINE = "Intelligent used-car price estimation"

EXAMPLE_PROMPTS = [
    "2018 Honda City, diesel, 95,000 km, first owner, manual",
    "2015 Maruti Swift, petrol, 60,000 km, first owner, manual",
    "2020 Hyundai Creta, diesel, 40,000 km, second owner, automatic",
]

LOGO_SVG = """
<svg width="36" height="36" viewBox="0 0 44 44" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect width="44" height="44" rx="12" fill="url(#g)"/>
  <defs><linearGradient id="g" x1="0" y1="0" x2="44" y2="44">
    <stop stop-color="#2563eb"/><stop offset="1" stop-color="#7c3aed"/>
  </linearGradient></defs>
  <path d="M10 26h24l-2.5-7H12.5L10 26z" stroke="#e0e7ff" stroke-width="1.5" fill="none"/>
  <circle cx="15" cy="27" r="2.5" fill="#fff" fill-opacity="0.9"/>
  <circle cx="29" cy="27" r="2.5" fill="#fff" fill-opacity="0.9"/>
</svg>
"""


def _css(theme: str) -> str:
    dark = theme == "dark"
    bg = "#070b14" if dark else "#f4f7fb"
    bg2 = "#0f172a" if dark else "#ffffff"
    text = "#f1f5f9" if dark else "#0f172a"
    muted = "#94a3b8" if dark else "#64748b"
    border = "rgba(148,163,184,0.12)" if dark else "rgba(15,23,42,0.08)"
    glass = "rgba(15,23,42,0.55)" if dark else "rgba(255,255,255,0.72)"
    accent = "#3b82f6"
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}
#MainMenu, footer, header {{ visibility: hidden; }}
.block-container {{
    padding: 1rem 2rem 2rem 2rem;
    max-width: 1200px;
}}
.stApp {{ background: {bg}; color: {text}; }}
div[data-testid="stSidebar"] {{
    background: {bg2};
    border-right: 1px solid {border};
}}
.hero {{
    background: linear-gradient(135deg, {'rgba(37,99,235,0.18)' if dark else 'rgba(37,99,235,0.08)'} 0%,
        {'rgba(124,58,237,0.12)' if dark else 'rgba(124,58,237,0.06)'} 100%);
    border: 1px solid {border};
    border-radius: 20px;
    padding: 1.75rem 2rem;
    margin-bottom: 1.25rem;
    backdrop-filter: blur(12px);
}}
.hero-title {{ font-size: 1.85rem; font-weight: 700; margin: 0; letter-spacing: -0.03em; color: {text}; }}
.hero-sub {{ color: {muted}; margin: 0.35rem 0 0 0; font-size: 1rem; }}
.brand-row {{ display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1rem; }}
.brand-name {{ font-weight: 700; font-size: 1.05rem; color: {text}; }}
.brand-tag {{ font-size: 0.78rem; color: {muted}; }}
.glass-card {{
    background: {glass};
    border: 1px solid {border};
    border-radius: 16px;
    padding: 1.1rem 1.25rem;
    backdrop-filter: blur(10px);
    box-shadow: {'0 8px 32px rgba(0,0,0,0.25)' if dark else '0 4px 24px rgba(15,23,42,0.06)'};
    margin-bottom: 0.75rem;
}}
.metric-label {{ font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.06em;
    color: {muted}; margin-bottom: 0.35rem; }}
.metric-value {{ font-size: 1.65rem; font-weight: 700; color: {text}; }}
.metric-sub {{ font-size: 0.85rem; color: {muted}; margin-top: 0.25rem; }}
.confidence-ring {{
    width: 72px; height: 72px; border-radius: 50%;
    background: conic-gradient({accent} var(--pct), {border} 0);
    display: flex; align-items: center; justify-content: center;
    margin: 0 auto 0.5rem auto;
}}
.confidence-inner {{
    width: 54px; height: 54px; border-radius: 50%; background: {bg2};
    display: flex; align-items: center; justify-content: center;
    font-weight: 700; font-size: 0.95rem; color: {text};
}}
.factor-pill {{
    display: inline-block; padding: 0.3rem 0.65rem; margin: 0.2rem 0.25rem 0 0;
    border-radius: 999px; font-size: 0.78rem; font-weight: 500;
}}
.pos {{ background: rgba(34,197,94,0.15); color: #4ade80; border: 1px solid rgba(34,197,94,0.25); }}
.neg {{ background: rgba(239,68,68,0.12); color: #f87171; border: 1px solid rgba(239,68,68,0.2); }}
.neu {{ background: rgba(148,163,184,0.12); color: {muted}; border: 1px solid {border}; }}
.status-dot {{ display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; }}
.status-ok {{ background: #22c55e; box-shadow: 0 0 8px rgba(34,197,94,0.6); }}
.status-bad {{ background: #ef4444; }}
.nav-item {{ padding: 0.55rem 0.75rem; border-radius: 10px; color: {muted}; font-size: 0.9rem; margin-bottom: 0.25rem; }}
.nav-active {{ background: {'rgba(37,99,235,0.2)' if dark else 'rgba(37,99,235,0.1)'}; color: {text}; font-weight: 600; }}
.history-item {{ padding: 0.65rem 0; border-bottom: 1px solid {border}; }}
.history-title {{ font-size: 0.85rem; font-weight: 600; color: {text}; }}
.history-meta {{ font-size: 0.75rem; color: {muted}; }}
.insight-box {{
    background: {'linear-gradient(90deg, rgba(124,58,237,0.15), rgba(37,99,235,0.1))' if dark else 'linear-gradient(90deg, rgba(37,99,235,0.08), rgba(124,58,237,0.05))'};
    border: 1px solid {border}; border-radius: 14px; padding: 1rem 1.25rem;
    font-size: 0.92rem; line-height: 1.6; color: {text};
}}
.section-title {{
    font-size: 0.95rem; font-weight: 600; color: {text}; margin: 0 0 0.75rem 0;
}}
.profile-grid {{
    display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem 0.75rem; margin-bottom: 0.85rem;
}}
.profile-item {{ font-size: 0.8rem; color: {muted}; }}
.profile-item strong {{ display: block; color: {text}; font-size: 0.88rem; margin-top: 0.1rem; }}
.glass-card, .hero, .insight-box {{
    animation: fadeUp 0.45s ease-out both;
}}
@keyframes fadeUp {{
    from {{ opacity: 0; transform: translateY(8px); }}
    to {{ opacity: 1; transform: translateY(0); }}
}}
div[data-testid="stChatMessage"] {{
    background: {glass};
    border: 1px solid {border};
    border-radius: 14px;
    padding: 0.35rem 0.5rem;
    margin-bottom: 0.65rem;
}}
div[data-testid="stChatInput"] > div {{
    border-radius: 14px !important;
    border: 1px solid {border} !important;
    background: {glass} !important;
    backdrop-filter: blur(10px);
}}
div[data-testid="column"] button[kind="secondary"] {{
    border-radius: 999px !important;
    border: 1px solid {border} !important;
    background: {glass} !important;
    font-size: 0.82rem !important;
    padding: 0.35rem 0.85rem !important;
}}
@media (max-width: 768px) {{
    .block-container {{ padding: 0.75rem 1rem 1.5rem 1rem; }}
    .hero-title {{ font-size: 1.45rem; }}
}}
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
        return f"http://{host_part}:{_default_api_port()}"
    except Exception:
        return None


def resolve_api_base() -> str:
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


def _init_state():
    defaults = {
        "messages": [],
        "session_id": None,
        "last_meta": None,
        "theme": "dark",
        "recent_valuations": [],
        "pending_prompt": None,
        "api_status": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _check_api_status(base_url: str) -> dict:
    try:
        t0 = datetime.now()
        r = httpx.get(f"{base_url}/health", timeout=8.0)
        ms = (datetime.now() - t0).total_seconds() * 1000
        ok = r.status_code == 200
        return {"ok": ok, "latency_ms": round(ms, 1), "detail": r.text[:80] if ok else r.text}
    except Exception as exc:
        return {"ok": False, "latency_ms": None, "detail": str(exc)}


def _get_api_status(base_url: str, *, refresh: bool = False) -> dict:
    cache = st.session_state.get("_api_status_cache")
    if not refresh and cache and cache.get("base_url") == base_url:
        return cache["status"]
    status = _check_api_status(base_url)
    st.session_state._api_status_cache = {"base_url": base_url, "status": status}
    return status


def _confidence_score(meta: dict) -> int:
    if meta.get("predicted_price") is None:
        return 0
    score = 88
    score -= len(meta.get("missing_fields") or []) * 8
    score -= min(len(meta.get("assumptions") or []), 3) * 3
    return max(55, min(98, score))


def _price_range(price: float) -> tuple[str, str]:
    lo = price * 0.92
    hi = price * 1.08
    return f"₹{lo:,.0f}", f"₹{hi:,.0f}"


def _vehicle_label(features: dict | None) -> str:
    if not features:
        return "Vehicle valuation"
    parts = [str(features.get("company") or ""), str(features.get("year") or "")]
    fuel = features.get("fuel")
    if fuel:
        parts.append(str(fuel))
    return " ".join(p for p in parts if p).strip() or "Vehicle valuation"


def _factors_html(features: dict | None) -> str:
    if not features:
        return '<p class="metric-sub">No structured factors available yet.</p>'
    pills = []
    km = features.get("km_driven")
    if km is not None:
        pills.append(("Low mileage" if km < 80000 else "Higher mileage", km < 80000))
    owner = features.get("owner")
    if owner and "First" in str(owner):
        pills.append(("First owner", True))
    elif owner:
        pills.append((f"{owner} owner", False))
    fuel = features.get("fuel")
    if fuel:
        pills.append((str(fuel), True))
    transmission = features.get("transmission")
    if transmission:
        pills.append((str(transmission), True))
    seller = features.get("seller_type")
    if seller:
        pills.append((f"{seller} sale", True))
    if not pills:
        return '<p class="metric-sub">No structured factors available yet.</p>'
    html = ""
    for label, positive in pills:
        cls = "pos" if positive else "neu"
        html += f'<span class="factor-pill {cls}">{label}</span>'
    return html


def _profile_html(features: dict) -> str:
    def cell(label: str, value) -> str:
        display = "—" if value is None or value == "" else value
        if label == "Odometer" and isinstance(display, (int, float)):
            display = f"{display:,.0f} km"
        return f'<div class="profile-item">{label}<strong>{display}</strong></div>'

    return (
        '<div class="profile-grid">'
        + cell("Make", features.get("company"))
        + cell("Year", features.get("year"))
        + cell("Odometer", features.get("km_driven"))
        + cell("Owner", features.get("owner"))
        + cell("Fuel", features.get("fuel"))
        + cell("Transmission", features.get("transmission"))
        + "</div>"
    )


def _depreciation_chart_html(price: float, year: int | None) -> str:
    base_year = year or datetime.now().year - 5
    years = list(range(base_year, datetime.now().year + 1))
    if len(years) < 2:
        years = [base_year, datetime.now().year]
    values = []
    for i, _ in enumerate(years):
        factor = 1.0 - (len(years) - 1 - i) * 0.08
        values.append(max(price * factor * 0.85, price * 0.5))
    values[-1] = price

    vmin, vmax = min(values), max(values)
    span = vmax - vmin or 1.0
    width, height = 320, 120
    pad_x, pad_y = 8, 12
    inner_w = width - pad_x * 2
    inner_h = height - pad_y * 2
    points = []
    for i, val in enumerate(values):
        x = pad_x + (i / max(len(values) - 1, 1)) * inner_w
        y = pad_y + inner_h - ((val - vmin) / span) * inner_h
        points.append(f"{x:.1f},{y:.1f}")
    polyline = " ".join(points)
    start_label = years[0]
    end_label = years[-1]
    end_value = f"₹{values[-1]:,.0f}"

    return f"""<div style="margin-top:0.35rem;">
        <svg viewBox="0 0 {width} {height}" width="100%" height="{height}" aria-hidden="true">
          <defs>
            <linearGradient id="depGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stop-color="#3b82f6" stop-opacity="0.35"/>
              <stop offset="100%" stop-color="#3b82f6" stop-opacity="0"/>
            </linearGradient>
          </defs>
          <polygon points="{polyline} {width - pad_x},{height - pad_y} {pad_x},{height - pad_y}"
                   fill="url(#depGrad)"/>
          <polyline points="{polyline}" fill="none" stroke="#3b82f6" stroke-width="2.5"
                    stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <div style="display:flex;justify-content:space-between;font-size:0.75rem;opacity:0.7;">
          <span>{start_label}</span><span>{end_label} · {end_value}</span>
        </div></div>"""


def _render_valuation_dashboard(meta: dict):
    price = meta.get("predicted_price")
    if price is None:
        return

    lo, hi = _price_range(float(price))
    conf = _confidence_score(meta)
    features = meta.get("extracted_features") or {}

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            f"""<div class="glass-card">
            <div class="metric-label">Estimated Value</div>
            <div class="metric-value">{meta.get('formatted_price', f'₹{price:,.0f}')}</div>
            <div class="metric-sub">Range: {lo} – {hi}</div></div>""",
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"""<div class="glass-card" style="text-align:center;">
            <div class="metric-label">Confidence Score</div>
            <div class="confidence-ring" style="--pct: {conf * 3.6}deg;">
              <div class="confidence-inner">{conf}%</div>
            </div>
            <div class="metric-sub">{'High confidence' if conf >= 85 else 'Moderate confidence'}</div></div>""",
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            """<div class="glass-card">
            <div class="metric-label">Market Trend</div>
            <div class="metric-value" style="font-size:1.25rem;">Stable</div>
            <div class="metric-sub">Based on segment & age profile</div></div>""",
            unsafe_allow_html=True,
        )

    left, right = st.columns([1.1, 1])
    with left:
        st.markdown(
            f"""<div class="glass-card">
            <div class="section-title">Car Profile</div>
            {_profile_html(features)}
            <div class="section-title" style="margin-top:0.25rem;">Key Value Factors</div>
            {_factors_html(features)}
            </div>""",
            unsafe_allow_html=True,
        )
    with right:
        st.markdown(
            f"""<div class="glass-card">
            <div class="section-title">Depreciation Trend</div>
            {_depreciation_chart_html(float(price), features.get("year"))}
            </div>""",
            unsafe_allow_html=True,
        )

    st.markdown(
        f'<div class="insight-box"><strong>AI Insight</strong><br>{meta.get("reply", "")}</div>',
        unsafe_allow_html=True,
    )


def _friendly_http_error(exc: httpx.HTTPStatusError) -> str:
    code = exc.response.status_code
    if code in (502, 503, 504):
        return (
            f"The valuation service is temporarily unavailable (HTTP {code}). "
            "This often happens on Render's free tier during cold starts — "
            "wait a few seconds and send your message again."
        )
    if code == 401:
        return "Authentication failed — check that `api_key` in secrets matches Render's `API_KEY`."
    body = exc.response.text.strip()
    if body.startswith("<!") or "<html" in body[:200].lower():
        return f"Unexpected gateway error (HTTP {code}). Please try again in a moment."
    return f"Service error ({code}): {body[:300]}"


def _call_chat(message: str, *, retries: int = 2) -> dict:
    url = f"{st.session_state.api_base_url}/chat"
    headers = {"api-key": st.session_state.api_key}
    payload = {"message": message, "session_id": st.session_state.session_id}
    last_exc: httpx.HTTPStatusError | None = None

    for attempt in range(retries + 1):
        try:
            resp = httpx.post(url, headers=headers, json=payload, timeout=TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            last_exc = exc
            if exc.response.status_code not in (502, 503, 504) or attempt >= retries:
                raise
            time.sleep(2 * (attempt + 1))

    assert last_exc is not None
    raise last_exc


def _process_prompt(prompt: str):
    st.session_state.messages.append({"role": "user", "content": prompt})
    try:
        data = _call_chat(prompt)
    except httpx.HTTPStatusError as exc:
        err = _friendly_http_error(exc)
        st.session_state.messages.append({"role": "assistant", "content": err, "meta": None})
        return
    except Exception as exc:
        err = f"Unable to reach valuation service: {exc}"
        st.session_state.messages.append({"role": "assistant", "content": err, "meta": None})
        return

    st.session_state.session_id = data["session_id"]
    st.session_state.last_meta = data
    st.session_state.messages.append({
        "role": "assistant",
        "content": data["reply"],
        "meta": data,
    })
    if data.get("predicted_price") is not None:
        entry = {
            "label": _vehicle_label(data.get("extracted_features")),
            "price": data.get("formatted_price"),
            "time": datetime.now().strftime("%H:%M"),
        }
        history = st.session_state.recent_valuations
        history.insert(0, entry)
        st.session_state.recent_valuations = history[:5]


def _reset_conversation():
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


# --- Page config ---
st.set_page_config(
    page_title=APP_NAME,
    layout="wide",
    initial_sidebar_state="expanded",
)

_init_state()
DEMO_PASSWORD = _resolve_demo_password()
if "demo_unlocked" not in st.session_state:
    st.session_state.demo_unlocked = False

st.session_state.api_base_url = resolve_api_base()
st.session_state.api_key = resolve_api_key()
st.session_state.api_status = _get_api_status(st.session_state.api_base_url)

theme = st.session_state.theme
st.markdown(_css(theme), unsafe_allow_html=True)

# --- Sidebar ---
with st.sidebar:
    st.markdown(
        f'<div class="brand-row">{LOGO_SVG}<div><div class="brand-name">{APP_NAME}</div>'
        f'<div class="brand-tag">{APP_TAGLINE}</div></div></div>',
        unsafe_allow_html=True,
    )

    theme_choice = st.toggle("Light mode", value=(theme == "light"), key="theme_toggle")
    if theme_choice and st.session_state.theme != "light":
        st.session_state.theme = "light"
        st.rerun()
    if not theme_choice and st.session_state.theme != "dark":
        st.session_state.theme = "dark"
        st.rerun()

    st.markdown('<div class="nav-item nav-active">Home</div>', unsafe_allow_html=True)
    st.markdown('<div class="nav-item">Valuation History</div>', unsafe_allow_html=True)
    st.markdown('<div class="nav-item">Market Insights</div>', unsafe_allow_html=True)

    st.divider()
    if st.button("New conversation", use_container_width=True, type="primary"):
        _reset_conversation()
        st.rerun()

    if st.session_state.recent_valuations:
        st.caption("RECENT VALUATIONS")
        for item in st.session_state.recent_valuations:
            st.markdown(
                f'<div class="history-item"><div class="history-title">{item["label"]}</div>'
                f'<div class="history-meta">{item["price"]} · {item["time"]}</div></div>',
                unsafe_allow_html=True,
            )

    st.divider()
    status = st.session_state.api_status or {}
    dot = "status-ok" if status.get("ok") else "status-bad"
    label = "All Systems Operational" if status.get("ok") else "API Unreachable"
    lat = status.get("latency_ms")
    lat_txt = f"{lat:.0f} ms" if lat is not None else "—"
    st.markdown(
        f'<div class="glass-card" style="padding:0.85rem;">'
        f'<div class="metric-label">API Status</div>'
        f'<div style="font-size:0.88rem;color:inherit;">'
        f'<span class="status-dot {dot}"></span>{label}</div>'
        f'<div class="metric-sub">Response: {lat_txt}</div></div>',
        unsafe_allow_html=True,
    )
    if st.button("Refresh status", use_container_width=True):
        st.session_state.api_status = _get_api_status(
            st.session_state.api_base_url, refresh=True
        )
        st.rerun()

# --- Demo gate ---
if DEMO_PASSWORD and not st.session_state.demo_unlocked:
    st.markdown(
        f'<div class="hero"><p class="hero-title">Sign in to {APP_NAME}</p>'
        f'<p class="hero-sub">Enter your demo access key to continue.</p></div>',
        unsafe_allow_html=True,
    )
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

# --- Hero ---
st.markdown(
    f"""<div class="hero">
    <p class="hero-title">Hi there — get the best value for your car.</p>
    <p class="hero-sub">Describe your vehicle in plain English. ML estimates price; LLM explains why.</p>
    </div>""",
    unsafe_allow_html=True,
)

# --- Example pills ---
st.caption("Try an example")
pill_cols = st.columns(len(EXAMPLE_PROMPTS))
for i, example in enumerate(EXAMPLE_PROMPTS):
    if pill_cols[i].button(example[:42] + ("…" if len(example) > 42 else ""), key=f"ex_{i}"):
        st.session_state.pending_prompt = example
        st.rerun()

# --- Chat history ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if not st.session_state.messages:
    with st.chat_message("assistant"):
        st.markdown(
            "Welcome to **AutoValuator AI**. Share make, model, year, fuel, kilometers, "
            "ownership, and transmission — I'll return an estimated market value with insights."
        )

# --- Valuation dashboard (latest prediction) ---
if st.session_state.last_meta and st.session_state.last_meta.get("predicted_price"):
    st.markdown("---")
    st.markdown("### Valuation Summary")
    _render_valuation_dashboard(st.session_state.last_meta)

# --- Input ---
prompt = st.session_state.pop("pending_prompt", None) or st.chat_input("Describe your vehicle...")
if prompt:
    with st.spinner("Analyzing vehicle profile..."):
        _process_prompt(prompt)
    st.rerun()
