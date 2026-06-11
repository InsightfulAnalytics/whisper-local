# Real-time streaming preview (experimental)

Whisper Local can show your words **in the overlay as you speak**, before the
final transcription lands — the Wispr-style live feedback. This page explains
what it does, how to turn it on, and an important design decision about *where*
streamed text goes.

## What it does

When enabled, a small streaming speech model ([sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx)
Zipformer) runs alongside your recording and feeds partial words into the
floating overlay pill in real time. When you stop, the **accurate** Whisper model
still does the actual transcription that gets delivered to your cursor.

So you get the best of both: instant visual feedback *and* high-quality final text.

## How to turn it on

In `user_settings.yaml`:

```yaml
streaming:
    streaming_enabled: true
    streaming_model: zipformer.tiny.en   # ~20 MB, English
```

The streaming model downloads automatically on first use (separate from the
Whisper model). It's English-only by default; other sherpa-onnx streaming
transducers can be added under `streaming.models` — browse them at
<https://k2-fsa.github.io/sherpa/onnx/pretrained_models/index.html>.

It's **off by default** because it needs that extra model download and a little
extra CPU while recording.

## Design decision: streamed text goes to the overlay, NOT your document

A reasonable question: *why not type the partial words straight into my document
as I speak, like some tools do?*

Because streaming transducers **revise** their output as more audio arrives:

```
"spag"  →  "spagetti"  →  "spaghetti"
"to"    →  "two"        →  "too"
```

If those intermediate guesses were pasted into your real document, you'd get a
stream of wrong words being typed and re-typed — corrupting the text, spamming
undo history, and fighting your cursor. The *final* Whisper pass is also more
accurate than the small streaming model, so committing partials would actually
*lower* quality.

So Whisper Local deliberately shows partials only in the **overlay** (safe,
disposable) and delivers the single accurate Whisper result to your cursor.

## Want true progressive delivery? (future opt-in)

There *is* a safe way to type-as-you-go: commit only **finalized** segments —
i.e. when the streaming model detects a phrase boundary (an "endpoint"), type
that settled chunk to the cursor and move on. No revisions reach your document
because only post-endpoint text is delivered.

The tradeoff: you'd get the streaming model's accuracy (lower than the full
Whisper pass), and it's a whole alternative delivery mode with its own edge cases
(cancel, auto-send, per-app rules, the fallback window). It's a real feature, just
a substantial and accuracy-trading one — tracked as a future opt-in (`docs/AUDIT.md`
product ideas) rather than the default. The endpoint detection it would need
(`streaming_recognizer.is_endpoint()`) already exists.
