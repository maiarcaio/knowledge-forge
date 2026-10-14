from dataclasses import dataclass
from urllib.parse import parse_qs, urlencode, urlparse


@dataclass(frozen=True)
class CanonicalUrl:
    canonical_url: str
    platform: str
    external_id: str | None


def canonicalize_url(value: str) -> CanonicalUrl:
    parsed = urlparse(value.strip())
    host = parsed.netloc.lower().removeprefix("www.")

    if host in {"youtube.com", "m.youtube.com"} and parsed.path == "/watch":
        video_id = parse_qs(parsed.query).get("v", [None])[0]
        if video_id:
            return CanonicalUrl(
                canonical_url=f"https://www.youtube.com/watch?{urlencode({'v': video_id})}",
                platform="youtube",
                external_id=video_id,
            )

    if host == "youtu.be" and parsed.path.strip("/"):
        video_id = parsed.path.strip("/")
        return CanonicalUrl(
            canonical_url=f"https://www.youtube.com/watch?{urlencode({'v': video_id})}",
            platform="youtube",
            external_id=video_id,
        )

    if host in {"instagram.com", "instagr.am"}:
        segments = [segment for segment in parsed.path.split("/") if segment]
        external_id = segments[1] if len(segments) > 1 and segments[0] in {"p", "reel", "reels"} else None
        return CanonicalUrl(
            canonical_url=f"https://www.instagram.com/{'/'.join(segments)}/" if segments else "https://www.instagram.com/",
            platform="instagram",
            external_id=external_id,
        )

    return CanonicalUrl(
        canonical_url=parsed._replace(query="", fragment="").geturl(),
        platform="web",
        external_id=None,
    )
