from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from src.utils.adapters.driver import DriverEngine
from src.helpers.lang_detector import LangDetector
from src.utils.config_manager import ConfigManager
from selenium.webdriver.common.by import By
from src.utils.logger import AppLogger
from tqdm import tqdm
import time


class ArticleCrawler:

    def __init__(self):
        self.driver = DriverEngine().driver
        self.logger = AppLogger()

        self.cfg_loader = ConfigManager().cfg
        self.lang_detector = LangDetector()
        self.logger = AppLogger()
        self._init_driver()

        self._pagination_count: int = 1
        self._pagination_root: str = "&page="
        self._max_pages: int = 2000000

        self.is_scraping_started: bool = False
        self.is_scraping_proceeding: bool = True
        self.link_count: int = 1

        self.tr_file = open("tr_href_links.txt", "a", encoding="utf-8")
        self.en_file = open("eng_href_links.txt", "a", encoding="utf-8")

        self.tr_seen = set()
        self.en_seen = set()

    def wait_for_page_ready(self):
        WebDriverWait(self.driver, self.cfg_loader.driver.timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )

    def scrape_article(self):
        try:
            WebDriverWait(self.driver, self.cfg_loader.driver.timeout).until(
                EC.presence_of_element_located(
                    (By.XPATH, self.cfg_loader.xpaths.article_cards)
                )
            )
        except TimeoutException:
            self.logger.info(
                "[DriverEngine](scrape_article) No articles found on page."
            )
            return 0

        articles = self.driver.find_elements(
            By.XPATH, self.cfg_loader.xpaths.article_cards
        )
        if not articles:
            return 0

        for article in tqdm(articles, desc="Article", leave=False):
            for _ in range(2):
                try:
                    link_el = article.find_element(
                        By.XPATH, self.cfg_loader.xpaths.article_title
                    )
                    title = link_el.text.strip()

                    if not title:
                        continue

                    href = link_el.get_attribute("href")

                    if not href:
                        self.logger.info(
                            "[DriverEngine](scrape_article) Either Hyperlink Is Broken Or Title Is Missing!"
                        )
                        continue

                    if self.lang_detector.detect_lang(text=title):
                        if href not in self.tr_seen:
                            self.tr_seen.add(href)
                            self.tr_file.write(href + "\n")
                            self.link_count += 1
                    else:
                        if href not in self.en_seen:
                            self.en_seen.add(href)
                            self.en_file.write(href + "\n")
                            self.link_count += 1

                    continue

                except StaleElementReferenceException:
                    time.sleep(0.1)
                    continue

                except Exception:
                    self.logger.debug(
                        "[DriverEngine](scrape_article) Card parse failed, skipping."
                    )
                    break

        self.tr_file.flush()
        self.en_file.flush()
        return len(articles)

    def check_pagination_end(self) -> bool:
        try:
            self.driver.find_element(By.XPATH, self.cfg_loader.xpaths.no_result_id)
            return True
        except Exception:
            return False

    def start_crawling(self):
        try:
            self.logger.info(
                f"[DriverEngine](start_crawling) Crawling started: {self.cfg_loader.xpaths.base_url}"
            )

            while (
                self.is_scraping_proceeding
                and self._pagination_count <= self._max_pages
            ):

                if not self.is_scraping_started:
                    url = self.cfg_loader.xpaths.base_url
                    self.is_scraping_started = True
                else:
                    url = f"{self.cfg_loader.xpaths.base_url}{self._pagination_root}{self._pagination_count}"

                self.driver.get(url)
                self.wait_for_page_ready()

                if self.check_pagination_end():
                    self.logger.info("[DriverEngine](start_crawling) Pagination ended.")
                    break

                count = self.scrape_article()
                if count == 0:
                    self.logger.info(
                        "[DriverEngine](start_crawling) No articles parsed, stopping."
                    )
                    break

                self._pagination_count += 1
                time.sleep(0.7)

        finally:
            if self.driver:
                self.driver.quit()
            self.tr_file.close()
            self.en_file.close()
            self.logger.info("[DriverEngine](start_crawling) Driver closed cleanly.")
