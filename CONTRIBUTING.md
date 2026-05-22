# Contributing to Whisper Local

Thank you for wanting to make this better. All contributions are welcome — bug reports, fixes, new features, docs, tests.

## Ground rules

- This project is maintained on a **best-effort basis**. There's no support SLA, no guaranteed response time, and no roadmap committee. Please be patient.
- Keep PRs focused. One thing per PR is easier to review than a monolith.
- Match the existing style: explicit names, no docstrings, no unnecessary comments (see `CLAUDE.md`).
- All contributions are MIT licensed.

## Getting started

```bash
git clone https://github.com/drajb/whisper-local.git
cd whisper-local
pip install -e .
python -m unittest tests.test_smoke
```

All 28 smoke tests should pass before you open a PR. CI runs the same suite on every push.

## Reporting bugs

Open an issue with:
1. What you expected to happen
2. What actually happened (include the relevant lines from `%APPDATA%\whisperkey\whisperkey.log`)
3. Your OS, Python version, and GPU (if any)

## Feature requests

Open an issue describing the use-case. The simpler and more self-contained the proposed feature, the more likely it lands.

## Credits

Forked from [whisper-key-local](https://github.com/PinW/whisper-key-local) by Pin Wang.
