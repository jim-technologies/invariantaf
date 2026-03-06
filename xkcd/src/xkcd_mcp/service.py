"""XKCDService — wraps the XKCD JSON API and explainxkcd wiki into proto RPCs."""

from __future__ import annotations

import html
import random
import re
from typing import Any

import httpx

from xkcd_mcp.gen.xkcd.v1 import xkcd_pb2 as pb

_XKCD_BASE = "https://xkcd.com"
_EXPLAIN_BASE = "https://www.explainxkcd.com/wiki/api.php"


class XKCDService:
    """Implements XKCDService RPCs via the XKCD JSON API."""

    def __init__(self):
        self._http = httpx.Client(timeout=30)

    def _get_comic_json(self, num: int | None = None) -> dict:
        """Fetch a single comic's JSON. None = latest."""
        if num is None:
            url = f"{_XKCD_BASE}/info.0.json"
        else:
            url = f"{_XKCD_BASE}/{num}/info.0.json"
        resp = self._http.get(url)
        resp.raise_for_status()
        return resp.json()

    def _json_to_comic(self, data: dict) -> pb.Comic:
        """Convert raw XKCD JSON dict to a Comic proto."""
        return pb.Comic(
            num=data.get("num", 0),
            title=data.get("title", ""),
            safe_title=data.get("safe_title", ""),
            alt=data.get("alt", ""),
            img=data.get("img", ""),
            year=str(data.get("year", "")),
            month=str(data.get("month", "")),
            day=str(data.get("day", "")),
            link=data.get("link", ""),
            news=data.get("news", ""),
            transcript=data.get("transcript", ""),
        )

    def _get_latest_num(self) -> int:
        """Get the number of the latest comic."""
        data = self._get_comic_json()
        return data.get("num", 0)

    def GetLatest(self, request: Any, context: Any = None) -> pb.GetLatestResponse:
        data = self._get_comic_json()
        return pb.GetLatestResponse(comic=self._json_to_comic(data))

    def GetComic(self, request: Any, context: Any = None) -> pb.GetComicResponse:
        data = self._get_comic_json(request.num)
        return pb.GetComicResponse(comic=self._json_to_comic(data))

    def GetRandom(self, request: Any, context: Any = None) -> pb.GetRandomResponse:
        latest_num = self._get_latest_num()
        num = random.randint(1, latest_num)
        # Skip 404 — it doesn't exist (it's a joke).
        if num == 404:
            num = 405
        data = self._get_comic_json(num)
        return pb.GetRandomResponse(comic=self._json_to_comic(data))

    def GetRange(self, request: Any, context: Any = None) -> pb.GetRangeResponse:
        start = request.start_num
        end = request.end_num
        # Clamp range to max 50.
        if end - start + 1 > 50:
            end = start + 49
        resp = pb.GetRangeResponse()
        for num in range(start, end + 1):
            if num == 404:
                continue
            try:
                data = self._get_comic_json(num)
                resp.comics.append(self._json_to_comic(data))
            except Exception:
                continue
        return resp

    def SearchByTitle(self, request: Any, context: Any = None) -> pb.SearchByTitleResponse:
        query = request.query.lower()
        search_count = request.search_count or 100
        if search_count > 500:
            search_count = 500

        latest_num = self._get_latest_num()
        resp = pb.SearchByTitleResponse()

        for num in range(latest_num, max(latest_num - search_count, 0), -1):
            if num == 404:
                continue
            try:
                data = self._get_comic_json(num)
                title = data.get("title", "")
                if query in title.lower():
                    resp.comics.append(self._json_to_comic(data))
            except Exception:
                continue
        return resp

    def GetExplanation(self, request: Any, context: Any = None) -> pb.GetExplanationResponse:
        num = request.num
        url = _EXPLAIN_BASE
        params = {
            "action": "parse",
            "page": str(num),
            "format": "json",
            "prop": "wikitext",
        }
        resp = self._http.get(url, params=params)
        resp.raise_for_status()
        raw = resp.json()

        parse = raw.get("parse", {})
        title = parse.get("title", "")
        wikitext = parse.get("wikitext", {}).get("*", "")

        # Clean up wikitext: strip markup for a readable plain text explanation.
        explanation = self._clean_wikitext(wikitext)

        return pb.GetExplanationResponse(
            num=num,
            title=title,
            explanation=explanation,
            url=f"https://www.explainxkcd.com/wiki/index.php/{num}",
        )

    def _clean_wikitext(self, text: str) -> str:
        """Best-effort conversion of MediaWiki markup to plain text."""
        # Remove HTML tags.
        text = re.sub(r"<[^>]+>", "", text)
        # Remove wiki links [[target|display]] -> display, [[target]] -> target.
        text = re.sub(r"\[\[[^|\]]*\|([^\]]+)\]\]", r"\1", text)
        text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)
        # Remove external links [url text] -> text.
        text = re.sub(r"\[https?://\S+\s+([^\]]+)\]", r"\1", text)
        # Remove {{ templates }}.
        text = re.sub(r"\{\{[^}]*\}\}", "", text)
        # Remove bold/italic markers.
        text = re.sub(r"'{2,}", "", text)
        # Remove section headers == ... ==.
        text = re.sub(r"^=+\s*", "", text, flags=re.MULTILINE)
        text = re.sub(r"\s*=+\s*$", "", text, flags=re.MULTILINE)
        # Unescape HTML entities.
        text = html.unescape(text)
        # Collapse multiple blank lines.
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def GetComicCount(self, request: Any, context: Any = None) -> pb.GetComicCountResponse:
        latest_num = self._get_latest_num()
        return pb.GetComicCountResponse(count=latest_num)

    def GetMultiple(self, request: Any, context: Any = None) -> pb.GetMultipleResponse:
        nums = list(request.nums)
        if len(nums) > 50:
            nums = nums[:50]
        resp = pb.GetMultipleResponse()
        for num in nums:
            if num == 404:
                continue
            try:
                data = self._get_comic_json(num)
                resp.comics.append(self._json_to_comic(data))
            except Exception:
                continue
        return resp

    def GetRecent(self, request: Any, context: Any = None) -> pb.GetRecentResponse:
        count = request.count or 10
        if count > 50:
            count = 50

        latest_num = self._get_latest_num()
        resp = pb.GetRecentResponse()

        for num in range(latest_num, max(latest_num - count, 0), -1):
            if num == 404:
                continue
            try:
                data = self._get_comic_json(num)
                resp.comics.append(self._json_to_comic(data))
            except Exception:
                continue
        return resp

    def GetByDate(self, request: Any, context: Any = None) -> pb.GetByDateResponse:
        year = str(request.year)
        month = str(request.month)
        search_count = request.search_count or 500

        latest_num = self._get_latest_num()
        resp = pb.GetByDateResponse()

        for num in range(latest_num, max(latest_num - search_count, 0), -1):
            if num == 404:
                continue
            try:
                data = self._get_comic_json(num)
                if str(data.get("year", "")) == year and str(data.get("month", "")).lstrip("0") == month.lstrip("0"):
                    resp.comics.append(self._json_to_comic(data))
            except Exception:
                continue
        return resp
