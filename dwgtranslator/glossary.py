import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Optional, Set, Union

from .translation_filter import DEFAULT_GLOSSARY


GlossaryInput = Union[str, Iterable[str]]


@dataclass(frozen=True)
class GlossaryConfig:
    terms: Set[str]
    translations: Dict[str, str]

    def translation_for(self, text: str) -> Optional[str]:
        return self.translations.get(_normalize_key(text))


def load_glossary(
    glossary: Optional[GlossaryInput] = None,
    glossary_json: Optional[str] = None,
    glossary_file: Optional[str] = None,
    merge_default: bool = True,
) -> GlossaryConfig:
    """Load glossary terms and fixed translations from direct input and/or JSON files."""
    terms = set(DEFAULT_GLOSSARY) if merge_default else set()
    translations = {}

    if glossary is not None:
        loaded_terms, loaded_translations = _coerce_glossary(glossary)
        terms.update(_normalize_terms(loaded_terms))
        translations.update(_normalize_translations(loaded_translations))
    if glossary_json:
        loaded_terms, loaded_translations = _parse_json_glossary(glossary_json)
        terms.update(_normalize_terms(loaded_terms))
        translations.update(_normalize_translations(loaded_translations))
    if glossary_file:
        loaded_terms, loaded_translations = _load_file_glossary(glossary_file)
        terms.update(_normalize_terms(loaded_terms))
        translations.update(_normalize_translations(loaded_translations))

    return GlossaryConfig(terms=terms, translations=translations)


def _load_file_glossary(file_path: str) -> tuple[Iterable[str], Dict[str, str]]:
    path = Path(file_path).expanduser()
    with path.open('r', encoding='utf-8') as f:
        return _glossary_from_json_value(json.load(f))


def _parse_json_glossary(value: str) -> tuple[Iterable[str], Dict[str, str]]:
    try:
        return _glossary_from_json_value(json.loads(value))
    except json.JSONDecodeError:
        # Convenient shorthand for CLI usage: --glossary-json ODF,PDU,CCU
        return [item.strip() for item in value.split(',')], {}


def _coerce_glossary(value: GlossaryInput) -> tuple[Iterable[str], Dict[str, str]]:
    if isinstance(value, str):
        return _parse_json_glossary(value)
    return value, {}


def _glossary_from_json_value(value) -> tuple[Iterable[str], Dict[str, str]]:
    if isinstance(value, list):
        return value, {}
    if isinstance(value, dict):
        if 'terms' not in value and 'translations' not in value:
            raise ValueError("Glossary JSON object must include 'terms' and/or 'translations'")
        terms = value.get('terms', [])
        translations = value.get('translations', {})
        if not isinstance(terms, list):
            raise ValueError("Glossary JSON field 'terms' must be a list")
        if not isinstance(translations, dict):
            raise ValueError("Glossary JSON field 'translations' must be an object")
        return terms, translations
    raise ValueError("Glossary JSON must be a list or an object with 'terms' and/or 'translations'")


def _normalize_terms(terms: Iterable[str]) -> Set[str]:
    normalized = set()
    for term in terms:
        if term is None:
            continue
        value = str(term).strip()
        if value:
            normalized.add(value.upper())
    return normalized


def _normalize_translations(translations: Dict[str, str]) -> Dict[str, str]:
    normalized = {}
    for source, target in translations.items():
        source_key = _normalize_key(source)
        target_value = str(target).strip() if target is not None else ''
        if source_key and target_value:
            normalized[source_key] = target_value
    return normalized


def _normalize_key(value: str) -> str:
    return re.sub(r'\s+', ' ', str(value).replace('\\P', ' ')).strip().upper()
