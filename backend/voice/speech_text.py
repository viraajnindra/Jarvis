"""Convert markdown-ish LLM output into plain prose suitable for TTS."""

import re

_FENCE = re.compile(r"```[^\n]*\n.*?```", re.DOTALL)
_INLINE_CODE = re.compile(r"`([^`]*)`")
_LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")
_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_HEADING = re.compile(r"^#{1,6}\s+", re.MULTILINE)
_BOLD_ITALIC = re.compile(r"(\*{1,3}|_{1,3})(?=\S)(.+?)(?<=\S)\1")
_STRIKE = re.compile(r"~~(.+?)~~")
_BULLET = re.compile(r"^\s*[-*+]\s+", re.MULTILINE)
_NUMBERED = re.compile(r"^\s*(\d+)[.)]\s+", re.MULTILINE)
_BLOCKQUOTE = re.compile(r"^\s*>\s?", re.MULTILINE)
_HRULE = re.compile(r"^\s*([-*_]\s*){3,}$", re.MULTILINE)
_TABLE_DIVIDER = re.compile(r"^\s*\|?[\s:|-]+\|[\s:|-]*$", re.MULTILINE)


def for_speech(text: str) -> str:
    """Strip markdown syntax so TTS reads flowing prose, not formatting marks."""
    text = _FENCE.sub(" here's the code, shown on screen. ", text)
    text = _IMAGE.sub("", text)
    text = _LINK.sub(r"\1", text)
    text = _INLINE_CODE.sub(r"\1", text)
    text = _HEADING.sub("", text)
    text = _TABLE_DIVIDER.sub("", text)
    # bold/italic can nest (***x***); run until stable
    prev = None
    while prev != text:
        prev = text
        text = _BOLD_ITALIC.sub(r"\2", text)
    text = _STRIKE.sub(r"\1", text)
    text = _HRULE.sub("", text)
    text = _BLOCKQUOTE.sub("", text)
    text = _BULLET.sub("", text)
    text = _NUMBERED.sub(r"\1. ", text)
    # table rows: turn pipes into commas so cells read as a list
    text = re.sub(r"\s*\|\s*", ", ", text)
    text = re.sub(r"(^|[.!?]\s*), ", r"\1", text)  # drop leading commas from pipe rows
    # collapse whitespace; newlines become natural pauses
    text = re.sub(r"\n{2,}", ". ", text)
    text = re.sub(r"\s*\n\s*", ", ", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"(,\s*){2,}", ", ", text)
    text = re.sub(r"([.!?]),", r"\1", text)
    text = re.sub(r",\s*([.!?])", r"\1", text)
    text = re.sub(r"\.\s*\.", ".", text)
    return text.strip(" ,\t\n")


def has_open_fence(text: str) -> bool:
    """True while a ``` code fence is still open (don't flush mid-block)."""
    return text.count("```") % 2 == 1
