"""Helpers for Meta Ads Miner."""

from __future__ import annotations

import logging
import re
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, TypeVar
from urllib.parse import quote, urlencode

ROOT = Path(__file__).resolve().parent
RESULTS_DIR = ROOT / "results"
LOGS_DIR = ROOT / "logs"
DATA_DIR = ROOT / "data"

COUNTRIES = {
    "Brasil": "BR",
    "Portugal": "PT",
    "Estados Unidos": "US",
    "México": "MX",
    "Argentina": "AR",
    "Espanha": "ES",
    "Reino Unido": "GB",
    "Alemanha": "DE",
    "França": "FR",
    "Itália": "IT",
    "Canadá": "CA",
    "Austrália": "AU",
    "Colômbia": "CO",
    "Chile": "CL",
    "Peru": "PE",
}

MIN_PRESETS = [10, 20, 30, 50, 75, 100, 150, 200, 300, 500]

T = TypeVar("T")


def ensure_dirs() -> None:
    for path in (RESULTS_DIR, LOGS_DIR, DATA_DIR):
        path.mkdir(parents=True, exist_ok=True)


def setup_logging() -> logging.Logger:
    ensure_dirs()
    logger = logging.getLogger("meta_ads_miner")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    error_handler = logging.FileHandler(LOGS_DIR / "errors.log", encoding="utf-8")
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(logging.Formatter("%(message)s"))

    logger.addHandler(error_handler)
    logger.addHandler(stream_handler)
    logger.propagate = False
    return logger


def slugify(text: str, max_len: int = 40) -> str:
    normalized = unicodedata.normalize("NFKD", text or "")
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", ascii_text).strip("_").lower()
    return (slug or "mineracao")[:max_len]


def parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def format_date(value: datetime | None) -> str:
    if not value:
        return "—"
    return value.astimezone(timezone.utc).strftime("%d/%m/%Y")


def days_running(value: datetime | None, now: datetime | None = None) -> int | None:
    if not value:
        return None
    current = now or datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    delta = current - value
    return max(delta.days, 0)


def iso_or_none(value: datetime | None) -> str | None:
    if not value:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def build_library_url(page_id: str, country: str = "BR") -> str:
    """Meta Ad Library URL filtered by page, using view_all_page_id.

    This query parameter is the one documented and parsed by
    meta_ads_collector.url_parser (not an invented path).
    """
    params = {
        "active_status": "active",
        "ad_type": "all",
        "country": (country or "BR").upper(),
        "is_targeted_country": "false",
        "media_type": "all",
        "search_type": "page",
        "view_all_page_id": str(page_id),
    }
    return "https://www.facebook.com/ads/library/?" + urlencode(params)


def build_ad_archive_url(ad_archive_id: str) -> str:
    return "https://www.facebook.com/ads/library/?id=" + quote(str(ad_archive_id))


def is_counted_active(is_active: bool | None) -> bool:
    """Count ads from an ACTIVE search unless explicitly marked inactive."""
    return is_active is not False


def retry_call(
    fn: Callable[[], T],
    *,
    attempts: int = 3,
    waits: tuple[float, ...] = (2.0, 5.0, 10.0),
    logger: logging.Logger | None = None,
    label: str = "operação",
) -> T:
    last_error: Exception | None = None
    for i in range(attempts):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - we must keep mining going
            last_error = exc
            wait = waits[i] if i < len(waits) else waits[-1]
            if logger:
                logger.warning("%s falhou (%s). Tentativa %s/%s. Esperando %ss.", label, exc, i + 1, attempts, wait)
            if i < attempts - 1:
                time.sleep(wait)
    assert last_error is not None
    raise last_error
