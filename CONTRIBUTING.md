# Contributing to Whisper Local

Thank you for wanting to make this better! All contributions are welcome — bug reports, fixes, new features, docs, tests, even just sharing how you use it.

This project is maintained by **Rohit Burani** ([@drajb](https://github.com/drajb)) on a best-effort basis. Whisper Local is a fork of [`whisper-key-local`](https://github.com/PinW/whisper-key-local) by Pin Wang — see [`AUTHORS.md`](AUTHORS.md) for the full credit list.

## Ground rules

- **Be kind.** This project follows the [Code of Conduct](CODE_OF_CONDUCT.md).
- **Privacy is non-negotiable.** No feature should send audio, transcripts, or user data anywhere without an explicit opt-in. If your change adds network calls, they must be opt-in and clearly disclosed in the README and `CHANGELOG.md`.
- **One thing per PR.** Small, focused PRs land faster than a sprawling one.
- **Match the existing style.** Explicit names. No docstrings. Minimal comments. See `CLAUDE.md`.
- **No SLA.** This is volunteer work. Be patient if reviews take a while.
- **All contributions are MIT licensed.** By submitting a PR, you agree your code is contributed under the [LICENSE](LICENSE).

## Getting started

```bash
git clone https://github.com/drajb/whisper-local.git
cd whisper-local
pip install -e .
python -m unittest tests.test_smoke
```

All smoke tests should pass (40 at time of writing). CI runs the same suite on every push.

To run the app from source while developing:

```bash
python -m whisper_key.main          # or `whisper-local` after pip install -e .
python -m whisper_key.main --doctor
python -m whisper_key.main --settings
```

## Reporting bugs

Use the [Bug report template](https://github.com/drajb/whisper-local/issues/new?template=bug_report.yml). Please include:

1. What you expected to happen
2. What actually happened
3. The relevant section of `%APPDATA%\whisperkey\whisperkey.log`
4. Output from `whisper-local --doctor`
5. Your OS, Python version, and Whisper backend

## Feature requests

Use the [Feature request template](https://github.com/drajb/whisper-local/issues/new?template=feature_request.yml). The simpler and more self-contained the proposed feature, the more likely it lands. For larger changes, please **open an issue or discussion first** so we can align on direction before you spend time on code.

## Security vulnerabilities

**Do not open a public issue for security problems.** See [`SECURITY.md`](SECURITY.md) for the private disclosure process.

## Pull request process

1. Fork the repo and create a feature branch from `master`
2. Make your change, keeping commits small and descriptive
3. Run `python -m unittest tests.test_smoke` and make sure all tests pass
4. Add new tests if you're adding new behaviour
5. Update `README.md` / `CHANGELOG.md` if the change is user-visible
6. Open a PR using the [template](.github/PULL_REQUEST_TEMPLATE.md)
7. Add yourself to [`AUTHORS.md`](AUTHORS.md) in the same PR

## Style notes

- **Names over comments.** A well-named function or variable beats a comment that says the same thing.
- **No docstrings.** The codebase deliberately avoids them. If a function isn't obvious from its name and signature, rename it.
- **Break old formats freely.** We don't maintain backward compatibility for configs across major versions — feel free to clean up.
- **Tests live in `tests/test_smoke.py`.** Add new test classes alongside the existing ones.

Thank you again — see you in the PR queue!

— Rohit ([@drajb](https://github.com/drajb))
