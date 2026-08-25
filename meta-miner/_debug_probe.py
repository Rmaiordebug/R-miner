"""Temporary empirical probe of the installed meta-ads-collector 1.4.0."""

from __future__ import annotations

import traceback
from collections import defaultdict

from meta_ads_collector import MetaAdsCollector


def summarize_ad(ad, i: int) -> None:
    page = ad.page
    print(f"\n--- ad[{i}] ---")
    print("type:", type(ad).__name__)
    print("id:", ad.id)
    print("ad_library_id:", ad.ad_library_id)
    print("is_active:", ad.is_active)
    print("ad_status:", ad.ad_status)
    print("delivery_start_time:", ad.delivery_start_time)
    print("delivery_stop_time:", ad.delivery_stop_time)
    print("snapshot_url:", ad.snapshot_url)
    print("ad_snapshot_url:", ad.ad_snapshot_url)
    print("collation_id:", ad.collation_id)
    print("collation_count:", ad.collation_count)
    print("publisher_platforms:", ad.publisher_platforms)
    if page:
        print("page.id:", page.id)
        print("page.name:", page.name)
        print("page.page_url:", page.page_url)
        print("page.likes:", page.likes)
        print("page.verified:", page.verified)
    else:
        print("page: None")
    print("creatives:", len(ad.creatives))
    if ad.creatives:
        c = ad.creatives[0]
        print("  title:", (c.title or "")[:80])
        print("  image_url set:", bool(c.image_url))
        print("  thumbnail_url set:", bool(c.thumbnail_url))
        print("  video_url set:", bool(c.video_url))
        print("  cta_text:", c.cta_text)


def main() -> None:
    collector = MetaAdsCollector(rate_limit_delay=2.0, jitter=0.5)

    print("=" * 60)
    print("PROBE 1: keyword search max_results=12 status=ACTIVE country=BR")
    print("=" * 60)

    ads = []
    pages = {}
    collation_values = []
    inactive_in_active_search = 0
    stop_in_past_but_active = 0

    try:
        for i, ad in enumerate(
            collector.search(
                query="emagrecimento",
                country="BR",
                status=MetaAdsCollector.STATUS_ACTIVE,
                max_results=12,
                page_size=10,
            )
        ):
            ads.append(ad)
            if ad.page and ad.page.id:
                pages[ad.page.id] = ad.page
            collation_values.append(ad.collation_count)
            if ad.is_active is False:
                inactive_in_active_search += 1
            if i < 3:
                summarize_ad(ad, i)
    except Exception:
        traceback.print_exc()
        return

    print("\nCollected:", len(ads))
    print("Unique pages:", len(pages))
    print("collation_count samples:", collation_values)
    print("is_active False while ACTIVE search:", inactive_in_active_search)
    print("ads_collected stats:", collector.get_stats().get("ads_collected"))
    print("pages_fetched stats:", collector.get_stats().get("pages_fetched"))

    if not pages:
        print("No pages found; aborting page probe.")
        return

    page_id, page = next(iter(pages.items()))
    print("\n" + "=" * 60)
    print("PROBE 2: collect_by_page_id max_results=8")
    print("page:", page.name, page_id)
    print("=" * 60)

    page_ads = []
    try:
        for i, ad in enumerate(
            collector.collect_by_page_id(
                page_id,
                country="BR",
                status=MetaAdsCollector.STATUS_ACTIVE,
                max_results=8,
                page_size=10,
            )
        ):
            page_ads.append(ad)
            if i == 0:
                summarize_ad(ad, 0)
            if ad.page:
                print(f"  [{i}] id={ad.id} page={ad.page.id} active={ad.is_active} collation={ad.collation_count}")
            else:
                print(f"  [{i}] id={ad.id} page=None")
    except Exception:
        traceback.print_exc()

    print("page ads collected with max_results=8:", len(page_ads))
    print("all from same page?", all((a.page and a.page.id == page_id) for a in page_ads))

    print("\n" + "=" * 60)
    print("PROBE 3: qualify-style stop at 3 ads")
    print("=" * 60)
    count = 0
    try:
        for ad in collector.collect_by_page_id(
            page_id,
            country="BR",
            status=MetaAdsCollector.STATUS_ACTIVE,
            max_results=3,
            page_size=10,
        ):
            if ad.is_active is False:
                continue
            count += 1
        print("counted with max_results=3:", count)
    except Exception:
        traceback.print_exc()

    print("\nDONE")
    collector.close()


if __name__ == "__main__":
    main()
