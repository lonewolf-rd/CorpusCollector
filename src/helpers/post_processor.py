from src.utils.logger import AppLogger
from typing import Tuple, List
from pathlib import Path
import json, glob, os


class PostProcessor:
    _BASE_DIR_PATH: Path = Path(__file__).parent.parent.parent / "data"

    def __init__(self):
        self.logger = AppLogger()

    @staticmethod
    def _detect_files(dir_root: Path = _BASE_DIR_PATH) -> Tuple[List[str], List[str]]:
        txt_list: List[str] = []
        json_list: List[str] = []

        if not dir_root.exists():
            return [], []

        for file_path in dir_root.iterdir():
            if file_path.is_file():
                if file_path.suffix == ".txt":
                    txt_list.append(str(file_path))
                elif file_path.suffix == ".json":
                    json_list.append(str(file_path))

        return txt_list, json_list

    def prepare_tokenizer_data(self, output_file="corpus.txt"):
        txt_files, json_files = self._detect_files()
        total_lines = 0

        with open(output_file, "w", encoding="utf-8") as outfile:
            for txt_f in txt_files:
                try:
                    with open(txt_f, "r", encoding="utf-8") as f:
                        for line in f:
                            clean_line = line.strip()
                            if clean_line:
                                outfile.write(clean_line + "\n")
                                total_lines += 1
                except Exception as e:
                    self.logger.error(f"[PostProcessor] Error While Processing -> {txt_f}.\n Error:\n{e}")

            for json_f in json_files:
                try:
                    with open(json_f, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            for sublist in data:
                                if isinstance(sublist, list):
                                    for text in sublist:
                                        if isinstance(text, str) and text.strip():
                                            clean_text = " ".join(text.split())
                                            outfile.write(clean_text + "\n")
                                            total_lines += 1
                except Exception as e:
                    self.logger.error(f"[PostProcessor] Error While Processing -> {json_f}.\n Error:\n{e}")

    @staticmethod
    def sanitize_corpus(file_path):
        with open(file_path, 'rb') as f:
            content = f.read()
        clean_content = content.decode('utf-8', 'ignore').encode('utf-8')
        with open(file_path, 'wb') as f:
            f.write(clean_content)
