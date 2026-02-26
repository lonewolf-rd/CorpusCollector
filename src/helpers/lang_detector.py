from langdetect import detect
from typing import Dict


class LangDetector:

    def __init__(self):
        self.lang_mapping: Dict[str, bool] = {"tr": True}

    def detect_lang(self, text: str) -> bool:
        try:
            language: str = detect(text=text)
            is_turkish: bool = self.lang_mapping.get(language)
            if is_turkish:
                return True

            return False

        except Exception:
            return False
