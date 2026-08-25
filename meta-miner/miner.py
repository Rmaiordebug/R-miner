"""Mining engine: discover pages, then count ACTIVE ads per page_id."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from datetime import datetime, timezone
from typing import Any

from meta_ads_collector import MetaAdsCollector
from meta_ads_collector.exceptions import MetaAdsError, RateLimitError, SessionExpiredError

from database import PageCache
from models import AdSample, CreativeSnapshot, MinerEvent, MinerSummary, PageResult
from utils import (
    build_library_url,
    days_running,
    format_date,
    is_counted_active,
    iso_or_none,
    parse_datetime,
    retry_call,
    setup_logging,
)

logger = setup_logging()

SAMPLE_LIMIT = 12
CREATIVE_LIMIT = 3
DEFAULT_SAFETY_CAP = 2000
RETRY_WAITS = (2.0, 5.0, 10.0)


def _raw(ad: Any) -> dict[str, Any]:
    return getattr(ad, "raw_data", None) or {}


def _unique_platforms(values: list[str] | None) -> list[str]:
    seen: list[str] = []
    for item in values or []:
        text = str(item).strip()
        if text and text not in seen:
            seen.append(text)
    return seen


def _creative_from_obj(creative: Any) -> CreativeSnapshot:
    return CreativeSnapshot(
        body=getattr(creative, "body", None),
        title=getattr(creative, "title", None),
        description=getattr(creative, "description", None),
        link_url=getattr(creative, "link_url", None),
        image_url=getattr(creative, "image_url", None),
        video_url=getattr(creative, "video_url", None),
        thumbnail_url=getattr(creative, "thumbnail_url", None),
        cta_text=getattr(creative, "cta_text", None),
        cta_type=getattr(creative, "cta_type", None),
    )


def _ad_sample(ad: Any) -> AdSample:
    raw = _raw(ad)
    raw_ad_id = raw.get("ad_id")
    if raw_ad_id is not None:
        raw_ad_id = str(raw_ad_id)
    archive_id = str(getattr(ad, "id", "") or raw.get("ad_archive_id") or "")
    creatives = [_creative_from_obj(c) for c in (getattr(ad, "creatives", None) or [])[:CREATIVE_LIMIT]]
    start = getattr(ad, "delivery_start_time", None)
    stop = getattr(ad, "delivery_stop_time", None)
    return AdSample(
        archive_id=archive_id,
        ad_library_id=getattr(ad, "ad_library_id", None),
        raw_ad_id=raw_ad_id,
        is_active=getattr(ad, "is_active", None),
        delivery_start_time=iso_or_none(parse_datetime(start) if not isinstance(start, datetime) else start),
        delivery_stop_time=iso_or_none(parse_datetime(stop) if not isinstance(stop, datetime) else stop),
        publisher_platforms=_unique_platforms(getattr(ad, "publisher_platforms", None)),
        snapshot_url=getattr(ad, "snapshot_url", None),
        ad_snapshot_url=getattr(ad, "ad_snapshot_url", None),
        collation_count=getattr(ad, "collation_count", None),
        creatives=creatives,
    )


def _page_seed(ad: Any) -> dict[str, Any] | None:
    page = getattr(ad, "page", None)
    if not page or not getattr(page, "id", None):
        return None
    return {
        "page_id": str(page.id),
        "page_name": page.name or "(sem nome)",
        "page_url": page.page_url,
        "likes": page.likes,
        "verified": page.verified,
        "profile_picture_url": page.profile_picture_url,
    }


def _preview_url(sample: AdSample) -> str | None:
    for creative in sample.creatives:
        if creative.image_url:
            return creative.image_url
        if creative.thumbnail_url:
            return creative.thumbnail_url
    return None


def _build_page_result(
    *,
    seed: dict[str, Any],
    country: str,
    count: int,
    capped: bool,
    samples: list[AdSample],
    platforms: list[str],
    starts: list[datetime],
    from_cache: bool = False,
) -> PageResult:
    oldest = min(starts) if starts else None
    newest = max(starts) if starts else None
    facebook_url = seed.get("page_url")
    return PageResult(
        page_id=seed["page_id"],
        page_name=seed["page_name"],
        page_url=facebook_url,
        likes=seed.get("likes"),
        verified=seed.get("verified"),
        profile_picture_url=seed.get("profile_picture_url"),
        active_ads_found=count,
        count_capped=capped,
        from_cache=from_cache,
        oldest_start=format_date(oldest),
        newest_start=format_date(newest),
        oldest_days=days_running(oldest),
        newest_days=days_running(newest),
        platforms=platforms,
        library_url=build_library_url(seed["page_id"], country),
        facebook_url=facebook_url,
        sample_ads=samples,
        preview_image_url=_preview_url(samples[0]) if samples else None,
        last_checked=datetime.now(timezone.utc).isoformat(),
        notes=(
            "Contagem limitada pelo teto de segurança da coleta."
            if capped
            else "Contagem = anúncios únicos retornados pela busca ACTIVE até o fim da paginação."
        ),
    )


class AdsMiner:
    def __init__(
        self,
        cache: PageCache | None = None,
        rate_limit_delay: float = 2.0,
        jitter: float = 0.8,
        page_size: int = 30,
        safety_cap: int = DEFAULT_SAFETY_CAP,
    ):
        self.cache = cache or PageCache()
        self.page_size = page_size
        self.safety_cap = safety_cap
        self.collector = MetaAdsCollector(rate_limit_delay=rate_limit_delay, jitter=jitter)

    def close(self) -> None:
        try:
            self.collector.close()
        except Exception:
            pass

    def _collect_page_ads(self, page_id: str, country: str, max_results: int | None) -> list[Any]:
        def _run() -> list[Any]:
            ads: list[Any] = []
            seen: set[str] = set()
            for ad in self.collector.collect_by_page_id(
                page_id,
                country=country,
                status=MetaAdsCollector.STATUS_ACTIVE,
                max_results=max_results,
                page_size=self.page_size,
            ):
                ad_id = str(getattr(ad, "id", "") or "")
                if not ad_id or ad_id in seen:
                    continue
                if not is_counted_active(getattr(ad, "is_active", None)):
                    continue
                seen.add(ad_id)
                ads.append(ad)
            return ads

        return retry_call(
            _run,
            attempts=3,
            waits=RETRY_WAITS,
            logger=logger,
            label=f"coleta page_id={page_id}",
        )

    def inspect_page(
        self,
        seed: dict[str, Any],
        country: str,
        min_active: int,
        use_cache: bool = True,
    ) -> tuple[PageResult | None, str]:
        """Return (result, status) where status is approved/rejected/error/cached."""
        page_id = seed["page_id"]
        if use_cache:
            cached = self.cache.get(page_id, country)
            if cached:
                cached.from_cache = True
                if cached.active_ads_found >= min_active:
                    return cached, "cached"
                return None, "cached_rejected"

        try:
            # One pass: reject as soon as pagination ends below the minimum;
            # if the minimum is reached, keep going until pagination ends (or cap).
            # This avoids a second full collect_by_page_id for approved pages.
            def _run() -> list[Any]:
                ads: list[Any] = []
                seen: set[str] = set()
                qualified = False
                for ad in self.collector.collect_by_page_id(
                    page_id,
                    country=country,
                    status=MetaAdsCollector.STATUS_ACTIVE,
                    max_results=self.safety_cap,
                    page_size=self.page_size,
                ):
                    ad_id = str(getattr(ad, "id", "") or "")
                    if not ad_id or ad_id in seen:
                        continue
                    if not is_counted_active(getattr(ad, "is_active", None)):
                        continue
                    seen.add(ad_id)
                    ads.append(ad)
                    if not qualified and len(ads) >= min_active:
                        qualified = True
                        logger.info("  Teste rápido: %s+", len(ads))
                        logger.info("  QUALIFICADA")
                        logger.info("  Contagem completa...")
                return ads

            ads = retry_call(
                _run,
                attempts=3,
                waits=RETRY_WAITS,
                logger=logger,
                label=f"coleta page_id={page_id}",
            )
            if len(ads) < min_active:
                logger.info("  Teste rápido: %s anúncios", len(ads))
                logger.info("  REJEITADA")
                if ads:
                    result = self._result_from_ads(seed, country, ads, capped=False)
                    self.cache.put(country, result)
                return None, "rejected"

            capped = len(ads) >= self.safety_cap
            result = self._result_from_ads(seed, country, ads, capped=capped)
            self.cache.put(country, result)
            logger.info("  %s anúncios encontrados%s", result.active_ads_found, " (teto)" if capped else "")
            logger.info("  APROVADA")
            return result, "approved"
        except (RateLimitError, SessionExpiredError, MetaAdsError, Exception) as exc:
            logger.error("  Erro na página %s (%s): %s", seed.get("page_name"), page_id, exc)
            logger.exception("page inspect failed")
            return None, "error"

    def _result_from_ads(
        self,
        seed: dict[str, Any],
        country: str,
        ads: list[Any],
        capped: bool,
    ) -> PageResult:
        samples: list[AdSample] = []
        platforms: list[str] = []
        starts: list[datetime] = []
        updated_seed = dict(seed)
        for ad in ads:
            fresh = _page_seed(ad)
            if fresh:
                updated_seed.update({k: v for k, v in fresh.items() if v not in (None, "")})
                updated_seed["page_id"] = seed["page_id"]
            sample = _ad_sample(ad)
            if len(samples) < SAMPLE_LIMIT:
                samples.append(sample)
            for plat in sample.publisher_platforms:
                if plat not in platforms:
                    platforms.append(plat)
            start = getattr(ad, "delivery_start_time", None)
            parsed = start if isinstance(start, datetime) else parse_datetime(start)
            if parsed:
                starts.append(parsed)
        return _build_page_result(
            seed=updated_seed,
            country=country,
            count=len(ads),
            capped=capped,
            samples=samples,
            platforms=platforms,
            starts=starts,
        )

    def mine(
        self,
        query: str,
        country: str,
        country_name: str,
        discovery_limit: int,
        min_active: int,
        use_cache: bool = True,
        exact_phrase: bool = False,
    ) -> Iterator[MinerEvent]:
        query = (query or "").strip()
        country = country.upper()
        summary = MinerSummary(
            query=query,
            country=country,
            country_name=country_name,
            discovery_limit=discovery_limit,
            min_active=min_active,
            ads_analyzed=0,
            pages_found=0,
            pages_analyzed=0,
            pages_approved=0,
            started_at=datetime.now(timezone.utc),
        )

        logger.info("")
        logger.info("=" * 37)
        logger.info("META ADS MINER")
        logger.info("QUERY: %s", query)
        logger.info("COUNTRY: %s", country)
        logger.info("DISCOVERY LIMIT: %s", discovery_limit)
        logger.info("MIN ACTIVE ADS: %s", min_active)
        logger.info("=" * 37)
        logger.info("Buscando anúncios...")

        yield MinerEvent("status", "Encontrando anúncios...", extra={"stage": "discovery"})

        search_type = (
            MetaAdsCollector.SEARCH_EXACT if exact_phrase else MetaAdsCollector.SEARCH_KEYWORD
        )
        pages: dict[str, dict[str, Any]] = {}
        ads_seen = 0

        try:
            for ad in self.collector.search(
                query=query,
                country=country,
                status=MetaAdsCollector.STATUS_ACTIVE,
                search_type=search_type,
                max_results=discovery_limit,
                page_size=self.page_size,
            ):
                ads_seen += 1
                seed = _page_seed(ad)
                if seed:
                    pages.setdefault(seed["page_id"], seed)
                if ads_seen == 1 or ads_seen % 10 == 0 or ads_seen >= discovery_limit:
                    yield MinerEvent(
                        "discovery",
                        f"{ads_seen} anúncios analisados",
                        current=ads_seen,
                        total=discovery_limit,
                        extra={"unique_pages": len(pages)},
                    )
        except Exception as exc:
            logger.error("Falha na descoberta: %s", exc)
            logger.exception("discovery failed")
            yield MinerEvent("error", f"Falha na busca inicial: {exc}")
            yield MinerEvent("finished", extra={"summary": summary})
            return

        summary.ads_analyzed = ads_seen
        summary.pages_found = len(pages)
        logger.info("%s anúncios coletados", ads_seen)
        logger.info("%s páginas únicas encontradas", len(pages))
        logger.info("=" * 37)

        yield MinerEvent(
            "discovery_done",
            f"{len(pages)} páginas únicas encontradas",
            current=ads_seen,
            total=discovery_limit,
            extra={"unique_pages": len(pages)},
        )

        page_items = list(pages.values())
        total_pages = len(page_items)

        for index, seed in enumerate(page_items, start=1):
            logger.info("")
            logger.info("[%s/%s]", index, total_pages)
            logger.info("%s", seed["page_name"])
            logger.info("Page ID: %s", seed["page_id"])
            yield MinerEvent(
                "page_start",
                f"Verificando {seed['page_name']}",
                current=index,
                total=total_pages,
                extra={"page_name": seed["page_name"], "page_id": seed["page_id"]},
            )
            result, status = self.inspect_page(seed, country, min_active, use_cache=use_cache)
            summary.pages_analyzed += 1
            if status == "error":
                summary.errors += 1
                summary.ignored.append({"page_id": seed["page_id"], "page_name": seed["page_name"], "reason": "error"})
                yield MinerEvent(
                    "page_error",
                    "Página ignorada após falha.",
                    current=index,
                    total=total_pages,
                    extra=seed,
                )
                logger.info("  Página ignorada.")
                logger.info("-" * 37)
                continue
            if status in {"rejected", "cached_rejected"}:
                summary.ignored.append(
                    {
                        "page_id": seed["page_id"],
                        "page_name": seed["page_name"],
                        "reason": status,
                    }
                )
                yield MinerEvent(
                    "page_rejected",
                    f"{seed['page_name']} abaixo do mínimo",
                    current=index,
                    total=total_pages,
                    extra=seed,
                )
                logger.info("-" * 37)
                continue
            if result:
                summary.pages_approved += 1
                summary.results.append(result)
                summary.results.sort(key=lambda item: item.active_ads_found, reverse=True)
                kind = "page_cached" if status == "cached" else "page_approved"
                logger.info("-" * 37)
                yield MinerEvent(
                    kind,
                    f"{result.page_name} — {result.active_ads_found} anúncios ativos encontrados",
                    current=index,
                    total=total_pages,
                    page=result,
                    extra={"approved": summary.pages_approved},
                )

        summary.finished_at = datetime.now(timezone.utc)
        summary.results.sort(key=lambda item: item.active_ads_found, reverse=True)
        logger.info("")
        logger.info("MINERAÇÃO FINALIZADA")
        logger.info("Páginas analisadas: %s", summary.pages_analyzed)
        logger.info("Páginas aprovadas: %s", summary.pages_approved)
        yield MinerEvent("finished", "Mineração finalizada", extra={"summary": summary})
