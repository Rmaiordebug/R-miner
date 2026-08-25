"""Internal data models for Meta Ads Miner."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class CreativeSnapshot:
    body: str | None = None
    title: str | None = None
    description: str | None = None
    link_url: str | None = None
    image_url: str | None = None
    video_url: str | None = None
    thumbnail_url: str | None = None
    cta_text: str | None = None
    cta_type: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> CreativeSnapshot:
        data = data or {}
        return cls(
            body=data.get("body"),
            title=data.get("title"),
            description=data.get("description"),
            link_url=data.get("link_url"),
            image_url=data.get("image_url"),
            video_url=data.get("video_url"),
            thumbnail_url=data.get("thumbnail_url"),
            cta_text=data.get("cta_text"),
            cta_type=data.get("cta_type"),
        )


@dataclass
class AdSample:
    archive_id: str
    ad_library_id: str | None = None
    raw_ad_id: str | None = None
    is_active: bool | None = None
    delivery_start_time: str | None = None
    delivery_stop_time: str | None = None
    publisher_platforms: list[str] = field(default_factory=list)
    snapshot_url: str | None = None
    ad_snapshot_url: str | None = None
    collation_count: int | None = None
    creatives: list[CreativeSnapshot] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "archive_id": self.archive_id,
            "ad_library_id": self.ad_library_id,
            "raw_ad_id": self.raw_ad_id,
            "is_active": self.is_active,
            "delivery_start_time": self.delivery_start_time,
            "delivery_stop_time": self.delivery_stop_time,
            "publisher_platforms": self.publisher_platforms,
            "snapshot_url": self.snapshot_url,
            "ad_snapshot_url": self.ad_snapshot_url,
            "collation_count": self.collation_count,
            "creatives": [c.to_dict() for c in self.creatives],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AdSample:
        return cls(
            archive_id=str(data.get("archive_id") or data.get("id") or ""),
            ad_library_id=data.get("ad_library_id"),
            raw_ad_id=data.get("raw_ad_id"),
            is_active=data.get("is_active"),
            delivery_start_time=data.get("delivery_start_time"),
            delivery_stop_time=data.get("delivery_stop_time"),
            publisher_platforms=list(data.get("publisher_platforms") or []),
            snapshot_url=data.get("snapshot_url"),
            ad_snapshot_url=data.get("ad_snapshot_url"),
            collation_count=data.get("collation_count"),
            creatives=[CreativeSnapshot.from_dict(c) for c in (data.get("creatives") or [])],
        )


@dataclass
class PageResult:
    page_id: str
    page_name: str
    page_url: str | None = None
    likes: int | None = None
    verified: bool | None = None
    profile_picture_url: str | None = None
    active_ads_found: int = 0
    count_capped: bool = False
    from_cache: bool = False
    oldest_start: str | None = None
    newest_start: str | None = None
    oldest_days: int | None = None
    newest_days: int | None = None
    platforms: list[str] = field(default_factory=list)
    library_url: str = ""
    facebook_url: str | None = None
    sample_ads: list[AdSample] = field(default_factory=list)
    preview_image_url: str | None = None
    last_checked: str | None = None
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "page_id": self.page_id,
            "page_name": self.page_name,
            "page_url": self.page_url,
            "likes": self.likes,
            "verified": self.verified,
            "profile_picture_url": self.profile_picture_url,
            "active_ads_found": self.active_ads_found,
            "count_capped": self.count_capped,
            "from_cache": self.from_cache,
            "oldest_start": self.oldest_start,
            "newest_start": self.newest_start,
            "oldest_days": self.oldest_days,
            "newest_days": self.newest_days,
            "platforms": self.platforms,
            "library_url": self.library_url,
            "facebook_url": self.facebook_url,
            "sample_ads": [a.to_dict() for a in self.sample_ads],
            "preview_image_url": self.preview_image_url,
            "last_checked": self.last_checked,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PageResult:
        return cls(
            page_id=str(data.get("page_id") or ""),
            page_name=str(data.get("page_name") or ""),
            page_url=data.get("page_url"),
            likes=data.get("likes"),
            verified=data.get("verified"),
            profile_picture_url=data.get("profile_picture_url"),
            active_ads_found=int(data.get("active_ads_found") or 0),
            count_capped=bool(data.get("count_capped")),
            from_cache=bool(data.get("from_cache")),
            oldest_start=data.get("oldest_start"),
            newest_start=data.get("newest_start"),
            oldest_days=data.get("oldest_days"),
            newest_days=data.get("newest_days"),
            platforms=list(data.get("platforms") or []),
            library_url=str(data.get("library_url") or ""),
            facebook_url=data.get("facebook_url"),
            sample_ads=[AdSample.from_dict(a) for a in (data.get("sample_ads") or [])],
            preview_image_url=data.get("preview_image_url"),
            last_checked=data.get("last_checked"),
            notes=str(data.get("notes") or ""),
        )


@dataclass
class MinerEvent:
    kind: str
    message: str = ""
    current: int = 0
    total: int = 0
    page: PageResult | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class MinerSummary:
    query: str
    country: str
    country_name: str
    discovery_limit: int
    min_active: int
    ads_analyzed: int
    pages_found: int
    pages_analyzed: int
    pages_approved: int
    started_at: datetime
    finished_at: datetime | None = None
    errors: int = 0
    results: list[PageResult] = field(default_factory=list)
    ignored: list[dict[str, Any]] = field(default_factory=list)
