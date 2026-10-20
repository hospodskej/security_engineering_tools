import json
import os
import time

PRUNE_AFTER = 60 * 24 * 3600  # forget listings not seen for 60 days


class State:
    """Remembers which listings were already seen, and per-source health, in a JSON file."""

    def __init__(self, path):
        self.path = path
        self.data = {"seen": {}, "sources": {}, "alerted": {}}
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                self.data.update(json.load(f))

    def source(self, name):
        return self.data["sources"].setdefault(name, {"initialized": False, "failures": 0, "alerted": False})

    def seen(self, key):
        return self.data["seen"].get(key)

    def mark(self, listing):
        now = int(time.time())
        entry = self.data["seen"].setdefault(listing.key, {"first": now})
        entry["last"] = now
        entry["rent"] = listing.rent

    def duplicate_of(self, listing):
        """Key of an already-alerted listing from another site with the same fingerprint."""
        fp = listing.fingerprint
        prior = self.data["alerted"].get(fp) if fp else None
        if prior and not prior["key"].startswith(f"{listing.source}:"):
            return prior["key"]
        return None

    def record_alert(self, listing):
        if listing.fingerprint:
            self.data["alerted"][listing.fingerprint] = {"key": listing.key, "time": int(time.time())}

    def forget(self, key):
        self.data["seen"].pop(key, None)

    def touch(self, key):
        if key in self.data["seen"]:
            self.data["seen"][key]["last"] = int(time.time())

    def save(self):
        cutoff = time.time() - PRUNE_AFTER
        self.data["seen"] = {k: v for k, v in self.data["seen"].items() if v.get("last", v["first"]) >= cutoff}
        self.data["alerted"] = {k: v for k, v in self.data["alerted"].items() if v["time"] >= cutoff}
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=1, sort_keys=True)
        os.replace(tmp, self.path)
