from .bazos import Bazos
from .idnes import Idnes
from .realitymix import Realitymix

SOURCES = {cls.name: cls for cls in (Idnes, Realitymix, Bazos)}


def build_sources(cfg, http):
    built = []
    for name, opts in (cfg.get("sources") or {}).items():
        opts = opts or {}
        if not opts.get("enabled", True):
            continue
        if name not in SOURCES:
            raise ValueError(f"unknown source '{name}' (known: {', '.join(SOURCES)})")
        built.append(SOURCES[name](http, opts))
    return built
