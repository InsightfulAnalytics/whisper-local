# GitHub Discoverability

Settings to apply on github.com so the repo ranks for searches like
"AI dictation tool", "whisper dictation", "local speech-to-text".

## Repository description

Settings → top-right edit pencil → Description:

> Free, local AI dictation for Windows & macOS. Press a hotkey, speak, get text at your cursor. Powered by Whisper. 100 % offline. Push-to-talk, voice commands, sub-second latency.

## Topics (tags)

Settings → top-right edit pencil → Topics. Add each:

```
ai-dictation
speech-to-text
whisper
voice-typing
voice-recognition
transcription
local-ai
offline
privacy
accessibility
windows
macos
global-hotkey
push-to-talk
faster-whisper
dictation
```

## Optional: pin a release tag

After bumping `pyproject.toml` and committing, tag and push:

```bash
git tag -a v0.9.0 -m "v0.9.0 — pre-roll buffer, profiles, doctor, takeover"
git push origin v0.9.0
```

GitHub then shows a "Releases" entry on the repo sidebar.

## Optional: apply via gh CLI in one command

If you're authenticated with `gh auth login`:

```bash
gh repo edit InsightfulAnalytics/whisper-local \
  --description "Free, local AI dictation for Windows & macOS. Press a hotkey, speak, get text at your cursor. Powered by Whisper. 100% offline. Push-to-talk, voice commands, sub-second latency." \
  --add-topic ai-dictation \
  --add-topic speech-to-text \
  --add-topic whisper \
  --add-topic voice-typing \
  --add-topic voice-recognition \
  --add-topic transcription \
  --add-topic local-ai \
  --add-topic offline \
  --add-topic privacy \
  --add-topic accessibility \
  --add-topic windows \
  --add-topic macos \
  --add-topic global-hotkey \
  --add-topic push-to-talk \
  --add-topic faster-whisper \
  --add-topic dictation
```
