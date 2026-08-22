#!/usr/bin/env python3
"""Scarica gli eventi del gruppo Meetup #pugMi e li scrive in docs/data/events.json.

Meetup non ha più un'API pubblica: i feed iCal e RSS del gruppo sono vuoti e in ogni
caso non hanno header CORS, quindi il browser non può leggerli. I dati stanno invece
nel blob __NEXT_DATA__ della pagina degli eventi, che una singola richiesta HTTP
restituisce completo (eventi, venue e statistiche del gruppo).

    python3 scripts/fetch_events.py          scarica e scrive il JSON
    python3 scripts/fetch_events.py --demo   self-check offline su scripts/fixture.html
"""

import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone

GROUP = "pugmilano"                                    # slug reale: milanophp è un redirect
SOURCE = f"https://www.meetup.com/{GROUP}/events/"
PUBLIC_URL = "https://www.meetup.com/it-it/milanophp/"  # l'URL che mostriamo agli utenti
OUT = os.path.join(os.path.dirname(__file__), os.pardir, "docs", "data", "events.json")
FIXTURE = os.path.join(os.path.dirname(__file__), "fixture.html")
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/126.0 Safari/537.36")
EXCERPT_LEN = 200

NEXT_DATA = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.S)


def fetch_html(url=SOURCE):
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept-Language": "it-IT,it;q=0.9"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def clean(text):
    """Ripulisce le descrizioni Meetup, che sono markdown con l'escape dei simboli.

    Nei dati reali si trovano sia sequenze di escape (\\- \\, \\. \\() sia markdown vero
    (**grassetto**, [testo](url)): per un estratto in chiaro va via tutto.
    """
    if not text:
        return ""
    text = re.sub(r"\\([^\w\s])", r"\1", text)          # \- \, \. -> - , .
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)  # [testo](url) -> testo
    text = re.sub(r"\*\*|__|~~|`", "", text)              # grassetto, barrato, codice
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.M)     # titoli markdown
    return re.sub(r"\s+", " ", text).strip()


def excerpt(text, limit=EXCERPT_LEN):
    text = clean(text)
    if len(text) <= limit:
        return text
    cut = text[:limit]
    space = cut.rfind(" ")
    return (cut[:space] if space > limit * 0.6 else cut).rstrip(" ,.;:") + "\u2026"


def parse(html):
    """Estrae il payload dal blob __NEXT_DATA__. Solleva ValueError se la pagina cambia."""
    m = NEXT_DATA.search(html)
    if not m:
        raise ValueError("__NEXT_DATA__ non trovato: Meetup ha cambiato la pagina")
    state = json.loads(m.group(1))["props"]["pageProps"].get("__APOLLO_STATE__")
    if not state:
        raise ValueError("__APOLLO_STATE__ assente nel blob __NEXT_DATA__")

    def deref(ref):
        return state.get(ref["__ref"], {}) if isinstance(ref, dict) and "__ref" in ref else {}

    groups = [v for k, v in state.items() if k.startswith("Group:")]
    group = next((g for g in groups if g.get("urlname") == GROUP), groups[0] if groups else {})
    stats = group.get("stats") or {}
    counts = stats.get("memberCounts") or {}
    ratings = stats.get("eventRatings") or {}

    now = datetime.now(timezone.utc)
    upcoming, past = [], []
    for key, ev in state.items():
        if not key.startswith("Event:") or not ev.get("dateTime"):
            continue
        # Lo status CANCELLED non è un evento passato: non va mostrato affatto.
        if ev.get("status") == "CANCELLED":
            continue
        venue = deref(ev.get("venue"))
        start = datetime.fromisoformat(ev["dateTime"])
        item = {
            "id": ev.get("id"),
            "title": clean(ev.get("title")),
            "url": ev.get("eventUrl"),
            "start": ev["dateTime"],
            "going": (ev.get("going") or {}).get("totalCount", 0),
            "online": bool(ev.get("isOnline")),
            "venue": {"name": venue.get("name", ""), "city": venue.get("city", "")},
            "excerpt": excerpt(ev.get("description")),
        }
        (upcoming if start > now else past).append(item)

    upcoming.sort(key=lambda e: e["start"])
    past.sort(key=lambda e: e["start"], reverse=True)
    if not upcoming and not past:
        raise ValueError("zero eventi estratti: struttura dei dati cambiata")

    return {
        "group": {
            "members": counts.get("all"),
            "rating": ratings.get("average"),
            "ratings_count": ratings.get("total"),
            "url": PUBLIC_URL,
        },
        "upcoming": upcoming,
        "past": past,
    }


def demo():
    with open(FIXTURE, encoding="utf-8") as f:
        data = parse(f.read())
    assert data["group"]["members"] > 1000, data["group"]
    assert data["past"], "la fixture deve contenere eventi passati"
    ev = data["past"][0]
    assert ev["title"] and ev["url"].startswith("https://"), ev
    assert datetime.fromisoformat(ev["start"]), ev
    assert not any(e["title"] == "" for e in data["past"]), "titoli vuoti"
    # nessun CANCELLED: la fixture ne contiene uno (24/06/2026) e va scartato
    assert all("off-talk" not in e["title"] for e in data["past"]), "evento annullato non filtrato"
    # né escape né markdown residuo negli estratti
    for e in data["past"]:
        assert not re.search(r"\\[^\w\s]|\*\*|__|\]\(", e["excerpt"]), e["excerpt"]
    assert len(ev["excerpt"]) <= EXCERPT_LEN + 1, len(ev["excerpt"])
    print(f"ok: {len(data['upcoming'])} upcoming, {len(data['past'])} past, "
          f"{data['group']['members']} membri")


def main():
    if "--demo" in sys.argv:
        return demo()
    data = parse(fetch_html())
    path = os.path.normpath(OUT)
    old = None
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            old = json.load(f)
            old.pop("fetched_at", None)
    if old == data:
        print("nessuna variazione")
        return
    data["fetched_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print(f"scritto {path}: {len(data['upcoming'])} upcoming, {len(data['past'])} past")


if __name__ == "__main__":
    main()
