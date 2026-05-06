import re
from dataclasses import dataclass
from typing import Optional, Set


DEFAULT_GLOSSARY: Set[str] = {
    'AC',
    'ALM',
    'CCU',
    'DC',
    'ETH',
    'MCCB',
    'ODF',
    'PDU',
    'PLC',
    'PWR',
    'RUN',
    'SPD',
    'UPS',
}


@dataclass(frozen=True)
class TranslationFilterResult:
    should_translate: bool
    reason: str = ''


_ASCII_LETTER_RE = re.compile(r'[A-Za-z]')
_CJK_RE = re.compile(r'[\u3400-\u9fff]')
_PURE_NUMBER_RE = re.compile(r'^[+-]?\d+(?:\.\d+)?$')
_PAGE_OR_RANGE_RE = re.compile(r'^[A-Za-z]?\d+\s*(?:[/\-]\s*[A-Za-z]?\d+)+$')
_DIMENSION_RE = re.compile(
    r'^(?:[RrΦφ])?\d+(?:\.\d+)?\s*(?:mm|cm|m|km|in|inch|")?$',
    re.IGNORECASE,
)
_SIZE_RE = re.compile(
    r'^\d+(?:\.\d+)?\s*(?:[xX×*])\s*\d+(?:\.\d+)?(?:\s*(?:mm|cm|m|km|in|inch|"))?$',
    re.IGNORECASE,
)
_SCALE_RE = re.compile(r'^\d+\s*:\s*\d+$')
_SLOT_RE = re.compile(r'^(?:\d+U|U\d+)$', re.IGNORECASE)
_ELECTRICAL_VALUE_RE = re.compile(
    r'^[+-]?\d+(?:\.\d+)?\s*(?:V|KV|A|MA|W|KW|HZ|KHZ|OHM|Ω)$',
    re.IGNORECASE,
)
_SIGNAL_RE = re.compile(r'^\d+(?:\.\d+)?\s*-\s*\d+(?:\.\d+)?\s*(?:mA|V|A)$', re.IGNORECASE)
_STANDARD_RE = re.compile(r'^(?:IEC|GB/T|GB|ISO|EN)\s*[-\w./]+$', re.IGNORECASE)
_EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
_URL_RE = re.compile(r'^(?:https?://)?[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?:/\S*)?$')
_FILE_RE = re.compile(r'^[\w.-]+\.(?:dwg|dxf|pdf|xls|xlsx|doc|docx|txt)$', re.IGNORECASE)
_UPPERCASE_TERM_RE = re.compile(r'^[A-Z]{1,8}(?:[-_/]?[A-Z0-9]{1,8})*$')
_EQUIPMENT_ID_RE = re.compile(r'^[A-Z]{1,5}[-_]?\d+[A-Z0-9]*(?::[-A-Z0-9]+)?$', re.IGNORECASE)
_GRID_MARK_RE = re.compile(r'^[A-Z](?:-[A-Z])?$', re.IGNORECASE)
_TECHNICAL_MARK_RE = re.compile(r'^[+\-]?[A-Z0-9][A-Z0-9+\-_/.:]*$')


def should_translate_text(
    text: str,
    source_lang: str = 'auto',
    target_lang: str = 'zh',
    glossary: Optional[Set[str]] = None,
) -> TranslationFilterResult:
    """Return whether text should be sent to a translation API."""
    normalized = _normalize_text(text)
    if not normalized:
        return TranslationFilterResult(False, 'empty')

    target = (target_lang or '').lower()
    terms = DEFAULT_GLOSSARY if glossary is None else glossary
    upper_normalized = normalized.upper()

    if upper_normalized in terms:
        return TranslationFilterResult(False, 'glossary')

    if _is_numeric_or_cad_marker(normalized):
        return TranslationFilterResult(False, 'cad_marker')

    if target.startswith('en') and not _has_cjk(normalized) and _has_ascii_letter(normalized):
        return TranslationFilterResult(False, 'target_language')

    if target.startswith('zh') and _has_cjk(normalized) and not _looks_like_mixed_english_sentence(normalized):
        return TranslationFilterResult(False, 'target_language')

    return TranslationFilterResult(True)


def _normalize_text(text: str) -> str:
    return re.sub(r'\s+', ' ', str(text).replace('\\P', ' ')).strip()


def _has_cjk(value: str) -> bool:
    return bool(_CJK_RE.search(value))


def _has_ascii_letter(value: str) -> bool:
    return bool(_ASCII_LETTER_RE.search(value))


def _is_numeric_or_cad_marker(value: str) -> bool:
    compact = re.sub(r'\s+', '', value)
    return any(
        pattern.match(compact)
        for pattern in (
            _PURE_NUMBER_RE,
            _PAGE_OR_RANGE_RE,
            _DIMENSION_RE,
            _SIZE_RE,
            _SCALE_RE,
            _SLOT_RE,
            _ELECTRICAL_VALUE_RE,
            _SIGNAL_RE,
            _STANDARD_RE,
            _EMAIL_RE,
            _URL_RE,
            _FILE_RE,
            _UPPERCASE_TERM_RE,
            _EQUIPMENT_ID_RE,
            _GRID_MARK_RE,
            _TECHNICAL_MARK_RE,
        )
    )


def _looks_like_mixed_english_sentence(value: str) -> bool:
    return _has_cjk(value) and bool(re.search(r'[A-Za-z]{2,}\s+[A-Za-z]{2,}', value))
