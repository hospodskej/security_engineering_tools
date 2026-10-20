import os

import pytest
import yaml

import magpie.runner as runner
from magpie.models import Listing
from magpie.sources.base import Source
from magpie.state import State

CONFIG = os.path.join(os.path.dirname(__file__), "..", "config.yaml")


class FakeSource(Source):
    def __init__(self, name, listings, fail=False):
        super().__init__(None, {})
        self.name, self.listings, self.fail = name, listings, fail

    def fetch(self):
        if self.fail:
            raise IOError("site down")
        return list(self.listings)


class Recorder:
    def __init__(self, fail=False):
        self.sent, self.fail = [], fail

    def send(self, title, message, click=None, priority=4, tags=None, image=None):
        if self.fail:
            raise IOError("ntfy unreachable")
        self.sent.append({"title": title, "message": message, "click": click, "priority": priority})


def flat(id, rent=12000, locality="Teyschlova, Brno - Bystrc", source="a", title="Pronájem bytu 2+kk 50 m²"):
    return Listing(source=source, id=id, url=f"https://{source}.cz/{id}", title=title, rent=rent,
                   fees=1000, locality=locality)


@pytest.fixture
def cfg(monkeypatch):
    monkeypatch.setattr(runner, "build_sources", lambda cfg, http: cfg["_sources"])
    with open(CONFIG, encoding="utf-8") as f:
        return yaml.safe_load(f)


def run(cfg, tmp_path, sources, notifier):
    cfg["_sources"] = sources
    state = State(str(tmp_path / "state.json"))
    failures = runner.run_once(cfg, state, notifier, http=None)
    state.save()
    return failures


def test_first_run_is_quiet_then_new_flats_buzz(cfg, tmp_path):
    rec = Recorder()
    run(cfg, tmp_path, [FakeSource("a", [flat("1"), flat("2", locality="Brno - Líšeň")])], rec)
    assert [m["priority"] for m in rec.sent] == [2]  # existing match, sent quietly

    rec = Recorder()
    run(cfg, tmp_path, [FakeSource("a", [flat("1"), flat("2", locality="Brno - Líšeň"), flat("3")])], rec)
    assert [(m["click"], m["priority"]) for m in rec.sent] == [("https://a.cz/3", 4)]

    rec = Recorder()
    run(cfg, tmp_path, [FakeSource("a", [flat("1"), flat("3")])], rec)
    assert rec.sent == []


def test_price_drop_into_budget_alerts_again(cfg, tmp_path):
    run(cfg, tmp_path, [FakeSource("a", [flat("1", rent=16000)])], Recorder())
    rec = Recorder()
    run(cfg, tmp_path, [FakeSource("a", [flat("1", rent=12500)])], rec)
    assert len(rec.sent) == 1 and "price dropped from 16 000 Kč" in rec.sent[0]["message"]


def test_same_flat_on_two_sites_alerts_once(cfg, tmp_path):
    run(cfg, tmp_path, [FakeSource("a", []), FakeSource("b", [])], Recorder())  # initialise both
    rec = Recorder()
    run(cfg, tmp_path, [FakeSource("a", [flat("1")]), FakeSource("b", [flat("9", source="b")])], rec)
    assert len(rec.sent) == 1


def test_failed_notification_is_retried(cfg, tmp_path):
    run(cfg, tmp_path, [FakeSource("a", [])], Recorder())
    assert run(cfg, tmp_path, [FakeSource("a", [flat("1")])], Recorder(fail=True)) == 1
    rec = Recorder()
    run(cfg, tmp_path, [FakeSource("a", [flat("1")])], rec)
    assert len(rec.sent) == 1


def test_broken_site_warns_once_then_recovers(cfg, tmp_path):
    cfg["health"]["alert_after_failures"] = 2
    sent = []
    for _ in range(4):
        rec = Recorder()
        run(cfg, tmp_path, [FakeSource("a", [], fail=True)], rec)
        sent += rec.sent
    assert [m["title"] for m in sent] == ["magpie: a is failing"]

    rec = Recorder()
    run(cfg, tmp_path, [FakeSource("a", [flat("1")])], rec)
    assert rec.sent[0]["title"] == "magpie: a works again"


def test_notification_text():
    from magpie.notify import describe, title_for
    l = flat("1", rent=11000, locality="Součkova, Brno-Komín, Brno")
    assert title_for(l) == "New flat · 12 000 Kč · Brno-Komín"
    assert "11 000 Kč + 1 000 Kč fees = 12 000 Kč" in describe(l, [])
    l = flat("2", rent=13900, locality="Hoppova, Brno - Veveří")
    l.fees = None
    assert title_for(l) == "New flat · 13 900 Kč · Brno - Veveří"
    assert "⚠ fees not listed" in describe(l, ["fees not listed"])


def test_first_run_overflow_is_summarised(cfg, tmp_path):
    cfg["first_run_limit"] = 2
    rec = Recorder()
    run(cfg, tmp_path, [FakeSource("a", [flat(str(i), rent=12000 + i) for i in range(5)])], rec)
    assert len(rec.sent) == 3 and rec.sent[0]["title"] == "magpie: 3 more on a"
