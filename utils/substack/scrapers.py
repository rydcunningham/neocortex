from typing import Optional
import logging
from time import sleep
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options as ChromiumOptions
from webdriver_manager.chrome import ChromeDriverManager

from .base_scraper import BaseSubstackScraper
from .config import EMAIL, PASSWORD

class SubstackScraper(BaseSubstackScraper):
    def __init__(self, base_substack_url: str, md_save_dir: str, html_save_dir: str):
        super().__init__(base_substack_url, md_save_dir, html_save_dir)

    def get_url_soup(self, url: str) -> Optional[BeautifulSoup]:
        """
        Gets soup from URL using requests with retries and better error handling
        """
        try:
            # Add headers to look more like a browser
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Connection': 'keep-alive',
            }
            
            # Try up to 3 times with increasing delays
            for attempt in range(3):
                try:
                    response = requests.get(url, headers=headers, timeout=10)
                    response.raise_for_status()
                    
                    soup = BeautifulSoup(response.content, "html.parser")
                    
                    # Check for paywall
                    if soup.find("h2", class_="paywall-title"):
                        logging.info(f"Skipping premium article: {url}")
                        return None
                        
                    # Check if we got a valid article
                    content = soup.select_one("div.available-content")
                    if not content:
                        logging.warning(f"No content found for {url}")
                        return None
                        
                    return soup
                    
                except requests.RequestException as e:
                    if attempt == 2:  # Last attempt
                        logging.error(f"Failed to fetch {url} after 3 attempts: {e}")
                        return None
                    sleep_time = (attempt + 1) * 2
                    logging.warning(f"Attempt {attempt + 1} failed, retrying in {sleep_time}s...")
                    sleep(sleep_time)
                    
        except Exception as e:
            logging.error(f"Unexpected error fetching {url}: {e}")
            return None
    
    def extract_post_data(self, soup: BeautifulSoup) -> tuple[str, str, str, str, str]:
        """
        Converts substack post soup to markdown with better error handling
        """
        try:
            # Title might be in different places
            title_elem = soup.select_one("h1.post-title, h2.post-title, h1, h2")
            if not title_elem:
                raise ValueError("Could not find title")
            title = title_elem.text.strip()

            # Subtitle is optional
            subtitle_element = soup.select_one("h3.subtitle")
            subtitle = subtitle_element.text.strip() if subtitle_element else ""

            # Date might be in different places
            date_element = soup.find(
                "div",
                class_=lambda x: x and all(c in x for c in ["pencraft", "color-pub-secondary-text"])
            )
            date = date_element.text.strip() if date_element else "Date not found"

            # Likes are optional
            like_count_element = soup.select_one("a.post-ufi-button .label")
            like_count = (
                like_count_element.text.strip()
                if like_count_element and like_count_element.text.strip().isdigit()
                else "0"
            )

            # Content is required
            content_elem = soup.select_one("div.available-content")
            if not content_elem:
                raise ValueError("Could not find content")
            content = str(content_elem)
            
            md = self.html_to_md(content)
            md_content = self.combine_metadata_and_content(title, subtitle, date, like_count, md)
            return title, subtitle, like_count, date, md_content

        except Exception as e:
            logging.error(f"Error extracting post data: {e}")
            raise

class PremiumSubstackScraper(BaseSubstackScraper):
    def __init__(
            self,
            base_substack_url: str,
            md_save_dir: str,
            html_save_dir: str,
            headless: bool = False,
            chromium_binary: str = '/Applications/Chromium.app/Contents/MacOS/Chromium',
            chromium_driver_path: str = '',
            user_agent: str = ''
    ) -> None:
        # Call parent's init with all arguments
        super().__init__(
            base_substack_url=base_substack_url,
            md_save_dir=md_save_dir,
            html_save_dir=html_save_dir
        )

        options = ChromiumOptions()
        if headless:
            options.add_argument("--headless=new")
        
        # Set Chromium binary location
        options.binary_location = chromium_binary
        
        if user_agent:
            options.add_argument(f'user-agent={user_agent}')

        # Add anti-detection measures
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)

        if chromium_driver_path:
            service = Service(executable_path=chromium_driver_path)
        else:
            service = Service(ChromeDriverManager().install())

        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        self.login()

    def login(self) -> None:
        """
        Login method using XPath selectors. May require manual CAPTCHA completion.
        """
        try:
            self.driver.get("https://substack.com/sign-in")
            logging.info("Loaded sign-in page")
            sleep(3)

            signin_with_password = self.driver.find_element(
                By.XPATH, "//a[@class='login-option substack-login__login-option']"
            )
            signin_with_password.click()
            logging.info("Clicked 'Sign in with password'")
            sleep(3)

            email = self.driver.find_element(By.NAME, "email")
            password = self.driver.find_element(By.NAME, "password")
            
            email.send_keys(EMAIL)
            password.send_keys(PASSWORD)
            logging.info("Entered credentials")

            submit = self.driver.find_element(
                By.XPATH, "//*[@id=\"substack-login\"]/div[2]/div[2]/form/button"
            )
            submit.click()
            logging.info("Clicked submit")
            
            logging.warning("If a CAPTCHA appears, please complete it manually within the next 30 seconds...")
            sleep(30)  # Wait for potential manual CAPTCHA completion

            if self.is_login_failed():
                raise Exception("Login failed - please check if CAPTCHA needs completing")
            
            logging.info("Successfully logged into Substack")
            
        except Exception as e:
            logging.error(f"Login failed: {e}")
            raise

    def is_login_failed(self) -> bool:
        error_container = self.driver.find_elements(By.ID, 'error-container')
        return len(error_container) > 0 and error_container[0].is_displayed()

    def get_url_soup(self, url: str) -> BeautifulSoup:
        try:
            self.driver.get(url)
            return BeautifulSoup(self.driver.page_source, "html.parser")
        except Exception as e:
            raise ValueError(f"Error fetching page: {e}") from e