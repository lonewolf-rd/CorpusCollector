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
from tqdm import tqdm
import time, json, os


class FormCrawler:
    _SCRIPT_PATH: str = f"{Path(__file__).parent.parent}/utils/scripts/commentParser.js"
    _JSON_PATH: str = f"{Path(__file__).parent.parent.parent}/data/eksisozluk.json"

    def __init__(self):
        self.cfg_loader = ConfigManager().cfg
        self.driver = DriverEngine().driver
        self.logger = AppLogger()

        # configs
        self._root_url: str = self.cfg_loader.form_driver.root_url
        self._driver_timeout: int = self.cfg_loader.form_driver.timeout
        self._min_length: int = self.cfg_loader.form_driver.min_length
        self._topic_path: str = self.cfg_loader.form_xpaths.topic_list

        # javascripts
        self._content_parser_script: Union[None, str] = None
        self._sd_script: str = self.cfg_loader.javascripts.scroll_down  # scrolldown

        # outer vars
        self.crawling_year: List[int] = []
        self.is_more_button: bool = False

        # inner vars
        self.is_next_button: bool = False
        self.page_num: int = 1
        self.thread_comments = []

        self._load_js_script()

    def _load_js_script(self):
        try:
            with open(file=self._SCRIPT_PATH, mode="r", encoding="utf-8") as f:
                self._content_parser_script = f.read()

        except FileNotFoundError as file_err:
            self.logger.error(
                f"[FormCrawler](_load_js_script) JS Script Couldn't Be Located: {file_err}"
            )

        if self._content_parser_script:
            self.logger.info(
                "[FormCrawler](_load_js_script) JS Script Loaded Successfully"
            )

    def _open_website(self) -> None:
        try:
            self.driver.get(url=self._root_url)
            self.logger.info("[FormCrawler](_open_website) Website Opened")

        except Exception as err:
            self.logger.warning(
                f"[FormCrawler](_open_website) Unable To Open - ({self._root_url})... Check URL"
            )
            raise err

    def _retrieve_year_data(self) -> None:
        try:
            _year_list = WebDriverWait(
                driver=self.driver, timeout=self._driver_timeout
            ).until(
                EC.presence_of_all_elements_located(
                    locator=(By.XPATH, self.cfg_loader.form_xpaths.year_dropdown)
                )
            )

            self.logger.info(
                "[FormCrawler](_retrieve_year_data) Year Dropdown Has Been Located"
            )
            for year in _year_list:
                self.crawling_year.append(year.text)

            self.logger.info(
                f"[FormCrawler](_retrieve_year_data) A total of - ({len(self.crawling_year)}) Years of Data Found!"
            )

        except Exception as not_found_err:
            self.logger.error(
                "[FormCrawler](_retrieve_year_data) Unable To Locate Year Dropdown!"
            )
            raise not_found_err

    def _set_year(self, selected_year: str):
        try:
            dropdown_element = WebDriverWait(self.driver, self._driver_timeout).until(
                EC.presence_of_element_located(
                    (By.XPATH, self.cfg_loader.form_xpaths.year_container)
                )
            )

            select = Select(dropdown_element)
            select.select_by_value(selected_year)

            WebDriverWait(self.driver, self._driver_timeout).until(
                EC.text_to_be_present_in_element(
                    (By.XPATH, self.cfg_loader.form_xpaths.selected_year), selected_year
                )
            )

            self.logger.info(f"[FormCrawler](_set_year) Year set to {selected_year}")

        except Exception as e:
            self.logger.error(
                f"[FormCrawler](_set_year) Failed to set year {selected_year}"
            )
            raise e

    def _next_thread(self):
        try:
            WebDriverWait(driver=self.driver, timeout=self._driver_timeout).until(
                EC.element_to_be_clickable(
                    mark=(By.XPATH, self.cfg_loader.form_xpaths.next_page_button)
                )
            ).click()
            self.logger.info("[FormCrawler](_next_thread) Moving On The Next Thread")

        except Exception:
            self.logger.error(
                "[FormCrawler](_next_thread) Next Thread Button Coulnd't Found"
            )
            pass

    def _scroll_down(self) -> None:
        try:
            self.driver.execute_script(self._sd_script)
            self.logger.info("[FormCrawler](_scroll_down) Scrolling Down")

        except Exception as driver_err:
            self.logger.error("[FormCrawler](_scroll_down) Unable to Scroll Down!")
            raise driver_err

    def _close_popup(self):
        try:
            WebDriverWait(driver=self.driver, timeout=self._driver_timeout).until(
                EC.element_to_be_clickable(
                    mark=(By.XPATH, self.cfg_loader.form_xpaths.popup)
                )
            ).click()
            self.logger.warning("[FormCrawler](_close_popup) Located Popup! Closing...")
        except Exception:
            self.logger.info("[FormCrawler](_close_popup) Didn't Encounter Any Popups")
            pass

    def _click_more_button(self) -> None:
        self._close_popup()

        try:
            _is_more_button = WebDriverWait(
                driver=self.driver, timeout=self._driver_timeout
            ).until(
                EC.element_to_be_clickable(
                    mark=(By.XPATH, self.cfg_loader.form_xpaths.more_button)
                )
            )
            if _is_more_button:
                self.logger.info(
                    "[FormCrawler](_click_more_button) Sidebar 'More' Button Has Been Located"
                )
                _is_more_button.click()
                self.is_more_button = True

            else:
                self.logger.warning(
                    "[FormCrawler](_click_more_button) 'More' Button Hasn't Been Located"
                )
                self.is_more_button = False

        except Exception as driver_err:
            self.logger.error("[FormCrawler](_click_more_button) Couldn't Find 'More' ")
            self.is_more_button = False
            raise driver_err

    def _locate_topics(self) -> Union[None, List[str]]:
        topic_links: List[str] = []
        try:
            _topic_list = WebDriverWait(
                driver=self.driver, timeout=self._driver_timeout
            ).until(
                EC.presence_of_all_elements_located(
                    locator=(By.XPATH, self._topic_path)
                )
            )
            if _topic_list:
                for topic in tqdm(iterable=_topic_list, desc="Topic Count"):
                    topic_links.append(topic.get_attribute("href"))

                return topic_links

            else:
                self.logger.warning(
                    "[FormCrawler](_locate_topics) Unable To Locate Topic Hrefs!"
                )
                return None

        except Exception as driver_err:
            pass

    def _enter_topic(self, topic_link: str):
        try:
            main_window = self.driver.current_window_handle

            self.driver.get(topic_link)
            self.logger.info(
                f"[FormCrawler](_enter_topic) Navigated to topic: {topic_link}"
            )

            return main_window

        except Exception as tab_err:
            self.logger.error(
                f"[FormCrawler](_enter_topic) Failed to enter topic {topic_link}"
            )
            raise tab_err

    def _get_back(self, main_window: str):
        try:
            self.driver.back()
            self.logger.info("[FormCrawler](_get_back) Returned to main page")

        except Exception as e:
            self.logger.error("[FormCrawler](_get_back) Failed to go back")
            raise e

    def _locate_next_button(self) -> bool:
        try:
            _is_clickable = WebDriverWait(
                driver=self.driver, timeout=self._driver_timeout
            ).until(
                EC.element_to_be_clickable(
                    mark=(By.XPATH, self.cfg_loader.form_xpaths.next_button)
                )
            )

            if _is_clickable:
                return True

            return False

        except Exception:
            return False

    def _next_page(self):
        try:
            WebDriverWait(driver=self.driver, timeout=self._driver_timeout).until(
                EC.element_to_be_clickable(
                    mark=(By.XPATH, self.cfg_loader.form_xpaths.next_button)
                )
            ).click()

            self.logger.info(
                "[FormCrawler](_next_page) Pagination Located, Clicking..."
            )

        except Exception:
            self.logger.warning("[FormCrawler](_next_page) Pagination Has Ended")

    def _collect_comments(self):
        comment_list: List[str] = []

        try:
            _content_containers = WebDriverWait(
                driver=self.driver, timeout=self._driver_timeout
            ).until(
                EC.presence_of_all_elements_located(
                    locator=(By.XPATH, self.cfg_loader.form_xpaths.content_body)
                )
            )

            if isinstance(_content_containers, List):
                for content in _content_containers:
                    parsed_nodes = self.driver.execute_script(
                        self._content_parser_script, content
                    )

                    comment_parts = []

                    for node in parsed_nodes:
                        if node["type"] in ("text", "b", "url"):
                            comment_parts.append(node["value"])

                    full_comment = " ".join(comment_parts)
                    comment_list.append(full_comment)

                self.logger.info(
                    f"[FormCrawler](_collect_comments) Total Comments Collected - ({len(comment_list)})"
                )

                return comment_list

        except Exception as container_err:
            self.logger.error(
                "[FormCrawler](_collect_comments) Couldn't Find Any Comment Containers!"
            )
            raise container_err

    def _move_to_next_comment(self):
        try:
            WebDriverWait(driver=self.driver, timeout=self._driver_timeout).until(
                EC.element_to_be_clickable(
                    mark=(By.XPATH, self.cfg_loader.form_xpaths.next_button)
                )
            ).click()
            self.logger.info(
                "[FormCrawler](_move_to_next_comment) Moving To Next Comment Page"
            )

        except Exception:
            self.logger.warning(
                "[FormCrawler](_move_to_next_comment) Couldn't Locate Next Button"
            )
            pass

    def _write_thread(self, thread_comments: List[str]) -> None:
        try:

            if not os.path.exists(self._JSON_PATH):
                with open(self._JSON_PATH, "w", encoding="utf-8") as f:
                    json.dump([thread_comments], f, ensure_ascii=False)

            else:
                with open(self._JSON_PATH, "r+", encoding="utf-8") as f:
                    data = json.load(f)
                    data.append(thread_comments)
                    f.seek(0)
                    json.dump(data, f, ensure_ascii=False)
                    f.truncate()

            self.logger.info(
                f"[FormCrawler](_write_thread) Thread saved ({len(thread_comments)} comments)"
            )

        except Exception as e:
            self.logger.error("[FormCrawler](_write_thread) Failed to write thread")
            raise e

    def _kill_ads(self) -> None:
        try:
            self.driver.execute_script(
                """
                document.querySelectorAll('iframe').forEach(el => {
                    const rect = el.getBoundingClientRect();
                    const src = el.src || '';
                    const isAd = (
                        src.includes('doubleclick') ||
                        src.includes('googlesyndication') ||
                        src.includes('adservice') ||
                        src.includes('adsystem') ||
                        rect.width >= 250 && rect.height <= 280
                    );
                    if (isAd) el.remove();
                });

                document.querySelectorAll([
                    '[id^="google_ads"]',
                    '[id^="div-gpt-ad"]',
                    '.advertisement',
                    '[data-ad-unit]',
                    'ins.adsbygoogle'
                ].join(',')).forEach(el => el.remove());
                """
            )
            self.logger.info("[FormCrawler](_kill_ads) Ads cleared")
        except Exception:
            pass

    def begin(self):
        self._open_website()
        time.sleep(1)
        self._kill_ads()
        self._retrieve_year_data()

        for year in tqdm(iterable=self.crawling_year, desc="Year Iteration"):
            self._scroll_down()
            self._click_more_button()
            self._set_year(selected_year=year)
            topic_list: List = self._locate_topics()

            for topic_link in topic_list:
                self.thread_comments = []

                self._enter_topic(topic_link=topic_link)
                self._kill_ads()
                self.is_more_button = self._locate_next_button()

                while self.is_more_button:
                    page_comments = self._collect_comments()
                    self.thread_comments.extend(page_comments)
                    time.sleep(1)
                    self._move_to_next_comment()
                    time.sleep(1)
                    self._kill_ads()
                    is_button_available = self._locate_next_button()
                    if not is_button_available:
                        self.is_more_button = False
                        break

                self._write_thread(self.thread_comments)
                self.driver.execute_script("window.gc && window.gc();")
                time.sleep(0.5)

            self._next_thread()


if __name__ == "__main__":
    crawler = FormCrawler()
    crawler.begin()
