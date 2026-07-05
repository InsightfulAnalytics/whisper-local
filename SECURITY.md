# Security Policy

Whisper Local is a privacy-first tool. We take security reports seriously.

## Reporting a vulnerability

**Please do not open a public GitHub issue for security problems.**

Use GitHub's **Private Vulnerability Reporting** instead:

1. Go to <https://github.com/InsightfulAnalytics/whisper-local/security/advisories/new>
2. Fill in the form with as much detail as you can — reproduction steps, affected versions, impact assessment
3. We'll acknowledge the report and work with you on a fix and coordinated disclosure

If for some reason you can't use Private Vulnerability Reporting, you can DM the maintainer ([@InsightfulAnalytics](https://github.com/InsightfulAnalytics)) on GitHub instead.

## Scope

We're particularly interested in reports about:

- **Arbitrary code execution** — anything in the voice command pipeline (`commands.yaml`) that lets a crafted phrase escape the matcher
- **Audio exfiltration** — any code path where audio or transcripts leave the machine without explicit user opt-in (the only allowed network calls are the Whisper model download, the opt-in GPU install, and the opt-in update check — see `onboarding.py` and `update_check.py`)
- **Clipboard hijacking** — bugs in the `paste_preserve_clipboard` logic that could leak previous clipboard contents
- **Privilege escalation** — the app should never need admin/sudo. If you find a code path that does, report it
- **Dependency vulnerabilities** that affect users of `whisper-local` specifically

Out of scope:

- Vulnerabilities in our dependencies that don't affect us (please report upstream instead)
- Social-engineering attacks that require the user to type malicious `commands.yaml` entries themselves — the README has a warning about this
- Issues that only reproduce on Python versions outside our supported range (3.11+)

## Supported versions

We're a small project — only the latest GitHub release gets security fixes. If you're on an older version, please upgrade first and confirm the issue still reproduces.

## Disclosure timeline

We aim to:

- Acknowledge the report within **7 days**
- Provide a fix or mitigation within **30 days** for high-severity issues
- Credit reporters in the changelog (unless you ask to stay anonymous)

This is a best-effort project with no SLA; please be patient.
