import json
import logging
import re
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)

_SENTENCE_END = ('.', '!', '?', '"', "'", ')', ']', ':', ';', ',', '…')

INLINE_FORMAT_REPLACEMENTS = [
    (r'\bnew paragraph\b', '\n\n'),
    (r'\bnew line\b', '\n'),
    (r'\b(?:full stop|period)\b', '.'),
    (r'\bcomma\b', ','),
    (r'\bquestion mark\b', '?'),
    (r'\bexclamation (?:mark|point)\b', '!'),
    (r'\bcolon\b', ':'),
    (r'\bsemi[- ]?colon\b', ';'),
    (r'\bopen (?:quote|quotes)\b', ' "'),
    (r'\bclose (?:quote|quotes)\b', '" '),
    (r'\bopen paren(?:thesis)?\b', ' ('),
    (r'\bclose paren(?:thesis)?\b', ') '),
    (r'\bopen bracket\b', ' ['),
    (r'\bclose bracket\b', '] '),
    (r'\bdash\b', ' — '),
    (r'\bhyphen\b', '-'),
]


def postprocess(text: str, config: dict) -> str:
    if not text or not config:
        return text

    if config.get('inline_formatting', False):
        text = _apply_inline_formatting(text, config)

    if config.get('strip_filler_words', False):
        text = _strip_fillers(text)

    if config.get('strip_trailing_period', False):
        text = _strip_trailing_period(text)

    if config.get('capitalize_first', False):
        text = _capitalize_first(text)

    if config.get('ensure_punctuation', False):
        text = _ensure_punctuation(text)

    ollama_cfg = config.get('ollama') or {}
    if ollama_cfg.get('enabled', False):
        polished = _ollama_polish(text, ollama_cfg)
        if polished:
            text = polished

    return text


def _strip_trailing_period(text: str) -> str:
    stripped = text.rstrip()
    if not stripped:
        return text
    trailing = text[len(stripped):]
    if stripped.endswith('.') and not stripped.endswith('..'):
        return stripped[:-1] + trailing
    return text


# Build the (pattern, replacement) list to apply. With no user config, this is
# just the built-in English map. A user can supply their own phrases via
# postprocess.inline_formatting_replacements — essential for non-English dictation
# (e.g. Polish), where Whisper won't emit the English trigger words. By default a
# user list REPLACES the English defaults; set inline_formatting_extend: true to
# append to them instead. User phrases are matched as whole, case-insensitive,
# regex-escaped words, so no regex injection or ReDoS is possible.
def _resolve_inline_replacements(config: dict):
    cfg = config or {}
    custom = cfg.get('inline_formatting_replacements') or []

    entries = []
    if not custom or cfg.get('inline_formatting_extend', False):
        entries.extend(INLINE_FORMAT_REPLACEMENTS)

    for item in custom:
        if not isinstance(item, dict):
            continue
        phrase = str(item.get('phrase', '')).strip()
        if not phrase:
            continue
        replacement = str(item.get('replacement', ''))
        entries.append((r'\b' + re.escape(phrase) + r'\b', replacement))
    return entries


def _apply_inline_formatting(text: str, config: dict = None) -> str:
    for pattern, replacement in _resolve_inline_replacements(config):
        # Literal replacement via a function repl: avoids re interpreting \1, \g<>,
        # or stray backslashes in user-provided replacement strings.
        text = re.sub(pattern, lambda _m, r=replacement: r, text, flags=re.IGNORECASE)
    text = re.sub(r' +([.,!?:;])', r'\1', text)
    text = re.sub(r'\(\s+', '(', text)
    text = re.sub(r'\s+\)', ')', text)
    text = re.sub(r' {2,}', ' ', text)
    return text.strip()


def _strip_fillers(text: str) -> str:
    pattern = re.compile(
        r'\b(um|uh|erm|uhm|like|you know)\b[,]?\s*',
        flags=re.IGNORECASE,
    )
    cleaned = pattern.sub('', text)
    cleaned = re.sub(r'\s{2,}', ' ', cleaned).strip()
    return cleaned or text


def _capitalize_first(text: str) -> str:
    stripped = text.lstrip()
    if not stripped:
        return text
    leading = text[: len(text) - len(stripped)]
    return leading + stripped[0].upper() + stripped[1:]


def _ensure_punctuation(text: str) -> str:
    stripped = text.rstrip()
    if not stripped:
        return text
    trailing = text[len(stripped):]
    if stripped.endswith(_SENTENCE_END):
        return text
    return stripped + '.' + trailing


def _ollama_polish(text: str, cfg: dict) -> str:
    endpoint = cfg.get('endpoint', 'http://localhost:11434').rstrip('/')
    model = cfg.get('model', 'llama3.2')
    prompt_template = cfg.get(
        'prompt',
        "Polish this dictation. Fix punctuation and capitalization only. Do not change wording or add anything. Output ONLY the polished text:\n\n{text}",
    )
    timeout = float(cfg.get('timeout', 5))

    if '{text}' in prompt_template:
        final_prompt = prompt_template.replace('{text}', text)
    else:
        final_prompt = f"{prompt_template}\n\n{text}"

    payload = {
        'model': model,
        'prompt': final_prompt,
        'stream': False,
    }

    try:
        req = urllib.request.Request(
            f"{endpoint}/api/generate",
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
        polished = (data.get('response') or '').strip()
        if polished:
            logger.debug("Ollama polish applied")
            return polished
    except (urllib.error.URLError, OSError, ValueError) as e:
        logger.warning(f"Ollama post-edit unavailable ({e}); using raw transcript")
    return ''
