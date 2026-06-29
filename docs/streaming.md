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

By default Whisper Local shows partials only in the **overlay** (safe, disposable)
and delivers the single accurate Whisper result to your cursor.

## Type-as-you-go: commit-on-endpoint delivery (opt-in)

If you want text to land *as you speak*, turn on:

```yaml
streaming:
    streaming_enabled: true
    deliver_to_cursor: true
```

Now, each time the streaming model detects a phrase boundary (an "endpoint"), that
**finalized** chunk is typed to the cursor and the run continues. Only post-endpoint
text is delivered, so a word is never typed and then corrected — no revision spam in
your document. When you stop, the trailing phrase is flushed and the full Whisper
pass is skipped (it would just duplicate what's already there).

**Trade-offs and scope, plainly:**
- You get the lighter streaming model's accuracy, not the full Whisper transcription.
- It only kicks in for **plain dictation into a real text field with auto-paste on**.
  Command mode, AI rephrase, copy-only apps, and `suppress` app-rules are unaffected
  and keep using the normal Whisper flow.
- Like any live-typing tool, text already typed can't be un-typed if you cancel.
- Smoothest with `clipboard.delivery_method: type` (direct injection, no clipboard churn).

It's experimental and off by default. The full Whisper path remains the default and
recommended experience for accuracy.
