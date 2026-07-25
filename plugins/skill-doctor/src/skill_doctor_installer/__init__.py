"""Installer for the skill-doctor Claude Agent Skill.

The skill content (SKILL.md, WIRING.md, reference/) is bundled inside this
package as data at `skill_doctor_installer/_bundled/` — see the
`force-include` mapping in pyproject.toml. Nothing here talks to git; the
wheel is the single artifact that ships the skill.
"""
