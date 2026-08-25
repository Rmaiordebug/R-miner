"""Dump GraphQL page_info keys to see if a total exists."""
import json
from meta_ads_collector import MetaAdsCollector
from meta_ads_collector.constants import SEARCH_PAGE, STATUS_ACTIVE

c = MetaAdsCollector(rate_limit_delay=1.5, jitter=0.3)
client = c.client
resp, cursor = client.search_ads(
    query="emagrecimento",
    country="BR",
    active_status=STATUS_ACTIVE,
    first=5,
)
print("top keys", list(resp.keys()))
print("page_info", resp.get("page_info"))
print("ads", len(resp.get("ads") or []))
raw = resp.get("raw") or {}
data = raw.get("data") or {}
print("data keys", list(data.keys()))
main = data.get("ad_library_main") or data.get("adLibraryMain") or {}
print("ad_library_main keys", list(main.keys())[:40])
conn = main.get("search_results_connection") or main.get("searchResultsConnection") or {}
print("connection keys", list(conn.keys()) if isinstance(conn, dict) else type(conn))
if isinstance(conn, dict):
    for k, v in conn.items():
        if k in ("edges", "page_info", "pageInfo"):
            continue
        print(f"  extra {k}: {str(v)[:200]}")
    pi = conn.get("page_info") or conn.get("pageInfo") or {}
    print("page_info full", pi)

# page search
pid = None
if resp.get("ads"):
    ad0 = resp["ads"][0]
    pid = ad0.get("page_id") or (ad0.get("page") or {}).get("id")
    print("sample ad keys", sorted(ad0.keys())[:50])
    print("collation_count", ad0.get("collation_count") or ad0.get("collationCount"))
    print("is_active", ad0.get("is_active") or ad0.get("isActive"))

if pid:
    print("\nPAGE SEARCH page_id", pid)
    resp2, cursor2 = client.search_ads(
        query="",
        country="BR",
        active_status=STATUS_ACTIVE,
        search_type=SEARCH_PAGE,
        page_ids=[str(pid)],
        first=5,
    )
    print("page page_info", resp2.get("page_info"))
    print("page ads", len(resp2.get("ads") or []))
    raw2 = resp2.get("raw") or {}
    main2 = (raw2.get("data") or {}).get("ad_library_main") or {}
    conn2 = main2.get("search_results_connection") or {}
    print("page connection keys", list(conn2.keys()) if isinstance(conn2, dict) else conn2)
    if isinstance(conn2, dict):
        for k, v in conn2.items():
            if k in ("edges",):
                print("  edges len", len(v) if isinstance(v, list) else v)
                continue
            print(f"  {k}: {str(v)[:300]}")

c.close()
