"""
run_pipeline.py — Rebuild the entire study from the crawl snapshots, in order.

One command redoes everything downstream of the raw crawls so no derived artifact
is ever left stale. Stages are idempotent and read from the immutable
crawls/*/data.json snapshots.

  fetch_siblings  → data/sibling_files.json     (folder contents per skill)
  score_corpus    → data/skill_quality.json     (the scored corpus)
  gen_types       → data/skill_types.json       (quality by skill type)
  track_history   → data/skill_history.json     (timelines + per-crawl delta)
  lineage_trace   → data/lineage.json           (copy clusters + ancestry)
  originator_lead → data/originator_leaderboard.json + docs/originators.md
  curiosities     → docs/curiosities.md         (the oddities)
  render_copy_net → docs/figures/copy-network.png
  render_sankey   → docs/figures/sankey-lineage.png
  build_lineage   → lineage.html
  patch_map       → index.html badges
  gen_stats       → data/corpus_stats.json + docs/STATS.md   (source of truth)
  check_docs      → warns if any narrative doc's headline numbers fell out of sync

Usage:
  python crawlers/run_pipeline.py                 # rebuild from existing snapshots
  python crawlers/run_pipeline.py --crawl LIST    # crawl first, then rebuild
  python crawlers/run_pipeline.py --no-net        # skip stages that hit the network
  python crawlers/run_pipeline.py --fast          # skip slow network stages (siblings, lineage fetch)
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
PY = sys.executable

# (script, args, hits_network, slow)
STAGES = [
    ('fetch_siblings.py', [], True, True),
    ('score_corpus.py', [], False, False),
    ('gen_types.py', [], False, False),
    ('track_history.py', [], False, False),
    ('lineage_trace.py', [], True, True),
    ('originator_leaderboard.py', [], False, False),
    ('gen_conventions.py', [], False, False),
    ('curiosities.py', [], False, False),
    ('render_copy_network.py', [], False, False),
    ('render_sankey.py', [], False, False),
    ('build_lineage_page.py', [], False, False),
    ('patch_map_badges.py', [], False, False),
    ('gen_stats.py', [], False, False),
    ('check_docs.py', [], False, False),
]


def run(script, args):
    t = time.time()
    r = subprocess.run([PY, str(HERE / script), *args],
                       capture_output=True, text=True)
    ok = r.returncode == 0
    tail = (r.stdout.strip().splitlines() or [''])[-1]
    mark = '✓' if ok else '⚠'
    print(f'  {mark} {script:28s} {time.time()-t:5.1f}s  {tail[:80]}')
    if not ok and script != 'check_docs.py':   # check_docs exits 1 on drift (a warning)
        print(r.stderr.strip()[-400:])
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--crawl', metavar='LIST', help='crawl this list first')
    ap.add_argument('--no-net', action='store_true', help='skip network stages')
    ap.add_argument('--fast', action='store_true', help='skip slow network stages')
    args = ap.parse_args()

    print('▶ skill-map pipeline')
    if args.crawl:
        print(f'  crawling {args.crawl} …')
        run('crawl.py', ['crawl', '--crawl-list', args.crawl])

    failed = []
    for script, sargs, net, slow in STAGES:
        if (args.no_net and net) or (args.fast and slow):
            print(f'  – {script:28s} skipped')
            continue
        if not run(script, sargs):
            failed.append(script)

    print('▶ done' + (f' — issues in: {", ".join(failed)}' if failed else
                       ' — all stages green'))
    # check_docs drift is surfaced above; don't fail the whole run on it
    sys.exit(1 if [f for f in failed if f != 'check_docs.py'] else 0)


if __name__ == '__main__':
    main()
