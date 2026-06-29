"""
graphio.py — One place that knows how the GRAPH JSON is embedded in index.html.

Previously tag_skills / reclassify / enrich_urls / patch_map_badges / classify_tags
each re-implemented `const GRAPH = ({.*?});\n` with INCONSISTENT re.S flags; the
no-DOTALL copies only worked because the blob happened to stay minified on one
line. Centralising it here means the parsing assumption lives once, and the day
the page is reformatted there is a single spot to fix.

    graph, content, match = load_graph()
    ...mutate graph...
    save_graph(graph, content, match)
"""
import json
import re
import sys
from pathlib import Path

HTML_PATH = Path(__file__).parent.parent / 'index.html'
GRAPH_RE = re.compile(r'const GRAPH = (\{.*?\});\n', re.S)


def load_graph(path=HTML_PATH):
    """Return (graph_dict, full_file_text, regex_match). Exits if not found."""
    content = Path(path).read_text()
    m = GRAPH_RE.search(content)
    if not m:
        sys.exit(f'Could not find `const GRAPH = {{...}};` in {path}')
    return json.loads(m.group(1)), content, m


def save_graph(graph, content, match, path=HTML_PATH):
    """Write `graph` back into the GRAPH slot, minified (one line, as the
    consumers assume on read)."""
    out = json.dumps(graph, separators=(',', ':'))
    Path(path).write_text(content[:match.start(1)] + out + content[match.end(1):])


def skill_nodes(graph):
    """The skill-bearing nodes (real skills + DHK session-layer nodes)."""
    return [n for n in graph['nodes'] if n.get('type') in ('skill', 'dhk')]
