from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Iterable

import pandas as pd
import streamlit as st

from database import PageCache
from miner import AdsMiner
from models import MinerSummary, PageResult
from utils import COUNTRIES, MIN_PRESETS, RESULTS_DIR, ensure_dirs, slugify

ensure_dirs()

st.set_page_config(
    page_title="R+miner",
    page_icon="🟡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>


    header[data-testid="stHeader"] {
        background: transparent !important;
        height: 0 !important;
        visibility: hidden !important;
    }

    div[data-testid="stToolbar"] {
        display: none !important;
    }

    div[data-testid="stDecoration"] {
        display: none !important;
    }

    div[data-testid="stStatusWidget"] {
        display: none !important;
    }

    #MainMenu {
        visibility: hidden !important;
    }

    footer {
        visibility: hidden !important;
    }

    .stAppDeployButton {
        display: none !important;
    }

    button[title="View fullscreen"] {
        display: none !important;
    }

    .block-container {
        padding-top: 0.9rem !important;
        max-width: 1500px;
    }
    button[kind="header"] {
        display: none !important;
    }

    :root {
        --bg-main: #050505;
        --bg-soft: #0b0b0b;
        --bg-panel: rgba(12, 12, 12, 0.96);
        --bg-panel-2: rgba(18, 18, 18, 0.98);
        --text: #f6f2e8;
        --muted: #9c9588;
        --gold: #ffbf1f;
        --gold-2: #ffcf4a;
        --gold-3: #8e6400;
        --line: rgba(255, 191, 31, 0.20);
        --line-strong: rgba(255, 191, 31, 0.42);
        --success-bg: rgba(20, 55, 31, 0.88);
        --warning-bg: rgba(76, 58, 8, 0.88);
        --shadow: 0 20px 60px rgba(0, 0, 0, 0.55);
    }

    html, body, [class*="css"]  {
        font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }

    .stApp {
        background:
            radial-gradient(circle at top right, rgba(255,191,31,0.10), transparent 25%),
            radial-gradient(circle at 20% 10%, rgba(255,191,31,0.05), transparent 18%),
            linear-gradient(180deg, #050505 0%, #070707 30%, #050505 100%);
        color: var(--text);
    }

    div[data-baseweb="select"] * {
        color: #fff5d7 !important;
    }

    div[data-baseweb="popover"] {
        background: #0b0b0b !important;
        border: 1px solid rgba(255,191,31,.16) !important;
    }

    ul[role="listbox"] {
        background: #0b0b0b !important;
        border: 1px solid rgba(255,191,31,.16) !important;
    }

    li[role="option"] {
        background: #0b0b0b !important;
        color: #fff5d7 !important;
    }

    li[role="option"]:hover {
        background: rgba(255,191,31,.08) !important;
    }


    details {
        border: 1px solid rgba(255,191,31,.12);
        border-radius: 16px;
        background: linear-gradient(180deg, rgba(12,12,12,.96), rgba(8,8,8,.98));
        overflow: hidden;
    }

    details summary {
        color: #fff1c9 !important;
        font-weight: 700 !important;
    }
    .block-container {
        padding-top: 1.3rem;
        max-width: 1500px;
    }

        section[data-testid="stSidebar"] {
        background:
            radial-gradient(circle at top left, rgba(255,191,31,0.08), transparent 22%),
            linear-gradient(180deg, #090909 0%, #060606 100%);
        border-right: 1px solid rgba(255,191,31,0.08);
        box-shadow: inset -1px 0 0 rgba(255,191,31,0.04);
    }

    section[data-testid="stSidebar"] .block-container {
        padding-top: 1.2rem;
    }

    .brand-mini {
        display: flex;
        align-items: center;
        gap: 0.8rem;
        margin-bottom: 1rem;
        padding: 0.8rem 0.9rem;
        border-radius: 18px;
        background: linear-gradient(180deg, rgba(20,20,20,.98), rgba(10,10,10,.98));
        border: 1px solid rgba(255,191,31,.18);
        box-shadow: var(--shadow);
        position: relative;
        overflow: hidden;
    }

    .brand-mini::before {
        content: "";
        position: absolute;
        inset: 0;
        border-radius: 18px;
        padding: 1px;
        background: linear-gradient(90deg,
            rgba(255,191,31,0.55) 0%,
            rgba(255,191,31,0.12) 18%,
            rgba(255,191,31,0.05) 82%,
            rgba(255,191,31,0.45) 100%);
        -webkit-mask:
            linear-gradient(#000 0 0) content-box,
            linear-gradient(#000 0 0);
        -webkit-mask-composite: xor;
        mask-composite: exclude;
        pointer-events: none;
    }

    .brand-icon {
        width: 44px;
        height: 44px;
        border-radius: 14px;
        display: grid;
        place-items: center;
        font-size: 1.1rem;
        color: #1a1200;
        background: linear-gradient(180deg, var(--gold-2), #ffb400);
        box-shadow: 0 0 24px rgba(255,191,31,.25);
        flex-shrink: 0;
    }

    .brand-title {
        color: #fff6d9;
        font-weight: 800;
        font-size: 1.15rem;
        line-height: 1.1;
        letter-spacing: 0.02em;
    }

    .brand-sub {
        color: var(--gold);
        font-size: 0.78rem;
        margin-top: 0.1rem;
        letter-spacing: 0.16em;
        text-transform: uppercase;
    }

    .sidebar-footer-box {
        margin-top: 1rem;
        padding: 0.95rem 1rem;
        border-radius: 18px;
        background: linear-gradient(180deg, rgba(16,16,16,.96), rgba(10,10,10,.98));
        border: 1px solid rgba(255,191,31,.16);
        color: #d8cfbf;
        box-shadow: var(--shadow);
    }

    .sidebar-footer-box b {
        color: var(--gold);
    }

    .hero-shell,
    .panel-shell,
    .result-shell,
    .summary-shell {
        position: relative;
        background:
            linear-gradient(180deg, rgba(14,14,14,.98), rgba(8,8,8,.98));
        border-radius: 24px;
        border: 1px solid rgba(255,191,31,0.13);
        box-shadow: var(--shadow);
        overflow: hidden;
    }

    .hero-shell::before,
    .panel-shell::before,
    .result-shell::before,
    .summary-shell::before {
        content: "";
        position: absolute;
        inset: 0;
        border-radius: 24px;
        padding: 1px;
        background: linear-gradient(90deg,
            rgba(255,191,31,0.55) 0%,
            rgba(255,191,31,0.10) 20%,
            rgba(255,191,31,0.05) 80%,
            rgba(255,191,31,0.42) 100%);
        -webkit-mask:
            linear-gradient(#000 0 0) content-box,
            linear-gradient(#000 0 0);
        -webkit-mask-composite: xor;
        mask-composite: exclude;
        pointer-events: none;
    }

/* SIDEBAR SEMPRE ABERTA */
section[data-testid="stSidebar"] {
    min-width: 273px !important;
    width: 273px !important;
    max-width: 273px !important;
    transform: none !important;
    visibility: visible !important;
    display: block !important;
}

/* Esconde o botão de recolher */
section[data-testid="stSidebar"]
button[data-testid="stSidebarCollapseButton"] {
    display: none !important;
}

/* Esconde também o controle de sidebar do topo */
button[data-testid="stSidebarCollapseButton"] {
    display: none !important;
}

/* Garante que o conteúdo principal respeite a sidebar */
[data-testid="stAppViewContainer"] {
    margin-left: 0 !important;
}
section[data-testid="stSidebar"] {
    min-width: 273px !important;
    max-width: 273px !important;
    width: 273px !important;
}


    .hero-shell {
        padding: 1.5rem 1.6rem;
        margin-bottom: 1rem;
        background:
            radial-gradient(circle at 78% 35%, rgba(255,191,31,.10), transparent 14%),
            radial-gradient(circle at 80% 50%, rgba(255,191,31,.06), transparent 18%),
            linear-gradient(180deg, rgba(10,10,10,.98), rgba(6,6,6,.98));
    }

    .hero-grid {
        display: grid;
        grid-template-columns: 1.4fr 0.8fr;
        gap: 1rem;
        align-items: center;
    }

    .eyebrow {
        display: inline-flex;
        align-items: center;
        gap: .4rem;
        color: var(--gold);
        font-size: 0.82rem;
        letter-spacing: 0.16em;
        text-transform: uppercase;
        margin-bottom: .4rem;
        font-weight: 700;
    }

    .hero-shell h1 {
        margin: 0;
        font-size: 2.2rem;
        line-height: 1.05;
        color: #fff9e8;
        font-weight: 900;
    }

    .hero-shell h1 span {
        display: block;
        color: var(--gold);
        margin-top: .15rem;
    }

    .hero-shell p {
        margin: 0.85rem 0 0 0;
        max-width: 800px;
        color: #c7bfaf;
        font-size: 1rem;
        line-height: 1.55;
    }

    .hero-visual-wrap {
        display: flex;
        justify-content: center;
        align-items: center;
        min-height: 185px;
        position: relative;
    }

    .hero-visual-wrap::before {
        content: "";
        position: absolute;
        width: 220px;
        height: 220px;
        background: radial-gradient(circle, rgba(255,191,31,.22), transparent 60%);
        filter: blur(18px);
        opacity: .9;
    }

    .hero-gem {
        width: 86px;
        height: 86px;
        transform: rotate(45deg);
        border-radius: 18px;
        background: linear-gradient(180deg, #ffd966, #ffb400);
        box-shadow:
            0 0 28px rgba(255,191,31,.45),
            0 0 60px rgba(255,191,31,.22);
        position: relative;
    }

    .hero-gem::before,
    .hero-gem::after {
        content: "";
        position: absolute;
        inset: 13px;
        border: 1px solid rgba(26, 18, 0, 0.25);
        border-radius: 10px;
    }

    .hero-gem::after {
        inset: 26px;
        border-color: rgba(26,18,0,.18);
    }

    .panel-shell {
        padding: 1.1rem 1.2rem 0.4rem 1.2rem;
        margin-bottom: 1rem;
    }

    .panel-title {
        color: #fff1c9;
        font-size: 1.02rem;
        font-weight: 800;
        letter-spacing: .03em;
        text-transform: uppercase;
        margin-bottom: .7rem;
        display: flex;
        align-items: center;
        gap: 0.55rem;
    }

    .panel-title .dot {
        color: var(--gold);
        font-size: 1rem;
    }

    .summary-shell {
        padding: 1.05rem 1.15rem;
        margin-bottom: 1rem;
    }

    .result-shell {
        padding: 1rem 1.05rem;
        margin: 0.65rem 0 1rem 0;
    }

    .result-header {
        display: flex;
        align-items: center;
        gap: .8rem;
        flex-wrap: wrap;
    }

    .rank-chip {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-width: 54px;
        height: 36px;
        padding: 0 .9rem;
        border-radius: 999px;
        font-weight: 900;
        color: #1a1200;
        background: linear-gradient(180deg, var(--gold-2), #ffb400);
        box-shadow: 0 0 20px rgba(255,191,31,.18);
        font-size: 1rem;
    }

    .result-title {
        margin: 0;
        font-size: 1.35rem;
        color: #fff8e1;
        font-weight: 800;
        line-height: 1.15;
    }

    .big-count {
        font-size: 1.28rem;
        font-weight: 800;
        color: var(--gold);
        margin-top: .35rem;
    }

    .muted {
        color: var(--muted);
    }

    .micro-caption {
        display: inline-flex;
        align-items: center;
        gap: .35rem;
        font-size: .82rem;
        color: #c2b9a8;
        margin-top: .25rem;
    }

    /* Inputs */
    .stTextInput > div > div > input,
    .stNumberInput input,
    div[data-baseweb="select"] > div,
    div[data-baseweb="input"] > div {
        background: linear-gradient(180deg, rgba(8,8,8,.98), rgba(12,12,12,.98)) !important;
        color: #fff5d7 !important;
        border: 1px solid rgba(255,191,31,.16) !important;
        border-radius: 14px !important;
        box-shadow: none !important;
    }

    .stTextInput label,
    .stNumberInput label,
    .stSelectbox label,
    .stCheckbox label {
        color: #f6f1e4 !important;
        font-weight: 600 !important;
    }

    .stTextInput > div > div > input:focus,
    .stNumberInput input:focus {
        border-color: rgba(255,191,31,.42) !important;
        box-shadow: 0 0 0 1px rgba(255,191,31,.15), 0 0 0 4px rgba(255,191,31,.06) !important;
    }

    .stCheckbox {
        padding-top: 0.15rem;
    }

    /* Buttons */
    .stButton > button,
    .stDownloadButton > button,
    .stLinkButton a {
        border-radius: 14px !important;
        border: 1px solid rgba(255,191,31,.20) !important;
        background: linear-gradient(180deg, #ffcf4a, #ffb400) !important;
        color: #1a1200 !important;
        font-weight: 800 !important;
        box-shadow: 0 8px 26px rgba(255,191,31,.20) !important;
    }

    .stButton > button:hover,
    .stDownloadButton > button:hover,
    .stLinkButton a:hover {
        filter: brightness(1.03);
        border-color: rgba(255,191,31,.34) !important;
        box-shadow: 0 10px 30px rgba(255,191,31,.28) !important;
    }

    /* Secondary button-like links inside result cards */
    .stLinkButton a {
        text-align: center;
    }

    /* Tabs */
    button[data-baseweb="tab"] {
        background: rgba(255,191,31,.05) !important;
        border: 1px solid rgba(255,191,31,.10) !important;
        border-radius: 12px !important;
        color: #eadfc8 !important;
        margin-right: .4rem !important;
    }

    button[data-baseweb="tab"][aria-selected="true"] {
        background: linear-gradient(180deg, rgba(255,191,31,.18), rgba(255,191,31,.10)) !important;
        color: #fff2c9 !important;
        border-color: rgba(255,191,31,.28) !important;
    }

    .history-item {
        padding: .75rem .85rem;
        border-radius: 14px;
        border: 1px solid rgba(255,191,31,.10);
        background: linear-gradient(180deg, rgba(13,13,13,.94), rgba(8,8,8,.98));
        margin-bottom: .5rem;
    }

    /* Metrics */
    div[data-testid="stMetric"] {
        background: linear-gradient(180deg, rgba(13,13,13,.95), rgba(9,9,9,.98));
        border: 1px solid rgba(255,191,31,.13);
        border-radius: 18px;
        padding: .9rem .95rem;
        box-shadow: var(--shadow);
    }

    div[data-testid="stMetricLabel"] {
        color: #d8cfbf !important;
        font-weight: 600 !important;
    }

    div[data-testid="stMetricValue"] {
        color: var(--gold) !important;
        font-size: 1.7rem !important;
        font-weight: 800 !important;
    }

    /* Dataframe wrapper */
    div[data-testid="stDataFrame"] {
        border: 1px solid rgba(255,191,31,.14);
        border-radius: 18px;
        overflow: hidden;
    }

    /* Alert boxes */
    div[data-testid="stAlert"] {
        border-radius: 16px !important;
        border: 1px solid rgba(255,191,31,.12) !important;
    }

    /* Progress bar */
    div[role="progressbar"] > div > div {
        background: linear-gradient(90deg, #ffcf4a, #ffb400) !important;
    }

    hr {
        border-color: rgba(255,191,31,.12) !important;
    }

    .caption-note {
        color: #bfb6a6;
        font-size: 0.9rem;
        line-height: 1.5;
    }

    .footer-explain {
        padding: 1rem 1.05rem;
        border-radius: 18px;
        background: linear-gradient(180deg, rgba(12,12,12,.96), rgba(7,7,7,.98));
        border: 1px solid rgba(255,191,31,.12);
    }

    @media (max-width: 1100px) {
        .hero-grid {
            grid-template-columns: 1fr;
        }

        .hero-visual-wrap {
            min-height: 120px;
        }

        .hero-shell h1 {
            font-size: 1.8rem;
        }
    }
</style>
""",
    unsafe_allow_html=True,
)


def _state_defaults() -> None:
    st.session_state.setdefault("summary", None)
    st.session_state.setdefault("live_results", [])
    st.session_state.setdefault("last_error", None)


_state_defaults()


def _sample_id(result: PageResult) -> str:
    if not result.sample_ads:
        return ""
    sample = result.sample_ads[0]
    return sample.ad_library_id or sample.archive_id or sample.raw_ad_id or ""


def _to_rows(results: Iterable[PageResult]) -> list[dict]:
    rows: list[dict] = []
    for rank, item in enumerate(results, start=1):
        rows.append(
            {
                "Rank": rank,
                "Page Name": item.page_name,
                "Page ID": item.page_id,
                "Active Ads Found": item.active_ads_found,
                "Count Capped": item.count_capped,
                "Oldest Active Ad": item.oldest_start,
                "Days Running": item.oldest_days,
                "Page Likes": item.likes,
                "Verified": item.verified,
                "Facebook URL": item.facebook_url or "",
                "Library URL": item.library_url or "",
                "Sample Ad ID": _sample_id(item),
                "From Cache": item.from_cache,
            }
        )
    return rows


def _save_exports(summary: MinerSummary) -> tuple[Path, Path]:
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    base = f"{slugify(summary.query)}_{stamp}"
    csv_path = RESULTS_DIR / f"{base}.csv"
    json_path = RESULTS_DIR / f"{base}.json"

    rows = _to_rows(summary.results)
    pd.DataFrame(rows).to_csv(csv_path, index=False, encoding="utf-8-sig")

    payload = {
        "query": summary.query,
        "country": summary.country,
        "country_name": summary.country_name,
        "discovery_limit": summary.discovery_limit,
        "min_active": summary.min_active,
        "ads_analyzed": summary.ads_analyzed,
        "pages_found": summary.pages_found,
        "pages_analyzed": summary.pages_analyzed,
        "pages_approved": summary.pages_approved,
        "errors": summary.errors,
        "started_at": summary.started_at.isoformat(),
        "finished_at": summary.finished_at.isoformat() if summary.finished_at else None,
        "results": [r.to_dict() for r in summary.results],
        "ignored": summary.ignored,
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return csv_path, json_path
def _list_saved_searches() -> list[dict]:
    if not RESULTS_DIR.exists():
        return []

    grouped = {}

    for file in RESULTS_DIR.iterdir():

        if not file.is_file():
            continue

        if file.suffix.lower() not in {".csv", ".json"}:
            continue

        stem = file.stem

        # Exemplo:
        # oracao_poderosa_2026-08-23_230455

        parts = stem.rsplit("_", 2)

        if len(parts) != 3:
            continue

        query_slug = parts[0]
        date_part = parts[1]
        time_part = parts[2]

        key = f"{query_slug}_{date_part}_{time_part}"

        if key not in grouped:
            grouped[key] = {
                "query_slug": query_slug,
                "date": date_part,
                "time": time_part,
                "csv": None,
                "json": None,
                "mtime": file.stat().st_mtime,
            }

        if file.suffix.lower() == ".csv":
            grouped[key]["csv"] = file

        elif file.suffix.lower() == ".json":
            grouped[key]["json"] = file

        grouped[key]["mtime"] = max(
            grouped[key]["mtime"],
            file.stat().st_mtime
        )

    searches = list(grouped.values())

    searches.sort(
        key=lambda item: item["mtime"],
        reverse=True
    )

    return searches


def _display_query_name(slug: str) -> str:
    return slug.replace("_", " ").strip()


def _display_search_date(date_part: str, time_part: str) -> str:
    try:

        dt = datetime.strptime(
            f"{date_part}_{time_part}",
            "%Y-%m-%d_%H%M%S"
        )

        return dt.strftime("%d/%m/%Y %H:%M")

    except Exception:
        return date_part

def _render_result_card(result: PageResult, rank: int) -> None:
    st.markdown("<div class='result-shell'>", unsafe_allow_html=True)

    left, main = st.columns([1, 5])

    with left:
        if result.preview_image_url:
            try:
                st.image(result.preview_image_url, use_container_width=True)
            except Exception:
                st.caption("Preview indisponível")
        elif result.profile_picture_url:
            try:
                st.image(result.profile_picture_url, use_container_width=True)
            except Exception:
                st.caption("Sem preview")
        else:
            st.caption("Sem preview")

    with main:
        count_label = f"{result.active_ads_found:,}".replace(",", ".")
        if result.count_capped:
            count_label += "+"
        cache_tag = " · cache" if result.from_cache else ""

        st.markdown(
            f"""
            <div class="result-header">
                <div class="rank-chip">#{rank:02d}</div>
                <div>
                    <div class="result-title">{result.page_name}</div>
                    <div class="micro-caption">Page ID: {result.page_id}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            f"<div class='big-count'>🔥 {count_label} anúncios ativos encontrados{cache_tag}</div>",
            unsafe_allow_html=True,
        )

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Page ID", result.page_id)
        c2.metric("Curtidas", f"{result.likes:,}".replace(",", ".") if result.likes is not None else "—")
        c3.metric("Mais antigo", f"{result.oldest_days} dias" if result.oldest_days is not None else "—")
        c4.metric("Plataformas", len(result.platforms))

        b1, b2, b3 = st.columns(3)
        if result.library_url:
            b1.link_button("Abrir na Meta Ad Library", result.library_url, use_container_width=True)
        if result.facebook_url:
            b2.link_button("Abrir página no Facebook", result.facebook_url, use_container_width=True)
        if result.sample_ads:
            sample = result.sample_ads[0]
            ad_id = sample.ad_library_id or sample.archive_id
            if ad_id:
                b3.link_button(
                    "Abrir anúncio de exemplo",
                    f"https://www.facebook.com/ads/library/?id={ad_id}",
                    use_container_width=True,
                )

        with st.expander("Ver detalhes"):
            d1, d2 = st.columns(2)
            with d1:
                st.write("**Nome da página:**", result.page_name)
                st.write("**Page ID:**", result.page_id)
                st.write("**Facebook:**", result.facebook_url or "—")
                st.write("**Verificada:**", "Sim" if result.verified else "Não" if result.verified is not None else "—")
                st.write("**Anúncio ativo mais antigo:**", result.oldest_start or "—")
                st.write("**Anúncio ativo mais recente:**", result.newest_start or "—")
            with d2:
                st.write("**Resultados ativos encontrados:**", result.active_ads_found)
                st.write("**Contagem limitada pelo teto:**", "Sim" if result.count_capped else "Não")
                st.write("**Plataformas:**", ", ".join(result.platforms) if result.platforms else "—")
                st.write("**Última verificação:**", result.last_checked or "—")
                st.write("**Interpretação:**", result.notes or "—")

            if result.sample_ads:
                st.markdown("#### IDs de anúncios de exemplo")
                samples = []
                for idx, ad in enumerate(result.sample_ads, start=1):
                    samples.append(
                        {
                            "#": idx,
                            "Archive/Ad ID": ad.archive_id,
                            "Ad Library ID": ad.ad_library_id or "",
                            "Raw Ad ID": ad.raw_ad_id or "",
                            "Ativo": ad.is_active,
                            "Início": ad.delivery_start_time or "",
                            "Collation": ad.collation_count,
                        }
                    )
                st.dataframe(pd.DataFrame(samples), use_container_width=True, hide_index=True)

                first = result.sample_ads[0]
                if first.creatives:
                    st.markdown("#### Criativo de exemplo")
                    creative = first.creatives[0]
                    if creative.title:
                        st.write("**Título:**", creative.title)
                    if creative.body:
                        st.write("**Texto:**", creative.body)
                    if creative.description:
                        st.write("**Descrição:**", creative.description)
                    if creative.cta_text:
                        st.write("**CTA:**", creative.cta_text)
                    if creative.link_url:
                        st.write("**Destino:**", creative.link_url)

    st.markdown("</div>", unsafe_allow_html=True)


st.markdown(
    """
<div class="hero-shell">
    <div class="hero-grid">
        <div>
            <div class="eyebrow">R+miner</div>
            <h1>Descubra páginas <span>que anunciam no Meta</span></h1>
            <p>
                Descubra páginas com grande volume de anúncios ativos, identifique o Page ID
                e abra o anunciante direto na Biblioteca de Anúncios.
            </p>
        </div>
        <div class="hero-visual-wrap">
            <div class="hero-gem"></div>
        </div>
    </div>
</div>
""",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown(
        """
        <div class="brand-mini">
            <div class="brand-icon"><img src="/app/static/rplusminer-logo.png" alt="Logo R+miner" /></div>
            <div>
                <div class="brand-title">R+miner</div>
                <div class="brand-sub">Meta Ads Miner</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.header("Configuração")

    query = st.text_input(
        "Palavra-chave",
        placeholder="Ex.: emagrecimento"
    )

    country_name = st.selectbox(
        "País",
        list(COUNTRIES.keys()),
        index=0
    )

    country = COUNTRIES[country_name]

    discovery_limit = st.number_input(
        "Anúncios para descoberta",
        min_value=10,
        max_value=5000,
        value=300,
        step=50,
        help="Quantidade máxima de anúncios da busca inicial usados para descobrir páginas únicas.",
    )

    preset_label = st.selectbox(
        "Mínimo de anúncios ativos",
        [f"{x}+" for x in MIN_PRESETS] + ["Personalizado"],
        index=3,
    )

    if preset_label == "Personalizado":
        min_active = st.number_input(
            "Valor personalizado",
            min_value=1,
            max_value=5000,
            value=50,
            step=1
        )
    else:
        min_active = int(
            preset_label.rstrip("+")
        )

    exact_phrase = st.checkbox(
        "Frase exata",
        value=False
    )

    use_cache = st.checkbox(
        "Usar cache (12h)",
        value=True
    )

    revalidate = st.checkbox(
        "Revalidar páginas ignorando cache",
        value=False
    )

    safety_cap = st.number_input(
        "Teto de segurança por página",
        min_value=100,
        max_value=10000,
        value=2000,
        step=100,
        help="Se uma página chegar neste teto, o resultado aparecerá com + para não fingir que o total é exato.",
    )

    mine_clicked = st.button(
        "🔎 MINERAR PÁGINAS",
        type="primary",
        use_container_width=True
    )

    st.divider()

    try:
        cache_stats = PageCache().stats()

        st.markdown(
            f"""
            <div class="sidebar-footer-box">
                <div><b>Cache local</b></div>
                <div>{cache_stats['entries']} páginas</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    except Exception:
        pass

    saved_searches = _list_saved_searches()

    st.markdown(
        """
        <div class="sidebar-footer-box">
            <div><b>Histórico local</b></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not saved_searches:
        st.caption(
            "Nenhuma pesquisa salva ainda."
        )

    else:
        for index, search in enumerate(
            saved_searches[:20]
        ):

            query_name = _display_query_name(
                search["query_slug"]
            )

            search_date = _display_search_date(
                search["date"],
                search["time"]
            )

            with st.expander(
                f"{query_name} · {search_date}",
                expanded=False
            ):

                if search["csv"]:
                    csv_data = search["csv"].read_bytes()

                    st.download_button(
                        "Baixar CSV",
                        data=csv_data,
                        file_name=search["csv"].name,
                        mime="text/csv",
                        key=f"csv_{index}",
                        use_container_width=True,
                    )

                if search["json"]:
                    json_data = search["json"].read_bytes()

                    st.download_button(
                        "Baixar JSON",
                        data=json_data,
                        file_name=search["json"].name,
                        mime="application/json",
                        key=f"json_{index}",
                        use_container_width=True,
                    )

if mine_clicked:
    if not query.strip():
        st.error("Digite uma palavra-chave antes de minerar.")
    else:
        st.session_state.summary = None
        st.session_state.live_results = []
        st.session_state.last_error = None

        status_box = st.empty()
        progress = st.progress(0.0, text="Preparando mineração...")
        metrics_box = st.empty()
        live_box = st.container()

        miner = AdsMiner(safety_cap=int(safety_cap))
        try:
            summary = None
            for event in miner.mine(
                query=query,
                country=country,
                country_name=country_name,
                discovery_limit=int(discovery_limit),
                min_active=int(min_active),
                use_cache=(use_cache and not revalidate),
                exact_phrase=exact_phrase,
            ):
                if event.kind == "discovery":
                    total = max(event.total, 1)
                    progress.progress(min(event.current / total, 1.0), text=event.message)
                    metrics_box.info(f"{event.message} · {event.extra.get('unique_pages', 0)} páginas únicas")
                elif event.kind == "discovery_done":
                    progress.progress(0.0, text="Descoberta concluída. Verificando páginas...")
                    metrics_box.success(event.message)
                elif event.kind == "page_start":
                    total = max(event.total, 1)
                    progress.progress(min(event.current / total, 1.0), text=event.message)
                    status_box.info(
                        f"Página {event.current}/{event.total}: {event.extra.get('page_name', '')} · ID {event.extra.get('page_id', '')}"
                    )
                elif event.kind in {"page_approved", "page_cached"} and event.page:
                    st.session_state.live_results.append(event.page)
                    with live_box:
                        st.success(f"🔥 {event.page.page_name} — {event.page.active_ads_found} anúncios ativos encontrados")
                elif event.kind == "page_error":
                    st.warning(event.message)
                elif event.kind == "error":
                    st.session_state.last_error = event.message
                    st.error(event.message)
                elif event.kind == "finished":
                    summary = event.extra.get("summary")

            if summary:
                st.session_state.summary = summary
                _save_exports(summary)
                progress.progress(1.0, text="Mineração finalizada")
                status_box.success("Mineração finalizada.")
        finally:
            miner.close()

summary: MinerSummary | None = st.session_state.summary

if summary:
    st.markdown("<div class='summary-shell'>", unsafe_allow_html=True)
    st.subheader("Mineração finalizada")
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Anúncios analisados", summary.ads_analyzed)
    m2.metric("Páginas encontradas", summary.pages_found)
    m3.metric("Páginas analisadas", summary.pages_analyzed)
    m4.metric("Páginas aprovadas", summary.pages_approved)
    m5.metric("Erros", summary.errors)
    st.markdown("</div>", unsafe_allow_html=True)

    if not summary.results:
        st.warning(f"Nenhuma página atingiu o mínimo de {summary.min_active} anúncios ativos encontrados.")
    else:
        st.markdown(
            """
            <div class="panel-shell">
                <div class="panel-title"><span class="dot">✦</span> Resultados da mineração</div>
                <div class="caption-note">
                    O número exibido é a quantidade de anúncios únicos retornados pela busca ACTIVE da biblioteca para aquela página.
                    Se o teto de segurança for atingido, o valor aparece com + e não é tratado como total exato.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        controls = st.columns([2, 1])
        search_results = controls[0].text_input("Pesquisar nos resultados", placeholder="Nome ou Page ID")
        sort_mode = controls[1].selectbox(
            "Ordenar",
            ["Mais anúncios primeiro", "Menos anúncios primeiro", "Anúncio mais antigo primeiro", "Mais curtidas"],
        )

        results = list(summary.results)
        term = search_results.strip().lower()
        if term:
            results = [r for r in results if term in r.page_name.lower() or term in r.page_id.lower()]

        if sort_mode == "Mais anúncios primeiro":
            results.sort(key=lambda r: r.active_ads_found, reverse=True)
        elif sort_mode == "Menos anúncios primeiro":
            results.sort(key=lambda r: r.active_ads_found)
        elif sort_mode == "Anúncio mais antigo primeiro":
            results.sort(key=lambda r: r.oldest_days if r.oldest_days is not None else -1, reverse=True)
        else:
            results.sort(key=lambda r: r.likes if r.likes is not None else -1, reverse=True)

        tab_cards, tab_table = st.tabs(["Cards", "Tabela"])
        with tab_cards:
            for rank, result in enumerate(results, start=1):
                _render_result_card(result, rank)

        with tab_table:
            st.dataframe(pd.DataFrame(_to_rows(results)), use_container_width=True, hide_index=True)

        csv_bytes = pd.DataFrame(_to_rows(summary.results)).to_csv(index=False).encode("utf-8-sig")
        json_bytes = json.dumps([r.to_dict() for r in summary.results], ensure_ascii=False, indent=2).encode("utf-8")
        d1, d2 = st.columns(2)
        d1.download_button(
            "⬇️ Baixar CSV",
            data=csv_bytes,
            file_name=f"{slugify(summary.query)}_meta_ads.csv",
            mime="text/csv",
            use_container_width=True,
        )
        d2.download_button(
            "⬇️ Baixar JSON",
            data=json_bytes,
            file_name=f"{slugify(summary.query)}_meta_ads.json",
            mime="application/json",
            use_container_width=True,
        )

st.markdown("<div class='footer-explain'>", unsafe_allow_html=True)
with st.expander("Como interpretar a contagem"):
    st.write(
        "A ferramenta procura anúncios com status ACTIVE, descobre Page IDs e depois consulta cada página individualmente. "
        "A contagem é de anúncios únicos retornados pelo collector até o fim da paginação. "
        "Se a coleta atingir o teto de segurança configurado, o resultado é marcado como limitado e deve ser lido como 'pelo menos esse valor'."
    )
st.markdown("</div>", unsafe_allow_html=True)
