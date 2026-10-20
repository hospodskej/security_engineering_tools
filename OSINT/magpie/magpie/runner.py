from .filters import Filters
from .notify import fmt_czk, listing_alert
from .sources import build_sources


def run_once(cfg, state, notifier, http, verbose=False):
    """One pass over every source. Returns the number of notifications that failed to send."""
    filters = Filters(cfg)
    fail_alert_after = cfg.get("health", {}).get("alert_after_failures", 6)
    first_run_limit = cfg.get("first_run_limit", 15)
    send_failures = 0

    def log(msg):
        print(msg, flush=True)

    for src in build_sources(cfg, http):
        st = state.source(src.name)
        try:
            listings = src.fetch()
            if not listings:
                raise RuntimeError("no listings parsed; the site layout may have changed")
        except Exception as e:
            st["failures"] += 1
            log(f"[{src.name}] fetch failed ({st['failures']}x in a row): {e}")
            if st["failures"] >= fail_alert_after and not st["alerted"]:
                try:
                    notifier.send(f"magpie: {src.name} is failing",
                                  f"{st['failures']} runs in a row failed.\nLast error: {e}",
                                  priority=3, tags=["warning"])
                    st["alerted"] = True
                except Exception as ne:
                    log(f"[{src.name}] could not send health alert: {ne}")
            continue

        if st["alerted"]:
            try:
                notifier.send(f"magpie: {src.name} works again", "Back to normal.", priority=2, tags=["white_check_mark"])
            except Exception as ne:
                log(f"[{src.name}] could not send recovery note: {ne}")
        st["failures"], st["alerted"] = 0, False

        first_run = not st["initialized"]
        matches = []
        for listing in listings:
            prev = state.seen(listing.key)
            if prev is not None:
                dropped = listing.rent is not None and prev.get("rent") is not None and listing.rent < prev["rent"]
                if not dropped:
                    state.touch(listing.key)
                    continue
                listing.notes.append(f"price dropped from {fmt_czk(prev['rent'])}")

            pre = filters.precheck(listing)
            if not pre.ok:
                if verbose:
                    log(f"[{src.name}] skip {listing.id}: {pre.reason}")
                state.mark(listing)
                continue

            try:
                src.enrich(listing)
            except Exception as e:
                # Not marked as seen, so it is retried next run; a listing that was
                # taken down drops out of the search results and stops being retried.
                log(f"[{src.name}] detail fetch failed for {listing.url}: {e}")
                continue

            verdict = filters.final(listing)
            state.mark(listing)
            if not verdict.ok:
                if verbose:
                    log(f"[{src.name}] skip {listing.id}: {verdict.reason}")
                continue
            dup = state.duplicate_of(listing)
            if dup:
                log(f"[{src.name}] {listing.url} is the same flat as {dup}, already sent")
                continue
            matches.append((listing, verdict.flags))
            log(f"[{src.name}] MATCH {listing.url} ({', '.join(verdict.flags) or 'clean'})")

        log(f"[{src.name}] {len(listings)} listings, {len(matches)} new matches"
            + (" (first run: sending quietly)" if first_run else ""))

        # The first run sees everything currently listed; send those quietly so the
        # phone only buzzes for flats that appear after magpie started watching.
        if first_run and len(matches) > first_run_limit:
            extra = len(matches) - first_run_limit
            matches = matches[:first_run_limit]
            try:
                notifier.send(f"magpie: {extra} more on {src.name}",
                              f"{extra} more matching flats are already listed on {src.name}. "
                              "From now on you'll get an alert for each new one.",
                              priority=2, tags=["house"])
            except Exception as e:
                log(f"[{src.name}] could not send first-run summary: {e}")
        for listing, flags in matches:
            try:
                listing_alert(notifier, listing, flags, priority=2 if first_run else 4)
                state.record_alert(listing)
            except Exception as e:
                send_failures += 1
                state.forget(listing.key)  # retry on the next run
                log(f"[{src.name}] notification failed for {listing.url}: {e}")
        st["initialized"] = True

    return send_failures
