from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from src.utils.adapters.driver import DriverEngine
from src.utils.config_manager import ConfigManager
from selenium.webdriver.common.by import By
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.utils.logger import AppLogger
from typing import Optional, List, Union
from PyPDF2 import PdfReader
from pathlib import Path
from io import BytesIO
from tqdm import tqdm
import time, requests, re


class ArticleParser:
    _DEFAULT_TR_LINK_PATH: str = (
        f"{Path(__file__).parent.parent.parent}/tr_href_links.txt"
    )

    def __init__(self, href_path: Optional[str] = _DEFAULT_TR_LINK_PATH):

        self.cfg_loader = ConfigManager().cfg
        self.logger = AppLogger()
        self.driver = DriverEngine().driver
        self.href_path = href_path

        self.article_hrefs: List[str] = [""]
        self.article_ids: List[int] = []
        self._load_article_links()

    def _load_article_links(self):
        try:
            with open(file=self.href_path, mode="r", encoding="utf-8") as file:
                self.article_hrefs = [
                    line.strip() for line in file.readlines() if line.strip()
                ]

        except FileNotFoundError as path_error:
            self.logger.error(
                f"[ArticleParser](_load_article_links)Check The Provided File Path - ({self.href_path})"
            )
            raise path_error

    @staticmethod
    def _extract_sections(full_text: str) -> Union[str, None]:

        normalized_text = full_text.casefold()
        normalized_text = re.sub(r"\s+", " ", normalized_text)

        abstract = None
        body = None

        abstract_match = re.search(
            r"\böz \b(.*?)\banahtar kelimeler\b",
            normalized_text,
            re.DOTALL,
        )

        if abstract_match:
            abstract = abstract_match.group(1).strip()

        body_match = re.search(
            r"\bgiriş\b(.*?)\bkaynaklar\b",
            normalized_text,
            re.DOTALL,
        )

        if body_match:
            body = body_match.group(1).strip()

        if not abstract and not body:
            return None

        return f"{abstract or ''}\n{body or ''}".strip()

    def _parse_text(self, response) -> Union[str, None]:
        pdf_bytes = BytesIO(initial_bytes=response.content)
        reader = PdfReader(pdf_bytes)

        full_text: str = ""
        for page in reader.pages:
            text: str = page.extract_text()
            if text:
                full_text += text.strip() + "\n"

        if not full_text.strip():
            return None

        else:
            parsed_article = self._extract_sections(full_text=full_text)
            return parsed_article

    def _request_article_pdf(self, article_id: int) -> str:
        _request_url: str = f"{self.cfg_loader.urls.article_root}{article_id}"
        try:
            response = requests.get(
                url=_request_url, timeout=self.cfg_loader.urls.timeout
            )
            try:
                cleaned_text = self._parse_text(response)
                return cleaned_text

            except Exception as parsing_err:
                self.logger.error(
                    f"[ArticleParser](_request_article_pdf) Couldn't Parse Article - ({article_id})"
                )

        except TimeoutException as timeout_err:
            self.logger.error(
                f"[ArticleParser](_request_article_pdf) Failed To Request Article - ({article_id})"
            )
            raise timeout_err

    def _collect_article_id(self) -> int:
        article_id: Union[int, None] = None

        article_link_element = self.driver.find_element(
            By.XPATH, self.cfg_loader.xpaths.pdf_path
        )
        if article_link_element:
            full_href: str = article_link_element.get_attribute("href")
            article_id: int = full_href.split("article-file/")

        return article_id[1]

    def _check_file_content(self):
        WebDriverWait(driver=self.driver, timeout=self.cfg_loader.driver.timeout).until(
            EC.visibility_of_element_located(
                (By.XPATH, self.cfg_loader.xpaths.text_layer_path)
            )
        )

    def parse_pdf(self, article_url: str):
        self.driver.get(article_url)
        time.sleep(1)
        article_id: int = self._collect_article_id()
        pdf_content = self._request_article_pdf(article_id)

        return pdf_content

    def start_parsing(self):
        corpus_parts: List[str] = []

        for link in tqdm(self.article_hrefs, desc="Article Count: "):
            try:
                parsed_text = self.parse_pdf(article_url=link)

                if parsed_text:
                    corpus_parts.append(parsed_text)

            except Exception as e:
                self.logger.error(f"Parse error for {link}: {e}")

        final_corpus = "\n\n".join(corpus_parts)

        with open("article_corpus.txt", "w", encoding="utf-8") as f:
            f.write(final_corpus)

        self.logger.info("[ArticleParser](start_parsing) Parsing Complete!")
