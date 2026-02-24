from selenium.webdriver.support import expected_conditions as EC
from src.utils.config_manager import ConfigManager
from src.utils.logger import AppLogger
import undetected_chromedriver as uc
from typing import Any


class DriverEngine:

    def __init__(self):
        self.driver: Any | None = None
        self.cfg_loader = ConfigManager().cfg
        self.logger = AppLogger()
        self._init_driver()

    def _init_driver(self):
        try:
            options = uc.ChromeOptions()
            self.driver = uc.Chrome(
                options=options, version_main=self.cfg_loader.driver.version
            )
            self.logger.info(
                "[DriverEngine](_init_driver) Undetected Chrome Driver Initialized"
            )
        except Exception as driver_err:
            self.logger.error(
                "[DriverEngine](_init_driver) Error While Initializing Web Driver"
            )
            raise driver_err
