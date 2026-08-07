# Contributing

There are three useful ways to contribute: submit a public skills repository,
audit and improve skills, or develop the crawler, scorer, and map.

## Submit your skills repo

The [Skill Map](https://dhk.github.io/skill-map/) indexes repositories by
reference. The crawler reads public `SKILL.md` files where they live; it does
not move ownership of those skills into this repository.

Choose either route.

### Issue form

Open the [Submit a skill repo
form](https://github.com/dhk/skill-map/issues/new?template=submit-skill.yml) and
provide the `owner/repo`.

### Pull request

Add a row to
[`crawlers/crawl-lists/community.md`](crawlers/crawl-lists/community.md):

```markdown
| owner/repo | single-skill | One-line description of what it does. |
```

The repository must be public and contain at least one `SKILL.md`. The crawler
requires only the repository column; the remaining fields provide human context.

## Audit your skills

Use the repository-level auditor to compare a skills collection with the
corpus-derived rubric:

```bash
pip install pyyaml
python crawlers/audit_repo.py /path/to/your/skills
python crawlers/audit_repo.py --github owner/repo
python crawlers/audit_repo.py --github owner/repo --token "$GITHUB_TOKEN"
```

The auditor reports repository signature, peer benchmarks, weak skills,
potential consolidation, and common capabilities that may be missing.

To review one skill interactively, install
[skill-doctor](SKILL-DOCTOR.md). The shortest route is:

```bash
pipx run dhk-skill-doctor
```

The [installation guide](INSTALL.md) contains the plugin, shell, zip, manual,
and verify-first alternatives.

To run the audit in GitHub Actions when a pull request changes a `SKILL.md`,
use the [bundled action](.github/actions/skill-audit/README.md):

```yaml
- uses: dhk/skill-map/.github/actions/skill-audit@main
```

## Develop this repo

### Requirements

- Git
- Python 3.9 or later
- a browser for the static map

Clone the repository:

```bash
git clone https://github.com/dhk/skill-map
cd skill-map
```

### Fast smoke test

This path uses only the Python standard library:

```bash
python crawlers/skill_quality.py plugins/skill-doctor/skills/skill-doctor/SKILL.md
```

A JSON score confirms that the checkout and core scorer are usable.
`skill_quality.py`, `audit_repo.py`, and `repo_signature.py` can run without
PyYAML, although installing it provides the preferred parser.

### Full pipeline

Install the development dependencies and rebuild derived artifacts from the
existing crawl snapshots:

```bash
pip install -r requirements.txt
python crawlers/run_pipeline.py --fast
```

The data flow is:

```text
public repository
    → seed-list reference
    → crawler
    → immutable snapshot in crawls/
    → scoring and analysis pipeline
    → data/, studies, and interactive map
```

The pipeline’s docstring is the source of truth for its current stage order.
See [the architecture overview](docs/architecture/overview.md) and
[incremental crawl design](docs/incremental-crawl-system.md) for the stable
boundaries.

## Validate a change

No comprehensive automated test suite exists yet. Use the checks appropriate to
the files you changed.

| Change | Minimum validation |
|---|---|
| `crawlers/` or scoring logic | Run the full pipeline and inspect changed generated artifacts |
| Narrative documentation or headline figures | Run `python crawlers/check_docs.py` |
| Wiring metadata | Run the validation command documented in [WIRING.md](WIRING.md) |
| Static map | Serve the repository locally and inspect the affected view |
| skill-doctor package | Run the package and zip checks documented under `plugins/skill-doctor/` |

Do not hand-edit generated files. The [documentation
index](docs/README.md) identifies which documents are generated and the command
that rebuilds them.

## Pull requests

Keep pull requests focused and explain:

- the problem being addressed;
- which source data or code changed;
- which derived artifacts were regenerated;
- the validation commands run; and
- any known limitation left for later work.

A corpus change should preserve the source repository and crawl provenance.
A documentation change should not invent a live count: use the generated
statistics or label the value with its crawl date.
