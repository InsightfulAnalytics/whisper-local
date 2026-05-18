# Recording the demo GIF

The README references `docs/demo.gif`. The image tag is commented out
until you drop a real recording in. To produce one:

## Easiest path (Windows, ~3 minutes)

1. **Install** [ScreenToGif](https://www.screentogif.com/) — free, open source, one installer.

2. **Run the helper script** in a PowerShell terminal:
   ```powershell
   powershell.exe -ExecutionPolicy Bypass -File tools\record-demo.ps1
   ```
   It opens Notepad centered on screen at a good capture size and prints the
   sentence to read.

3. **Start ScreenToGif** in *Recorder* mode. Position its frame around the Notepad window. Set FPS to 15 (smaller GIF) and click **Record**.

4. **Press Enter** in the PowerShell terminal — it counts down 5 seconds. Hold `Ctrl+Win` and speak the suggested line. Release.

5. The transcript appears in Notepad. **Stop ScreenToGif's recording.**

6. In ScreenToGif's editor:
   - Trim to the moments around the dictation (target ~5–7 seconds)
   - **File → Save As → GIF** with optimiser enabled
   - Aim for **< 2 MB** so GitHub renders it inline

7. Save as `docs\demo.gif` (overwrite the missing placeholder).

8. Open `README.md` and uncomment the line that says `<!-- ![Demo](docs/demo.gif) -->` — just remove the `<!--` and `-->`.

9. `git add docs/demo.gif README.md && git commit -m "Add demo GIF" && git push`.

## macOS path

1. Install [Kap](https://getkap.co/) (free).
2. Open TextEdit or any plain text window.
3. Record a region around it.
4. Dictate with `Fn+Ctrl` (default mac hotkey).
5. Stop, export as GIF.
6. Save to `docs/demo.gif`, same final steps as above.

## From an existing video file

If you already have an `.mp4`/`.mov` recording:

```bash
ffmpeg -i input.mp4 -vf "fps=12,scale=720:-1:flags=lanczos" -loop 0 docs/demo.gif
```

## Tips

- **Keep it under 7 seconds.** Anyone scrolling the README isn't watching 30 seconds of dictation.
- **One smooth take.** The helper script counts down so you don't waste opening seconds clicking around.
- **Light theme on Notepad** can read cleaner in a GIF than dark mode. Try both.
- **The overlay** (bottom-center pill while recording) should be visible — that's the part viewers find compelling.
