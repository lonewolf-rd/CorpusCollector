from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from src.utils.adapters.driver import DriverEngine
from src.utils.config_manager import ConfigManager
from selenium.webdriver.common.by import By
from src.utils.logger import AppLogger
from typing import Dict, List, Optional, Union
from pathlib import Path
from bs4 import BeautifulSoup
from tqdm import tqdm
import time, json, os, requests
from lxml import html




class NewsCrawler:
    FILE_PATH = f"{Path(__file__).parent.parent.parent}/data/news_content.txt"

    def __init__(self):
        self.cfg_loader = ConfigManager().cfg
        self.driver = DriverEngine().driver
        self.logger = AppLogger()

        # configs
        self.root_url: str = self.cfg_loader.news.base_url
        self.driver_timeout: int = self.cfg_loader.news.timeout
        self.next_button: str = self.cfg_loader.news.next_button
        self.news_hrefs_container: str = self.cfg_loader.news.news_hrefs

        self.title_path: str = self.cfg_loader.news.title_path
        self.spot_path: str = self.cfg_loader.news.spot_path
        self.body_path: str = self.cfg_loader.news.body_path

        self.news_file = open(self.FILE_PATH, "a", encoding="utf-8")
        self.href_links: set = set()

    def open_website(self) -> None:
        try:
            self.driver.get(url=self.root_url)
            self.logger.info("[NewsCrawler](open_website) Website Opened")

        except Exception as err:
            self.logger.warning(
                f"[NewsCrawler](open_website) Unable To Open - ({self.root_url})... Check URL"
            )
            raise err

    def scrape_news_content(self, news_link: str) -> Union[str, None]:
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(news_link, headers=headers, timeout=10)

            if response.status_code != 200:
                self.logger.warning(f"[NewsCrawler] Status Code: {response.status_code} for {news_link}")
                return None

            tree = html.fromstring(response.content)
            title_list = tree.xpath(self.title_path)
            title_text = title_list[0].text_content().strip() if title_list else ""

            spot_list = tree.xpath(self.spot_path)
            spot_text = spot_list[0].text_content().strip() if spot_list else ""

            body_elements = tree.xpath(self.body_path)
            body_placeholder = " ".join([el.text_content().strip() for el in body_elements])

            if not title_text and not body_placeholder:
                return None

            return f"{title_text}. {spot_text}. {body_placeholder}"

        except Exception as err:
            self.logger.error(f"[NewsCrawler](scrape_news_content) LXML Error: {err}")
            return None

    def collect_news_hrefs(self) -> None:
        try:
            page_count: int = 1
            while True:
                news_elements = self.driver.find_elements(By.XPATH, self.news_hrefs_container)
                for element in news_elements:
                    href = element.get_attribute("href")
                    if href:
                        self.href_links.add(href)
                        self.logger.info(f"[NewsCrawler](collect_news_hrefs) Link Collected... Current Link Count -> {len(self.href_links)}")

                try:
                    next_btn = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, self.next_button))
                    )
                    next_btn.click()
                    page_count += 1
                    time.sleep(1)
                except TimeoutException:
                    self.logger.info("[NewsCrawler](collect_news_hrefs) Pagination ended.")
                    self.logger.info(f"[NewsCrawler](collect_news_hrefs) Total Link Count -> {len(self.href_links)}")
                    break

        except Exception as err:
            self.logger.error(f"[NewsCrawler](collect_news_hrefs) Unexpected Error: {err}")
            raise err

    def begin_crawling(self):
        try:
            self.open_website()
            self.collect_news_hrefs()

            with open(self.FILE_PATH, "a", encoding="utf-8") as f:
                for link in tqdm(self.href_links, desc="Processing News"):
                    news_content = self.scrape_news_content(news_link=link)

                    if news_content:
                        f.write(news_content + "\n")
                        f.flush()

            self.logger.info("Crawling completed successfully.")

        except Exception as err:
            self.logger.error(f"[NewsCrawler](begin_crawling) Unexpected Error: {err}")
            raise err
        finally:
            if self.driver:
                self.driver.quit()


if __name__ == "__main__":
    news_crawler = NewsCrawler()
    news_crawler.begin_crawling()
