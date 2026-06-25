"""
reclassify.py — Reclassify all skill nodes into new domains and patch index.html.

Usage (from repo root):
    python crawlers/reclassify.py

Edit NEW_DOMAINS, MOVES, and RENAME to adjust the taxonomy, then re-run.
The script reads the GRAPH JSON embedded in index.html, rebuilds nodes/links,
and writes the result back in-place.
"""
import json, re, os

HTML_PATH = os.path.join(os.path.dirname(__file__), '..', 'index.html')

with open(HTML_PATH, 'r') as f:
    content = f.read()

match = re.search(r'const GRAPH = ({.*?});\n', content)
graph = json.loads(match.group(1))

# ── NEW DOMAINS ─────────────────────────────────────────────────
NEW_DOMAINS = {
    'Session Layer':        {'color':'#16a34a','size':14,'count':8},
    'Platform & APIs':      {'color':'#6366f1','size':34,'count':195},
    'Frontend & UI':        {'color':'#8b5cf6','size':28,'count':128},
    'Infrastructure & DevOps': {'color':'#0ea5e9','size':20,'count':82},
    'Data & Analytics':     {'color':'#10b981','size':18,'count':65},
    'Agent & Orchestration':{'color':'#f59e0b','size':19,'count':70},
    'Security':             {'color':'#ef4444','size':20,'count':76},
    'Testing & Quality':    {'color':'#06b6d4','size':18,'count':67},
    'Creative & Media':     {'color':'#f97316','size':17,'count':52},
    'Document & Writing':   {'color':'#ec4899','size':17,'count':58},
    'Marketing & Growth':   {'color':'#14b8a6','size':15,'count':44},
    'Product & Strategy':   {'color':'#84cc16','size':14,'count':33},
    'Finance & Payments':   {'color':'#fb923c','size':12,'count':14},
    'Research & Learning':  {'color':'#a855f7','size':12,'count':24},
    'Developer Experience': {'color':'#3b82f6','size':22,'count':81},
}

# ── EXPLICIT MOVES (skill id → new domain) ─────────────────────
MOVES = {
    # was Document Creation
    'voltagent/voltagent-docs-bundle':              'Platform & APIs',
    'microsoft/azure-ai-document-intelligence-dotnet': 'Platform & APIs',
    'fal-ai-community/fal-restore':                 'Creative & Media',
    'WordPress/wordpress-router':                   'Developer Experience',
    'coreyhaines31/product-marketing-context':      'Marketing & Growth',
    # was Security & Auth
    'anthropics/doc-coauthoring':                   'Document & Writing',
    'composiohq/composio':                          'Platform & APIs',
    'firecrawl/firecrawl-build-interact':           'Platform & APIs',
    'veniceai/venice-api-overview':                 'Platform & APIs',
    'googleworkspace/gws-shared':                   'Platform & APIs',
    'WordPress/wp-plugin-development':              'Developer Experience',
    'openai/netlify-deploy':                        'Infrastructure & DevOps',
    # was Media & Creative
    'trailofbits/entry-point-analyzer':             'Security',
    'getsentry/sentry-flutter-sdk':                 'Testing & Quality',
    'realkimbarrett/schwartz-awareness-mapper':     'Marketing & Growth',
    'binance/crypto-market-rank':                   'Finance & Payments',
    'brave/images-search':                          'Platform & APIs',
    'flutter/flutter-handling-concurrency':         'Frontend & UI',
    # was Frontend & Design
    'anthropics/canvas-design':                     'Creative & Media',
    'voltagent/create-voltagent':                   'Agent & Orchestration',
    'google-gemini/gemini-live-api-dev':            'Platform & APIs',
    'stripe/stripe-best-practices':                 'Finance & Payments',
    'tinybirdco/tinybird-cli-guidelines':           'Platform & APIs',
    'hashicorp/terraform-style-guide':              'Infrastructure & DevOps',
    'sanity-io/content-modeling-best-practices':    'Developer Experience',
    'firecrawl/firecrawl-build':                    'Platform & APIs',
    # was Communication (all move out — domain retired)
    'anthropics/slack-gif-creator':                 'Creative & Media',
    'anthropics/internal-comms':                    'Document & Writing',
    'trycourier/courier-skills':                    'Platform & APIs',
    'googleworkspace/gws-gmail':                    'Platform & APIs',
    'getsentry/sentry-create-alert':                'Infrastructure & DevOps',
    'microsoft/azure-communication-callautomation-java': 'Platform & APIs',
    'coreyhaines31/cold-email':                     'Marketing & Growth',
    'resend/resend':                                'Platform & APIs',
    'NVIDIA/Megatron-Bridge/perf-expert-parallel-overlap': 'Research & Learning',
    # was Testing & Debugging
    'googleworkspace/gws-admin-reports':            'Platform & APIs',
    'trailofbits/dwarf-expert':                     'Research & Learning',
    'openai/gh-fix-ci':                             'Developer Experience',
    'realkimbarrett/ad-angle-multiplier':           'Marketing & Growth',
    'deanpeters/epic-hypothesis':                   'Product & Strategy',
    # was Developer Tools (all move out — domain retired)
    'anthropics/template':                          'Developer Experience',
    'google-gemini/gemini-api-dev':                 'Platform & APIs',
    'replicate/replicate':                          'Platform & APIs',
    'veniceai/venice-chat':                         'Platform & APIs',
    'vercel-labs/next-best-practices':              'Frontend & UI',
    'googleworkspace/gws-drive':                    'Platform & APIs',
    'expo/expo-api-routes':                         'Platform & APIs',
    'huggingface/hf-cli':                           'Platform & APIs',
    'trailofbits/sharp-edges':                      'Security',
    'getsentry/sentry-sdk-setup':                   'Developer Experience',
    'microsoft/continual-learning':                 'Research & Learning',
    'fal-ai-community/fal-platform':                'Platform & APIs',
    # was Agent Orchestration
    'callstackincubator/github':                    'Developer Experience',
    'sanity-io/sanity-best-practices':              'Developer Experience',
    'veniceai/venice-video':                        'Creative & Media',
    'expo/expo-cicd-workflows':                     'Infrastructure & DevOps',
    'trailofbits/claude-in-chrome-troubleshooting': 'Developer Experience',
    'openai/linear':                                'Product & Strategy',
    # was Data & Databases
    'cloudflare/durable-objects':                   'Infrastructure & DevOps',
    'google-labs-code/stitch-loop':                 'Creative & Media',
    'trailofbits/testing-handbook-skills':          'Testing & Quality',
    'getsentry/sentry-pr-code-review':              'Developer Experience',
    'WordPress/wp-performance':                     'Infrastructure & DevOps',
    # was DevOps & Infrastructure
    'google-gemini/vertex-ai-api-dev':              'Platform & APIs',
    'hashicorp/new-terraform-provider':             'Developer Experience',
    'cloudflare/cloudflare-email-service':          'Platform & APIs',
    'getsentry/sentry-setup-ai-monitoring':         'Developer Experience',
    # was Finance & Payments
    'trailofbits/constant-time-analysis':           'Security',
    'microsoft/azure-keyvault-keys-rust':           'Security',
    # was Marketing & Content
    'googleworkspace/gws-modelarmor':               'Security',
    'microsoft/azure-ai-contentsafety-java':        'Security',
    'brave/llm-context':                            'Platform & APIs',
    'deanpeters/pestel-analysis':                   'Product & Strategy',
    'degausai/wonda':                               'Creative & Media',
    # was Product Management
    'openai/sentry':                                'Developer Experience',
    'coreyhaines31/launch-strategy':                'Marketing & Growth',
    'realkimbarrett/offer-extraction':              'Marketing & Growth',
    'datadog-labs/dd-llmo-eval-bootstrap':          'Testing & Quality',
    'addyosmani/core-web-vitals':                   'Testing & Quality',
    'redhat/cve-skillpack':                         'Security',
    'Paramchoudhary/ResumeSkills':                  'Research & Learning',
}

