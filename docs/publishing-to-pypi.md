# Publishing whisper-local to PyPI

`pyproject.toml` is configured for PyPI. Follow these steps once to publish, then a shorter loop for each release after.

## One-time PyPI account setup

1. **Create a PyPI account**: https://pypi.org/account/register/
2. **Enable 2FA** (PyPI requires it for upload).
3. **Generate a project-scoped API token**:
   - Go to https://pypi.org/manage/account/token/
   - Token name: `whisper-local-publisher`
   - Scope: "Project: whisper-local" (after first upload — see below)
   - Save the token starting with `pypi-...`
4. **Test on TestPyPI first** (recommended for first release):
   - Register at https://test.pypi.org/account/register/
   - Generate a token there too

## First release flow

```powershell
# From G:\Git\whisper-local

# 1. Bump version in pyproject.toml if needed
#    (currently 0.9.0)

# 2. Build wheel + sdist
Remove-Item -Recurse -Force dist, build, *.egg-info, src\*.egg-info -ErrorAction SilentlyContinue
python -m build

# 3. Sanity check the artifacts
python -m twine check dist\*

# 4. Upload to TestPyPI first (optional but recommended)
python -m twine upload --repository testpypi dist\*
# When prompted: username = __token__, password = <your testpypi token>

# 5. Install from TestPyPI to verify
pip install --index-url https://test.pypi.org/simple/ \
            --extra-index-url https://pypi.org/simple \
            whisper-local

# 6. Once happy, upload to real PyPI
python -m twine upload dist\*
# username = __token__, password = <your pypi token>
```

After step 6, anyone can run:

```bash
pip install whisper-local
whisper-local
```

## Subsequent releases

```powershell
# Bump version in pyproject.toml (e.g. 0.9.0 → 0.9.1)
# Add a CHANGELOG entry
git commit -am "Bump to v0.9.1"
git tag -a v0.9.1 -m "v0.9.1 — what changed"
git push origin master --tags

Remove-Item -Recurse -Force dist, build, *.egg-info -ErrorAction SilentlyContinue
python -m build
python -m twine upload dist\*
```

## Credential storage (skip the prompt)

Create `%USERPROFILE%\.pypirc`:

```ini
[pypi]
username = __token__
password = pypi-AgEIcHlwaS5vcmcCJDh...your token...

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-AgENdGVzdC5weXBpLm9yZwIk...your testpypi token...
```

After this, `twine upload dist\*` runs without prompts.

## What the user-side install will look like

Once published:

```bash
pip install whisper-local                    # base install
pip install 'whisper-local[whispercpp]'      # with whisper.cpp backend
whisper-local --setup                        # interactive setup
whisper-local                                # run the app
```

## Troubleshooting

**`File already exists`**: PyPI doesn't allow re-uploading the same version. Bump the version and rebuild.

**`HTTPError: 403`**: Token may be scoped to wrong project, or 2FA required. Re-generate.

**Wheel rejected**: Check the validation step `python -m twine check dist\*` first.
