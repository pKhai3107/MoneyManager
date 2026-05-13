from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from urllib import error, parse, request


ROOT = Path(__file__).resolve().parents[1]
I18N_DIR = ROOT / "i18n"
SUPPORTED_LANGS = ("vi", "en")


class TranslationError(RuntimeError):
    pass


class Translator:
    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        raise NotImplementedError


class OpenAITranslator(Translator):
    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        prompt = (
            f"Translate the following UI text from {source_lang} to {target_lang}. "
            "Preserve placeholders like {amount}, HTML tags like <br>, and punctuation. "
            "Return only the translated text.\n\n"
            f"Text: {text}"
        )
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a precise translation engine for UI strings."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
        }
        req = request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=60) as response:
                data = json.loads(response.read().decode("utf-8"))
        except error.URLError as exc:
            raise TranslationError(f"OpenAI request failed: {exc}") from exc

        try:
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise TranslationError(f"Unexpected OpenAI response: {data}") from exc


class DeepLTranslator(Translator):
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        source_code = "VI" if source_lang == "vi" else "EN"
        target_code = "VI" if target_lang == "vi" else "EN"
        payload = parse.urlencode(
            {
                "auth_key": self.api_key,
                "text": text,
                "source_lang": source_code,
                "target_lang": target_code,
            }
        ).encode("utf-8")
        req = request.Request(
            "https://api-free.deepl.com/v2/translate",
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=60) as response:
                data = json.loads(response.read().decode("utf-8"))
        except error.URLError as exc:
            raise TranslationError(f"DeepL request failed: {exc}") from exc

        try:
            return data["translations"][0]["text"].strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise TranslationError(f"Unexpected DeepL response: {data}") from exc


class PassthroughTranslator(Translator):
    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        return text


def load_json(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise TranslationError(f"{path} must contain a JSON object")
    return {str(key): str(value) for key, value in data.items()}


def save_json(path: Path, data: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def choose_translator(provider: str) -> Translator:
    if provider == "none":
        return PassthroughTranslator()

    if provider == "openai":
        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise TranslationError("OPENAI_API_KEY is required for provider=openai")
        model = os.environ.get("OPENAI_TRANSLATION_MODEL", "gpt-4.1-mini")
        return OpenAITranslator(api_key, model)

    if provider == "deepl":
        api_key = os.environ.get("DEEPL_API_KEY", "").strip()
        if not api_key:
            raise TranslationError("DEEPL_API_KEY is required for provider=deepl")
        return DeepLTranslator(api_key)

    raise TranslationError(f"Unknown provider: {provider}")


def merge_translations(source: dict[str, str], target: dict[str, str], translator: Translator, source_lang: str, target_lang: str) -> tuple[dict[str, str], list[str]]:
    merged = dict(target)
    warnings: list[str] = []
    for key, source_value in source.items():
        translated = translator.translate(source_value, source_lang, target_lang)
        merged[key] = translated
        if translated == source_value and translator.__class__ is PassthroughTranslator:
            warnings.append(f"{key}: copied source text because no translator provider was configured")
    return merged, warnings


def sync_pair(source_lang: str, target_lang: str, provider: str) -> list[str]:
    source_path = I18N_DIR / f"{source_lang}.json"
    target_path = I18N_DIR / f"{target_lang}.json"
    source = load_json(source_path)
    target = load_json(target_path)
    translator = choose_translator(provider)
    merged, warnings = merge_translations(source, target, translator, source_lang, target_lang)
    save_json(target_path, merged)
    return warnings


def sync_both(provider: str) -> list[str]:
    warnings: list[str] = []
    warnings.extend(sync_pair("vi", "en", provider))
    warnings.extend(sync_pair("en", "vi", provider))
    return warnings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync MoneyManager translation files.")
    parser.add_argument("--source", choices=SUPPORTED_LANGS, help="Source language file")
    parser.add_argument("--target", choices=SUPPORTED_LANGS, help="Target language file")
    parser.add_argument("--both", action="store_true", help="Sync both vi->en and en->vi")
    parser.add_argument(
        "--provider",
        choices=("none", "openai", "deepl"),
        default="none",
        help="Translation provider to use when a key is missing",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.both:
        warnings = sync_both(args.provider)
    else:
        if not args.source or not args.target:
            print("Use --source and --target, or --both.", file=sys.stderr)
            return 2
        warnings = sync_pair(args.source, args.target, args.provider)

    if warnings:
        for warning in warnings:
            print(f"WARN: {warning}")
    print("Done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
