from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .config import BASE_URL


@dataclass(frozen=True)
class Location:
    name: str
    address: str
    city: str
    state: str
    zip: str
    care_offerings: list[str]
    phone: str
    administrator: str
    source_url: str

    def to_dict(self) -> dict:
        return asdict(self)


def _detail_value(soup: BeautifulSoup, label: str):
    for dt in soup.select("dl.detail dt"):
        if dt.get_text(" ", strip=True).casefold() == label.casefold():
            return dt.find_next_sibling("dd")
    raise ValueError(f"Missing {label!r} on {soup.title.string if soup.title else 'page'}")


def scrape_locations(session: requests.Session | None = None) -> list[dict]:
    session = session or requests.Session()
    links: list[str] = []
    page = 1
    while True:
        response = session.get(f"{BASE_URL}/communities", params={"page": page}, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        links.extend(urljoin(BASE_URL, a["href"]) for a in soup.select(".card h3 a[href]"))
        next_link = soup.select_one('.pager a[href*="page="]:last-of-type')
        if not next_link or "Next" not in next_link.get_text(" ", strip=True):
            break
        page += 1

    locations: list[dict] = []
    for url in dict.fromkeys(links):
        response = session.get(url, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        address_dd = _detail_value(soup, "Address")
        address_parts = [part.strip() for part in address_dd.stripped_strings]
        city_match = re.fullmatch(r"(.+),\s*([A-Z]{2})\s+(\d{5}(?:-\d{4})?)", address_parts[-1])
        if not city_match:
            raise ValueError(f"Could not parse city/state/zip on {url}: {address_parts}")
        care = [x.get_text(" ", strip=True) for x in _detail_value(soup, "Care Offerings").select(".badge")]
        location = Location(
            name=soup.select_one(".wrap h1").get_text(" ", strip=True),
            address=" ".join(address_parts[:-1]),
            city=city_match.group(1),
            state=city_match.group(2),
            zip=city_match.group(3),
            care_offerings=care,
            phone=_detail_value(soup, "Phone").get_text(" ", strip=True),
            administrator=_detail_value(soup, "Administrator").get_text(" ", strip=True),
            source_url=url,
        )
        locations.append(location.to_dict())
    return locations

