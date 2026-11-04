# Skill registry — Portfolio_backend

Generated for SDD init (engram). Paths are absolute for agent handoff.

| name | trigger | path | scope |
|------|---------|------|-------|
| judgment-day | judgment day, dual review, juzgar | `C:\Users\aserra\.cursor\skills\judgment-day\SKILL.md` | user |
| sdd-init | sdd init | `C:\Users\aserra\.agents\skills\sdd-init\SKILL.md` | user |
| work-unit-commits | commit splitting | `C:\Users\aserra\.cursor\skills\work-unit-commits\SKILL.md` | user |

## Project conventions

- Stack: Python 3.14, FastAPI-style `app/`, Docker, Coolify compose
- Test: `pytest -q` (`pytest.ini` testpaths=tests); `aiosqlite` in requirements-dev
- Lint: none pinned (use compileall until ruff/flake8 added)
- Deps: `requirements.txt` + `requirements-dev.txt`
