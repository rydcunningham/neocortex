from abc import ABC, abstractmethod
from typing import List, Tuple
import os
import json
import logging
from time import sleep
import random
import requests
from bs4 import BeautifulSoup
import html2text
import markdown
from tqdm import tqdm
from xml.etree import ElementTree as ET
import random

from .config import ESSAYS_METADATA_FILE
from .utils import extract_main_part

class BaseSubstackScraper(ABC):
    def __init__(
            self, 
            base_substack_url: str, 
            md_save_dir: str, 
            html_save_dir: str,
            **kwargs
    ):
        # Set retry and batch processing parameters first
        self.max_retries = 3
        self.retry_delay = 60  # seconds
        self.request_delay = 2  # seconds between requests
        self.batch_size = 25
        self.min_batch_delay = 7
        self.max_batch_delay = 10

        # Ensure consistent URL format
        if not base_substack_url.endswith("/"):
            base_substack_url += "/"
            
        # Set the base URL first since other methods depend on it
        self.base_substack_url = base_substack_url
        
        # Get writer name from URL
        self.writer_name = extract_main_part(base_substack_url)
        
        # Set up directories
        self.md_save_dir = f"{md_save_dir}/{self.writer_name}"
        self.html_save_dir = f"{html_save_dir}/{self.writer_name}"

        if not os.path.exists(self.md_save_dir):
            os.makedirs(self.md_save_dir)
            print(f"Created md directory {self.md_save_dir}")
        if not os.path.exists(self.html_save_dir):
            os.makedirs(self.html_save_dir)
            print(f"Created html directory {self.html_save_dir}")
        
        # Set other instance variables
        self.keywords = ["about", "archive", "podcast"]
        
        # Load existing metadata
        self.existing_urls = self.get_existing_urls()
        
        # Get all post URLs
        self.post_urls = self.get_all_post_urls()

    def get_existing_urls(self) -> set:
        """Get set of URLs that have already been scraped"""
        try:
            with open(ESSAYS_METADATA_FILE, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                # Get URLs for this Substack
                substack_data = metadata.get(self.base_substack_url.rstrip('/'), [])
                return {essay['url'] for essay in substack_data}
        except (FileNotFoundError, json.JSONDecodeError):
            return set()

    def analyze_scraping_task(self) -> tuple:
        """
        Analyze what needs to be scraped
        Returns (total_posts, already_scraped, to_scrape)
        """
        all_urls = set(self.get_all_post_urls())
        already_scraped = all_urls.intersection(self.existing_urls)
        to_scrape = all_urls - already_scraped
        
        return len(all_urls), len(already_scraped), len(to_scrape)

    def get_all_post_urls(self) -> List[str]:
        """
        Attempts to fetch URLs from sitemap.xml, falling back to feed.xml if necessary.
        """
        urls = self.fetch_urls_from_sitemap()
        if not urls:
            urls = self.fetch_urls_from_feed()
        return self.filter_urls(urls, self.keywords)

    def fetch_urls_from_sitemap(self) -> List[str]:
        """
        Fetches URLs from sitemap.xml with retry logic
        """
        sitemap_url = f"{self.base_substack_url}sitemap.xml"
        
        for attempt in range(self.max_retries):
            try:
                response = requests.get(sitemap_url)
                if response.ok:
                    root = ET.fromstring(response.content)
                    urls = [element.text for element in root.iter('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]
                    return urls
                
            except Exception as e:
                if attempt == self.max_retries - 1:
                    logging.error(f'Error fetching sitemap at {sitemap_url}: {e}')
                    return []
                    
                logging.warning(f'Attempt {attempt + 1} failed, retrying in {self.retry_delay} seconds...')
                sleep(self.retry_delay)
        
        return []

    def fetch_urls_from_feed(self) -> List[str]:
        """
        Fetches URLs from feed.xml with retry logic
        """
        print('Falling back to feed.xml. This will only contain up to the 22 most recent posts.')
        feed_url = f"{self.base_substack_url}feed.xml"
        
        for attempt in range(self.max_retries):
            try:
                response = requests.get(feed_url)
                if response.ok:
                    root = ET.fromstring(response.content)
                    urls = []
                    for item in root.findall('.//item'):
                        link = item.find('link')
                        if link is not None and link.text:
                            urls.append(link.text)
                    return urls
                    
            except Exception as e:
                if attempt == self.max_retries - 1:
                    print(f'Error fetching feed at {feed_url}: {e}')
                    return []
                    
                print(f'Attempt {attempt + 1} failed, retrying in {self.retry_delay} seconds...')
                sleep(self.retry_delay)
        
        return []

    @staticmethod
    def filter_urls(urls: List[str], keywords: List[str]) -> List[str]:
        """
        This method filters out URLs that contain certain keywords
        """
        return [url for url in urls if all(keyword not in url for keyword in keywords)]

    @staticmethod
    def html_to_md(html_content: str) -> str:
        """
        This method converts HTML to Markdown
        """
        if not isinstance(html_content, str):
            raise ValueError("html_content must be a string")
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.body_width = 0
        return h.handle(html_content)

    @staticmethod
    def save_to_file(filepath: str, content: str) -> None:
        """
        This method saves content to a file. Can be used to save HTML or Markdown
        """
        if not isinstance(filepath, str):
            raise ValueError("filepath must be a string")

        if not isinstance(content, str):
            raise ValueError("content must be a string")

        if os.path.exists(filepath):
            print(f"File already exists: {filepath}")
            return

        with open(filepath, 'w', encoding='utf-8') as file:
            file.write(content)

    @staticmethod
    def md_to_html(md_content: str) -> str:
        """
        This method converts Markdown to HTML
        """
        return markdown.markdown(md_content, extensions=['extra'])


    def save_to_html_file(self, filepath: str, content: str) -> None:
        """
        This method saves HTML content to a file with a link to an external CSS file.
        """
        if not isinstance(filepath, str):
            raise ValueError("filepath must be a string")

        if not isinstance(content, str):
            raise ValueError("content must be a string")

        # Calculate the relative path from the HTML file to the CSS file
        html_dir = os.path.dirname(filepath)
        css_path = os.path.relpath("./assets/css/essay-styles.css", html_dir)
        css_path = css_path.replace("\\", "/")  # Ensure forward slashes for web paths

        html_content = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Markdown Content</title>
                <link rel="stylesheet" href="{css_path}">
            </head>
            <body>
                <main class="markdown-content">
                {content}
                </main>
            </body>
            </html>
        """

        with open(filepath, 'w', encoding='utf-8') as file:
            file.write(html_content)

    @staticmethod
    def get_filename_from_url(url: str, filetype: str = ".md") -> str:
        """
        Gets the filename from the URL (the ending)
        """
        if not isinstance(url, str):
            raise ValueError("url must be a string")

        if not isinstance(filetype, str):
            raise ValueError("filetype must be a string")

        if not filetype.startswith("."):
            filetype = f".{filetype}"

        return url.split("/")[-1] + filetype

    @staticmethod
    def combine_metadata_and_content(title: str, subtitle: str, date: str, like_count: str, content) -> str:
        """
        Combines the title, subtitle, and content into a single string with Markdown format
        """
        if not isinstance(title, str):
            raise ValueError("title must be a string")

        if not isinstance(content, str):
            raise ValueError("content must be a string")

        metadata = f"# {title}\n\n"
        if subtitle:
            metadata += f"## {subtitle}\n\n"
        metadata += f"**{date}**\n\n"
        metadata += f"**Likes:** {like_count}\n\n"

        return metadata + content

    def extract_post_data(self, soup: BeautifulSoup) -> Tuple[str, str, str, str, str]:
        """
        Converts substack post soup to markdown, returns metadata and content
        """
        title = soup.select_one("h1.post-title, h2").text.strip()  # When a video is present, the title is demoted to h2

        subtitle_element = soup.select_one("h3.subtitle")
        subtitle = subtitle_element.text.strip() if subtitle_element else ""

        
        date_element = soup.find(
            "div",
            class_="pencraft pc-reset color-pub-secondary-text-hGQ02T line-height-20-t4M0El font-meta-MWBumP size-11-NuY2Zx weight-medium-fw81nC transform-uppercase-yKDgcq reset-IxiVJZ meta-EgzBVA"
        )
        date = date_element.text.strip() if date_element else "Date not found"

        like_count_element = soup.select_one("a.post-ufi-button .label")
        like_count = (
            like_count_element.text.strip()
            if like_count_element and like_count_element.text.strip().isdigit()
            else "0"
        )

        content = str(soup.select_one("div.available-content"))
        md = self.html_to_md(content)
        md_content = self.combine_metadata_and_content(title, subtitle, date, like_count, md)
        return title, subtitle, like_count, date, md_content

    @abstractmethod
    def get_url_soup(self, url: str) -> str:
        raise NotImplementedError

    def save_essays_data_to_json(self, essays_data: list) -> None:
        """
        Saves essays data to a consolidated JSON file
        """
        if not os.path.exists(os.path.dirname(ESSAYS_METADATA_FILE)):
            os.makedirs(os.path.dirname(ESSAYS_METADATA_FILE))

        # Load existing metadata
        all_metadata = {}
        if os.path.exists(ESSAYS_METADATA_FILE):
            with open(ESSAYS_METADATA_FILE, 'r', encoding='utf-8') as f:
                all_metadata = json.load(f)
        
        # Update metadata for this Substack
        substack_key = self.base_substack_url.rstrip('/')
        existing_essays = all_metadata.get(substack_key, [])
        
        # Add new essays, avoiding duplicates
        updated_essays = existing_essays + [
            essay for essay in essays_data 
            if essay not in existing_essays
        ]
        
        # Update the metadata
        all_metadata[substack_key] = updated_essays
        
        # Save updated metadata
        with open(ESSAYS_METADATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(all_metadata, f, ensure_ascii=False, indent=4)

    def scrape_posts(self, num_posts_to_scrape: int = 0) -> None:
        """
        Scrape posts with initial analysis and batch processing.
        Only count successfully processed posts towards batch size.
        """
        # Get all URLs first
        all_urls = self.get_all_post_urls()
        total_posts, already_scraped, to_scrape = self.analyze_scraping_task()
        
        logging.info(f"\nScraping analysis for {self.base_substack_url}:")
        logging.info(f"Total posts available: {total_posts}")
        logging.info(f"Already scraped: {already_scraped}")
        logging.info(f"To be scraped: {to_scrape}")
        
        if num_posts_to_scrape:
            to_scrape = min(to_scrape, num_posts_to_scrape)
            logging.info(f"Will scrape {to_scrape} posts (limited by user request)")
        
        if to_scrape == 0:
            logging.info("No new posts to scrape!")
            return

        # Filter out already scraped URLs
        urls_to_process = [url for url in all_urls if url not in self.existing_urls]
        if num_posts_to_scrape:
            urls_to_process = urls_to_process[:num_posts_to_scrape]

        essays_data = []
        processed = 0
        url_index = 0
        
        while url_index < len(urls_to_process):
            batch_processed = 0
            batch_urls = []
            
            # Process until we get batch_size successful posts or run out of URLs
            while batch_processed < self.batch_size and url_index < len(urls_to_process):
                url = urls_to_process[url_index]
                batch_urls.append(url)
                url_index += 1
                
            batch_num = (processed // self.batch_size) + 1
            total_batches = (to_scrape + self.batch_size - 1) // self.batch_size
            
            logging.info(f"\nProcessing batch {batch_num}/{total_batches}")
            
            for url in tqdm(batch_urls, desc=f"Batch {batch_num}/{total_batches}"):
                try:
                    md_filename = self.get_filename_from_url(url, filetype=".md")
                    html_filename = self.get_filename_from_url(url, filetype=".html")
                    md_filepath = os.path.join(self.md_save_dir, md_filename)
                    html_filepath = os.path.join(self.html_save_dir, html_filename)

                    if not os.path.exists(md_filepath):
                        soup = self.get_url_soup(url)
                        if soup is None:
                            logging.warning(f"Skipping {url} - could not get content")
                            sleep(1)  # Brief pause after failed attempt
                            continue
                        
                        try:
                            title, subtitle, like_count, date, md = self.extract_post_data(soup)
                        except Exception as e:
                            logging.error(f"Failed to extract data from {url}: {e}")
                            sleep(1)
                            continue
                            
                        try:
                            self.save_to_file(md_filepath, md)
                            html_content = self.md_to_html(md)
                            self.save_to_html_file(html_filepath, html_content)
                        except Exception as e:
                            logging.error(f"Failed to save files for {url}: {e}")
                            # Clean up any partially written files
                            for f in [md_filepath, html_filepath]:
                                if os.path.exists(f):
                                    os.remove(f)
                            continue
                        
                        essays_data.append({
                            "title": title,
                            "subtitle": subtitle,
                            "like_count": like_count,
                            "date": date,
                            "url": url,
                            "md_file": md_filepath,
                            "html_file": html_filepath
                        })
                        
                        logging.info(f"Saved: {title} ({date})")
                        processed += 1
                        batch_processed += 1
                        
                        # Small delay between successful posts
                        sleep(0.5)
                        
                    else:
                        logging.debug(f"File already exists: {md_filepath}")
                    
                except Exception as e:
                    logging.error(f"Error scraping {url}: {e}")
                    sleep(1)  # Brief pause after any error
            
            # Save progress and delay after each batch
            if essays_data:
                self.save_essays_data_to_json(essays_data)
            
            if url_index < len(urls_to_process):
                delay = random.uniform(self.min_batch_delay, self.max_batch_delay)
                remaining = len(urls_to_process) - url_index
                logging.info(f"Batch complete. {remaining} posts remaining. Sleeping for {delay:.1f} seconds...")
                sleep(delay)

        logging.info(f"\nCompleted scraping for {self.base_substack_url}")
        logging.info(f"Successfully processed {processed} posts")

