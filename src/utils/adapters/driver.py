from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchDriverException
from src.utils.config_manager import ConfigManager
from selenium.webdriver.common.by import By
from src.utils.logger import AppLogger
import undetected_chromedriver as uc
from typing import Union, Any

class DriverAdapter:

    def __init__(self):
        self.driver: Union[Any, None] = None

        self.cfg_loader = ConfigManager().cfg
        self.logger = AppLogger()
        self._init_driver()

    def _init_driver(self):
        try:
            _options = uc.ChromeOptions()
            self.driver = uc.Chrome(options=_options, version_main=self.cfg_loader.driver.version)
            self.logger.info("[DriverAdapter](_init_driver) Undetected Chrome Driver Initialized")

        except NoSuchDriverException as driver_err:
            self.logger.error("[DriverAdapter](_init_driver) Error While Initializing Driver!")
            raise driver_err

    