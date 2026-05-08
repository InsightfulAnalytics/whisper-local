# Recording the demo GIF

The README references `docs/demo.gif`. Until you record a real one, the
image will 404 in the rendered README. To produce one:

## Recommended

1. Install [ScreenToGif](https://www.screentogif.com/) (Windows) or
   [Kap](https://getkap.co/) (macOS) — both are free and open source.
2. Open a clean Notepad / VS Code window so the cursor target is obvious.
3. Start ScreenToGif, capture a region just around that window.
4. Press `Ctrl+Win`, speak a short sentence (e.g. "the quick brown fox jumps
   over the lazy dog"), release.
5. Wait for the transcript to appear at the cursor.
6. Stop the recording, trim to ~5 seconds, save as `docs/demo.gif`.
7. Optimise: ScreenToGif's built-in optimiser; aim for under 2 MB so
   GitHub renders it inline.

## Drop-in via FFmpeg (CLI)

If you already have a screen recording in `.mp4`:

```bash
ffmpeg -i input.mp4 -vf "fps=12,scale=720:-1:flags=lanczos" -loop 0 docs/demo.gif
```

## Linking from README

The README already has a placeholder image tag:

```markdown
![Demo](docs/demo.gif)
```

Replace it with your file at the same path and the README will pick it up
automatically.
