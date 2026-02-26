from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from src.utils.adapters.driver import DriverEngine
from src.utils.config_manager import ConfigManager
from src.utils.logger import AppLogger
from tqdm import tqdm

import time, requests, re


class FormCrawler:

    def __init__(self):
        self.cfg_loader = ConfigManager().cfg
        self.driver = DriverEngine().driver
        self.logger = AppLogger()



    
