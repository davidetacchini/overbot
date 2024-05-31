from __future__ import annotations

from typing import TYPE_CHECKING, Any

import aiohttp

from classes.exceptions import UnknownError

from .request import Request

if TYPE_CHECKING:
    from asyncpg import Record


class Profile:
    __slots__ = (
        "id",
        "battletag",
        "record",
        "platforms",
        "session",
        "_request",
        "_data",
    )

    def __init__(
        self,
        battletag: None | str = None,
        *,
        session: aiohttp.ClientSession,
        record: None | Record = None,
    ) -> None:
        self.id: None | int = record.get("id") if record else None
        self.battletag: None | str = record.get("battletag") if record else battletag
        self.session: aiohttp.ClientSession = session
        self.platforms: tuple[str, ...] = ("pc", "console")
        self._request: None | Request = None
        self._data: dict[str, Any] = {}

    @property
    def request(self) -> Request:
        if not self._request:
            self._request = Request(battletag=self.battletag, session=self.session)  # type: ignore
        return self._request

    @property
    def username(self) -> str:
        return self._safe_get("summary.username")

    @property
    def avatar(self) -> str:
        return self._safe_get("summary.avatar", default="https://imgur.com/a/BrDrZKL")

    @property
    def namecard(self) -> None | str:
        return self._safe_get("summary.namecard")

    @property
    def title(self) -> None | str:
        return self._safe_get("summary.title", default="N/A")

    @property
    def endorsement(self) -> None | str:
        return self._safe_get("summary.endorsement.level", default="N/A")

    def _safe_get(self, path: str, /, *, default={}) -> Any:
        if "." not in path:
            return self._data.get(path)
        ret = self._data
        for key in path.split("."):
            ret = ret.get(key)
            if not ret:
                return default
        return ret

    @staticmethod
    def _list_to_dict(source: list[dict[str, Any]]) -> dict[str, Any]:
        career_stats = {}
        for item in source:
            stats = {}
            for stat in item["stats"]:
                stats[stat["key"]] = stat["value"]
            career_stats[item.pop("category")] = stats
        return career_stats

    async def fetch_data(self):
        try:
            self._data = await self.request.fetch_data()
        except aiohttp.ClientConnectionError as e:
            raise UnknownError() from e

    def get_ratings(self, *, platform: str) -> Any:
        raw_ratings = self._safe_get(f"summary.competitive.{platform}")
        if not raw_ratings:
            return

        ratings = {}
        for key, value in raw_ratings.items():
            if not value:
                continue
            elif isinstance(value, int):
                ratings[key.lower()] = value
            else:
                ratings[key.lower()] = f"**{value['division'].capitalize()} {str(value['tier'])}**"
        return ratings

    def get_stats(self, *, platform: str, hero: str) -> Any:
        q = self._safe_get(f"stats.{platform}.quickplay.career_stats.{hero}")
        q = self._list_to_dict(q)
        c = self._safe_get(f"stats.{platform}.competitive.career_stats.{hero}")
        c = self._list_to_dict(c)

        if not q and not c:
            return

        keys = list({*q, *c})
        keys.sort()

        return keys, q, c
