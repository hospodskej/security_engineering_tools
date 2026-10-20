import argparse
import os
import sys
import time

import yaml

from magpie.http import Http
from magpie.notify import Console, Ntfy
from magpie.runner import run_once
from magpie.state import State

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    parser = argparse.ArgumentParser(description="magpie: get a push notification when a matching flat is listed")
    parser.add_argument("--config", default=os.path.join(HERE, "config.yaml"))
    parser.add_argument("--state", default=os.path.join(HERE, "state", "seen.json"))
    parser.add_argument("--dry-run", action="store_true", help="print notifications and don't save state")
    parser.add_argument("--test-notify", action="store_true", help="send one test notification and exit")
    parser.add_argument("--loop", type=float, metavar="MINUTES", help="keep running, checking every MINUTES")
    parser.add_argument("-v", "--verbose", action="store_true", help="log why each listing was skipped")
    args = parser.parse_args()

    with open(args.config, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    try:
        notifier = Console() if args.dry_run else Ntfy(cfg.get("notify", {}))
    except ValueError as e:
        print(f"error: {e} (or use --dry-run)", file=sys.stderr)
        return 2
    if args.test_notify:
        notifier.send("magpie test", "Notifications work. You'll get one like this for every new matching flat.",
                      click="https://github.com/hospodskej/security_engineering_tools", tags=["house"])
        return 0

    http = Http()
    while True:
        state = State(args.state)
        failures = run_once(cfg, state, notifier, http, verbose=args.verbose)
        if not args.dry_run:
            state.save()
        if not args.loop:
            return 1 if failures else 0
        time.sleep(args.loop * 60)


if __name__ == "__main__":
    sys.exit(main())
