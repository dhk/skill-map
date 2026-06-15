# The Skill Map

![Last Updated](https://img.shields.io/badge/updated-June%202026-9aabb8) ![Skills](https://img.shields.io/badge/skills-1%2C119-16a34a) ![Domains](https://img.shields.io/badge/domains-13-3b82f6) ![Stars](https://img.shields.io/github/stars/dhk/skill-map?style=flat&color=9aabb8)

**A living reference for the Agent Skills ecosystem: 1,119 skills, 13 domains, 5 uncharted territories**

An interactive force-directed map of every published skill in the Claude / agent ecosystem, built from crawling [VoltAgent/awesome-agent-skills](https://github.com/VoltAgent/awesome-agent-skills) in June 2026. Thirteen domains. Fifty-two organizations. And five territories with zero published skills: the negative space that tells you where the ecosystem is missing something.

[**Open the map →**](https://dhk.github.io/skill-map)

---

## The Session Layer Gap

Every published skill in this corpus does one thing: it makes Claude better at a task. Write better Terraform. Review smarter contracts. Generate cleaner dbt models. The task layer is well-covered: 1,119 skills and counting.

Nobody has published a skill for how to run a day.

That's the session layer: the skills that manage continuity across a working session. Captain's log. Day planning. Context snapshots. Weekly resets. Reading list ingestion. These aren't task-layer utilities: they're the infrastructure that makes Claude a persistent collaborator rather than a stateless tool. Stateless tools get abandoned. Persistent collaborators become habits.

DHK has been building and running session-layer skills in production for over a year, before Anthropic formalized the Skills format in October 2025. None of that work appears in the public corpus, because nobody had a category for it. This map makes the gap visible.

---

## The Negative Space

Five territories with zero published skills as of June 2026:

**1. The Session Layer**: Skills for continuity: captain's log, day planning, context handoff, weekly resets. The stickiest use case in the ecosystem, and the most underbuilt.

**2. Claude as Personal OS**: Orchestrated workflow systems that embed Claude into daily rhythm. Not individual automations: a coordinated layer that runs your day.

**3. Skill Discovery**: No canonical registry. No versioning standard. No dependency management. The npm problem, unsolved.

**4. Skill Evaluation**: No benchmark. No eval harness. Skills ship on vibes. The ecosystem has no way to measure whether a skill is good.

**5. Healthcare & Life Sciences**: The largest enterprise vertical in software. Zero published skills. HIPAA compliance, clinical workflow, EHR integration: all dark matter.

---

## How to Use the Map

- **Click a domain node** to filter to that domain and surface the persona who lives there
- **Click an org node** to see all skills from that organization
- **Click a skill node** to see the skill's name, domain, and org
- **Click "DHK" in the filter bar** to isolate the session-layer cluster in the negative space
- **Click "Uncharted"** to highlight the five red clouds: the territories with no published skills
- **Click any red cloud** to open the territory description

---

## Data Sources

- **Skills corpus:** [VoltAgent/awesome-agent-skills](https://github.com/VoltAgent/awesome-agent-skills): 1,119 skills across 52 organizations
- **Crawled:** June 2026
- **Graph:** 226 nodes, 302 links
- **Domains:** 13 (Developer Tools, Security & Auth, Frontend & Design, Agent Orchestration, Data & Databases, DevOps & Infrastructure, Testing & Debugging, Document Creation, Marketing & Content, Product Management, Finance & Payments, Communication, Media & Creative)
- **Negative space:** 5 uncharted territories identified by DHK

---

## About

Built by [DHK](https://dhkondata.substack.com): practitioner writing on data, AI, and working systems.

- Substack: [dhkondata.substack.com](https://dhkondata.substack.com)
- GitHub: [github.com/dhk](https://github.com/dhk)

The argument behind the map: [The Session Layer](https://dhkondata.substack.com): published June 2026.
