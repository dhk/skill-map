# The Session Layer

*I crawled 1,119 published agent skills. None of them answer the question that matters most.*

---

Every published skill in the Agent Skills ecosystem does one thing: it makes Claude better at a task. The pattern is consistent across all 1,119 entries. There is a skill for upgrading Stripe integrations. There is a skill for writing secure smart contracts. There is a skill for enforcing Cloudflare Workers best practices. Each one is a bounded, deployable piece of domain knowledge. Load it, use it, ship the thing.

The task layer is well-covered. Thirteen domains, fifty-two organizations, skills for developer tooling and data engineering and agent orchestration and creative work. The corpus is real. The work in it is good. If you need Claude to do a specific technical thing better, there is probably a skill for that.

Nobody has published a skill for how to run a day.

That is the gap. Not a task. The session. The task layer handles what Claude knows. The session layer handles how Claude works with you over time: the continuity, the rhythm, the memory that makes a tool feel like a collaborator. Captain's log. Day planning. Context snapshots at the end of a working session. Weekly resets that carry decisions forward. Reading list ingestion that turns your inbox into a knowledge source. These are not utilities. They are the infrastructure that determines whether Claude is a stateless tool you pick up and put down, or a persistent collaborator you build a working relationship with.

---

I built the map to make the gap visible.

The source is VoltAgent/awesome-agent-skills, a curated list of Claude skills maintained by the community. I crawled it in June 2026, normalized the data, classified 1,119 skills into thirteen domains, and built an interactive force-directed graph. [The map is here.](https://dhk.github.io/skill-map)

What the map shows: a dense cluster of developer tools (407 skills, more than a third of the corpus), strong representation in security and frontend work, real depth in agent orchestration. The ecosystem has been built by engineers, for engineers, and it shows.

What the map also shows: five territories with no skills at all. Not underrepresented. Absent. In the map, they appear as red dashed clouds in the negative space around the main graph. Each one is a territory the ecosystem has not touched.

---

The five uncharted territories:

The session layer is the first and most obvious. No published skill for captain's log, day planning, context continuity, or working session management. The tools that make Claude a persistent part of your day do not exist in the public corpus.

Claude as personal OS is the second. This is distinct from the session layer: it is the idea of Claude as an orchestrated system that runs your daily rhythm, not just a tool you invoke when you have a task. No published skill approaches this. The closest things are individual automations with no coordination layer above them.

Skill discovery is the third. There is no canonical registry. No versioning standard. No dependency management. If you want to know what skills exist, you find a GitHub list and read it. The npm problem, unsolved.

Skill evaluation is the fourth. No benchmark. No eval harness. No standardized way to measure whether a skill is good. Skills ship on vibes. The ecosystem is producing a lot of them with no mechanism for knowing which ones work.

Healthcare and life sciences is the fifth. The largest enterprise vertical in software has zero published skills. HIPAA compliance, clinical workflow, EHR integration. All dark matter. The reasons are obvious (regulatory caution, enterprise procurement cycles, legal review) and do not make the gap smaller.

---

I have been building in the first territory for over a year.

The skills I run in production: captain's-log (passive session note-taker), close-day (end-of-day wrap), plan-day (daily planning), reading-list-builder (Gmail to NotebookLM to audio pipeline), daily-briefing (start-of-day summary), snapshot-create (context handoff for long sessions), tricorder (PR review analysis pipeline), weekly-reset (weekly planning reset that carries decisions forward).

I started building these before Anthropic formalized the Skills format in October 2025. At the time, there was no category for what I was building. There still is not one in the public corpus.

The argument for why this matters: the session layer is the stickiest use case. It is the one that makes you not switch. Task-layer skills are fungible. If a better code review tool ships, you switch. Session-layer infrastructure is not fungible. It knows your rhythm. It carries your history. It has seen your decisions. You do not migrate away from something that has been running your day for a year.

---

The negative space is an invitation. These five territories are open. The session layer is the most buildable right now. It requires no new infrastructure, no regulatory approval, no enterprise procurement cycle. It requires building for the question nobody has asked yet: not what Claude can do, but how Claude works with you over time.

What comes next for this work: a team version of the session layer, where the continuity and rhythm are shared across a group rather than owned by one person. That is a different problem. It is also the one that matters at scale.

---

*The map: [dhk.github.io/skill-map](https://dhk.github.io/skill-map)*
*The corpus: [VoltAgent/awesome-agent-skills](https://github.com/VoltAgent/awesome-agent-skills)*
