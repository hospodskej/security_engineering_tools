class Source:
    """A rental site. fetch() returns current search results; enrich() fills in detail-page data."""

    name = ""

    def __init__(self, http, opts):
        self.http = http
        self.opts = opts

    def fetch(self):
        raise NotImplementedError

    def enrich(self, listing):
        pass
