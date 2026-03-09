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

        # outer vars
        self.crawling_year: List[int] = []
        self.is_next_button: bool = False
        self.topic_list: List[str] = []

        # inner vars
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

    def _next_entry_page(self):
        try:
            WebDriverWait(driver=self.driver, timeout=self._driver_timeout).until(
                EC.element_to_be_clickable(
                    mark=(By.XPATH, self.cfg_loader.form_xpaths.next_button)
                )
            ).click()

        except Exception:
            self.logger.warning(
                "[FormCrawler](_next_entry_page) Next Entry Button Coulnd't Found"
            )
            pass

    def _next_thread_page(self):
        try:
            WebDriverWait(driver=self.driver, timeout=self._driver_timeout).until(
                EC.element_to_be_clickable(
                    mark=(By.XPATH, self.cfg_loader.form_xpaths.next_page_button)
                )
            ).click()

        except Exception:
            self.logger.warning(
                "[FormCrawler](_next_thread) Next Thread Button Coulnd't Found"
            )
            pass

    def _scroll_down(self) -> None:
        try:
            for _ in range(3):
                self.driver.execute_script(
                    """
                    const sidebar = document.querySelector('div#index-section div');
                    if (sidebar) {
                        sidebar.style.overflow = 'auto';
                        sidebar.scrollTop = sidebar.scrollHeight;
                    }
                """
                )
                time.sleep(1)
            self.logger.info("[FormCrawler](_scroll_down) Scrolling Down")

        except Exception as driver_err:
            self.logger.error("[FormCrawler](_scroll_down) Unable to Scroll Down!")
            raise driver_err

    def _close_popup(self):
        try:
            WebDriverWait(driver=self.driver, timeout=2).until(
                EC.element_to_be_clickable(
                    mark=(By.XPATH, self.cfg_loader.form_xpaths.popup)
                )
            ).click()
            self.logger.warning("[FormCrawler](_close_popup) Located Popup! Closing...")
        except Exception:
            pass

    def _is_page_responsive(self) -> bool:
        try:
            result = self.driver.execute_script("return document.readyState;")
            return result == "complete"
        except Exception:
            return False

    def _retry(self, func, retries: int = 3, *args, **kwargs):
        for attempt in range(retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                self.logger.warning(
                    f"[FormCrawler](_retry) Attempt {attempt + 1} failed: {func.__name__}"
                )
                if attempt < retries - 1:
                    self._safe_refresh()
                    time.sleep(2)
                else:
                    raise e

    def _safe_refresh(self) -> None:
        try:
            current_url = self.driver.current_url
            self.driver.refresh()
            WebDriverWait(self.driver, self._driver_timeout).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            self.logger.info("[FormCrawler](_safe_refresh) Page Refreshed")
        except Exception as e:
            self.logger.error("[FormCrawler](_safe_refresh) Refresh Failed")
            raise e

    def _click_more_thread_button(self) -> bool:
        try:
            _more_button = WebDriverWait(
                driver=self.driver, timeout=self._driver_timeout
            ).until(
                EC.presence_of_element_located(
                    locator=(By.XPATH, self.cfg_loader.form_xpaths.more_button)
                )
            )
            if _more_button:
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center'});", _more_button
                )
                time.sleep(0.5)
                self.driver.execute_script("arguments[0].click();", _more_button)
                self.logger.info(
                    "[FormCrawler](_click_more_thread_button) Sidebar 'More' Button Clicked"
                )
                return True
            else:
                self.logger.warning(
                    "[FormCrawler](_click_more_thread_button) 'More' Button Hasn't Been Located"
                )
                return False

        except Exception:
            self.logger.error(
                "[FormCrawler](_click_more_thread_button) Couldn't Find 'More' Button"
            )
            return False

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
                for topic in _topic_list:
                    topic_links.append(topic.get_attribute("href"))

                return topic_links

            else:
                self.logger.warning(
                    "[FormCrawler](_locate_topics) Unable To Locate Topic Hrefs!"
                )
                return None

        except Exception as driver_err:
            None

    def _wait_for_new_topics(self, expected_page: int) -> None:
        try:
            if expected_page == 1:
                return

            WebDriverWait(self.driver, self._driver_timeout).until(
                EC.presence_of_element_located(
                    (By.XPATH, f"//div[@data-currentpage='{expected_page}']")
                )
            )
            self.logger.info(
                f"[FormCrawler](_wait_for_new_topics) Page {expected_page} loaded"
            )
        except Exception:
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

    def _locate_next_entry_page(self) -> bool:
        try:
            _is_clickable = WebDriverWait(driver=self.driver, timeout=3).until(
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

                return comment_list

        except Exception as container_err:
            self.logger.warning(
                "[FormCrawler](_collect_comments) Couldn't Find Any Comment Containers!"
            )
            pass

    def _next_entry_page(self):
        try:
            element = WebDriverWait(
                driver=self.driver, timeout=self._driver_timeout
            ).until(
                EC.element_to_be_clickable(
                    mark=(By.XPATH, self.cfg_loader.form_xpaths.next_button)
                )
            )
            self.driver.execute_script("arguments[0].click();", element)

            WebDriverWait(self.driver, self._driver_timeout).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )

        except Exception:
            self.logger.warning(
                "[FormCrawler](_next_entry_page) Couldn't Locate Next Button"
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
                // Sadece sayfanın üstünü kapatan fixed/absolute pozisyonlu overlay'leri kaldır
                document.querySelectorAll('*').forEach(el => {
                    const style = window.getComputedStyle(el);
                    const isOverlay = (
                        (style.position === 'fixed' || style.position === 'absolute') &&
                        style.zIndex > 100 &&
                        !el.closest('#index-section') &&
                        !el.closest('#content-body') &&
                        !el.closest('header') &&
                        !el.closest('nav')
                    );
                    if (isOverlay) el.remove();
                });
            """
            )
        except Exception:
            pass

    def collect_thread_links(self):
        href_links: List[str] = []
        self._open_website()
        self._retrieve_year_data()

        for year in self.crawling_year:
            self._set_year(selected_year=year)

            is_thread_ended: bool = False
            is_more_button_clicked: bool = False

            topic_list = self._locate_topics()
            href_links.extend(topic_list)

            self._close_popup()
            self._kill_ads()

            while not is_thread_ended:
                if not is_more_button_clicked:
                    self._close_popup()
                    self._kill_ads()
                    is_more_available: bool = self._click_more_thread_button()

                    if not is_more_available:
                        is_thread_ended = True
                        break
                    is_more_button_clicked = True
                    topic_list = self._locate_topics()
                    href_links.extend(topic_list)

                else:
                    try:
                        self._close_popup()
                        self._kill_ads()
                        self._next_thread_page()
                        topic_list = self._locate_topics()
                        href_links.extend(topic_list)
                    except Exception:
                        is_thread_ended = True

        return href_links

    def begin(self):
        self._open_website()
        self._retrieve_year_data()
        time.sleep(1)
        self._kill_ads()

        for year in self.crawling_year:
            self._set_year(selected_year=year)

            is_thread_ended: bool = False
            is_more_button_clicked: bool = False
            sidebar_page: int = 1
            processed_links: set = set()

            self._kill_ads()
            self.topic_list = self._locate_topics()

            while not is_thread_ended:
                new_topics = [l for l in self.topic_list if l not in processed_links]

                for topic_link in tqdm(
                    iterable=new_topics, desc="Scraping In Progress"
                ):
                    self.thread_comments = []
                    self._enter_topic(topic_link=topic_link)
                    self._kill_ads()
                    try:
                        for _ in range(3):
                            page_comments = self._collect_comments()
                            self.thread_comments.extend(page_comments)
                            time.sleep(0.5)
                    except:
                        pass

                    while self._locate_next_entry_page():
                        self._next_entry_page()
                        self._kill_ads()

                        try:
                            for _ in range(3):
                                page_comments = self._collect_comments()
                                self.thread_comments.extend(page_comments)
                                time.sleep(0.5)
                        except:
                            pass

                    self._write_thread(self.thread_comments)
                    processed_links.add(topic_link)

                if not is_more_button_clicked:
                    self._close_popup()
                    self._kill_ads()
                    is_more_available: bool = self._click_more_thread_button()

                    if not is_more_available:
                        is_thread_ended = True
                        break
                    is_more_button_clicked = True
                    sidebar_page += 1
                    self._wait_for_new_topics(expected_page=sidebar_page)
                    self._close_popup()
                    self._kill_ads()
                    time.sleep(1)
                    self.topic_list = self._locate_topics()

                else:
                    try:
                        self._close_popup()
                        self._kill_ads()
                        self._next_thread_page()
                        sidebar_page += 1
                        self._wait_for_new_topics(expected_page=sidebar_page)
                        self._close_popup()
                        self._kill_ads()
                        time.sleep(1)
                        self.topic_list = self._locate_topics()
                    except Exception:
                        is_thread_ended = True


if __name__ == "__main__":
    crawler = FormCrawler()
    crawler.begin()