# ── DOMAIN RENAMES (for skills not in MOVES) ────────────────────
RENAME = {
    'Security & Auth':      'Security',
    'Agent Orchestration':  'Agent & Orchestration',
    'Data & Databases':     'Data & Analytics',
    'DevOps & Infrastructure': 'Infrastructure & DevOps',
    'Testing & Debugging':  'Testing & Quality',
    'Media & Creative':     'Creative & Media',
    'Document Creation':    'Document & Writing',
    'Marketing & Content':  'Marketing & Growth',
    'Product Management':   'Product & Strategy',
    'Frontend & Design':    'Frontend & UI',
}

def get_new_domain(node):
    if node['type'] in ('dhk', 'dhk_hub', 'dhk_negative_space'):
        return 'Session Layer'
    if node['id'] in MOVES:
        return MOVES[node['id']]
    old = node.get('domain','')
    return RENAME.get(old, old)

# ── REBUILD NODES ───────────────────────────────────────────────
old_domain_ids = {n['id'] for n in graph['nodes'] if n['type']=='domain'}
new_nodes = []

# Add new domain nodes
for dname, dmeta in NEW_DOMAINS.items():
    new_nodes.append({
        'id': f'domain:{dname}',
        'label': dname,
        'type': 'domain',
        'color': dmeta['color'],
        'size': dmeta['size'],
        'count': dmeta['count'],
    })

# Add all non-domain nodes, updating domain field
for n in graph['nodes']:
    if n['type'] == 'domain':
        continue  # replaced above
    new_n = dict(n)
    if n['type'] in ('skill','dhk'):
        nd = get_new_domain(n)
        new_n['domain'] = nd
        new_n['color'] = NEW_DOMAINS[nd]['color']
    new_nodes.append(new_n)

# ── REBUILD LINKS ───────────────────────────────────────────────
new_links = []
for l in graph['links']:
    src = l['source'] if isinstance(l['source'],str) else l['source']['id']
    tgt = l['target'] if isinstance(l['target'],str) else l['target']['id']
    # Drop links to old domain nodes
    if tgt in old_domain_ids or src in old_domain_ids:
        continue
    new_links.append(l)

# Add new domain links for skills and dhk nodes (so they cluster into their domain)
for n in new_nodes:
    if n['type'] == 'skill':
        new_links.append({'source': n['id'], 'target': f'domain:{n["domain"]}', 'type':'domain'})
    elif n['type'] in ('dhk', 'dhk_hub'):
        nd = n.get('domain', 'Session Layer')
        new_links.append({'source': n['id'], 'target': f'domain:{nd}', 'type':'domain'})

# org links are already in new_links from the non-domain original links

new_graph = {'nodes': new_nodes, 'links': new_links}
out = json.dumps(new_graph, separators=(',',':'))
print(f"Nodes: {len(new_nodes)}, Links: {len(new_links)}")

# ── PATCH HTML ──────────────────────────────────────────────────
new_content = content[:match.start(1)] + out + content[match.end(1):]
with open(HTML_PATH, 'w') as f:
    f.write(new_content)
print("Done.")
