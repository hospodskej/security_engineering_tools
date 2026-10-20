import os

import requests


def fmt_czk(value):
    return f"{value:,}".replace(",", " ") + " Kč"


def describe(listing, flags):
    lines = [listing.title]
    if listing.locality:
        lines.append(listing.locality)
    if listing.fees_included:
        lines.append(f"{fmt_czk(listing.rent)} incl. fees")
    elif listing.fees is not None:
        lines.append(f"{fmt_czk(listing.rent)} + {fmt_czk(listing.fees)} fees = {fmt_czk(listing.total)}")
    else:
        lines.append(f"{fmt_czk(listing.rent)} rent")
    for flag in flags + listing.notes:
        lines.append(f"⚠ {flag}")
    lines.append(f"via {listing.source}")
    return "\n".join(lines)


def title_for(listing):
    price = listing.total if listing.total is not None else listing.rent
    # "Street, Brno - Veveří" / "Street, Brno-Komín, Brno": the district, not a bare city name.
    parts = [p.strip() for p in listing.locality.split(",") if p.strip()]
    while len(parts) > 1 and " " not in parts[-1] and "-" not in parts[-1]:
        parts.pop()
    place = parts[-1] if parts else ""
    return " · ".join(p for p in ("New flat", fmt_czk(price), place) if p)


class Ntfy:
    """Push notifications through ntfy (https://ntfy.sh) — the phone app buzzes on each message."""

    def __init__(self, cfg):
        self.server = (os.environ.get("NTFY_SERVER") or cfg.get("server") or "https://ntfy.sh").rstrip("/")
        self.topic = os.environ.get("NTFY_TOPIC") or cfg.get("topic")
        self.token = os.environ.get("NTFY_TOKEN") or cfg.get("token")
        if not self.topic:
            raise ValueError("ntfy topic missing: set the NTFY_TOPIC environment variable")

    def send(self, title, message, click=None, priority=4, tags=None, image=None):
        payload = {"topic": self.topic, "title": title, "message": message,
                   "priority": priority, "tags": tags or []}
        if click:
            payload["click"] = click
            payload["actions"] = [{"action": "view", "label": "Open listing", "url": click}]
        if image:
            payload["attach"] = image
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        resp = requests.post(self.server, json=payload, headers=headers, timeout=20)
        resp.raise_for_status()


class Console:
    """Prints instead of sending; used for --dry-run and when no ntfy topic is configured."""

    def send(self, title, message, click=None, priority=4, tags=None, image=None):
        print(f"\n[notify p{priority}] {title}\n{message}" + (f"\n{click}" if click else ""))


def listing_alert(notifier, listing, flags, priority=4):
    notifier.send(title_for(listing), describe(listing, flags), click=listing.url,
                  priority=priority, tags=["house"], image=listing.image)
