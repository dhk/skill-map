"""
ghapi.py — minimal authenticated GitHub REST helper.

Threads $GITHUB_TOKEN (5,000 req/hr authenticated vs 60 unauthenticated) so the
commit-date / tree / sibling passes don't silently exhaust the rate limit. On a
non-2xx response it raises (callers see a real error) instead of letting a bare
`except` turn rate-limit exhaustion into silently-dropped data.
"""
import os
import json
import urllib.request

USER_AGENT = 'skill-map'


def auth_headers(accept='application/vnd.github+json'):
    h = {'Accept': accept, 'User-Agent': USER_AGENT}
    tok = os.environ.get('GITHUB_TOKEN')
    if tok:
        h['Authorization'] = f'Bearer {tok}'
    return h


def gh_get(url, timeout=40, accept='application/vnd.github+json'):
    """Return the open response (caller reads/parses). Raises on non-2xx."""
    req = urllib.request.Request(url, headers=auth_headers(accept))
    return urllib.request.urlopen(req, timeout=timeout)


def gh_json(url, timeout=40):
    """GET and parse JSON."""
    with gh_get(url, timeout=timeout) as r:
        return json.loads(r.read())


def has_token():
    return bool(os.environ.get('GITHUB_TOKEN'))
