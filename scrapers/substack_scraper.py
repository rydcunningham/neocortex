# scrapers/substack_scraper.py
import os
import sys
import logging
import argparse
from dotenv import load_dotenv

# Get absolute path to project root (parent of scrapers directory)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(PROJECT_ROOT)

from utils.substack.config import *
from utils.substack.scrapers import SubstackScraper, PremiumSubstackScraper
from utils.substack.metadata import get_tracked_substacks

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape a Substack site.")
    parser.add_argument(
        "-u", "--url", type=str, help="The base URL of the Substack site to scrape."
    )
    parser.add_argument(
        "-d", "--directory", type=str, help="The directory to save scraped posts."
    )
    parser.add_argument(
        "-n", "--number", type=int, default=0,
        help="The number of posts to scrape. If 0 or not provided, all posts will be scraped.",
    )
    parser.add_argument(
        "-p", "--premium", action="store_true",
        help="Include -p to use the Premium Substack Scraper with selenium.",
    )
    parser.add_argument(
        "--headless", action="store_true",
        help="Run browser in headless mode for Premium Substack Scraper.",
    )
    parser.add_argument(
        "--chromium-binary",
        type=str,
        default="/Applications/Chromium.app/Contents/MacOS/Chromium",
        help='Path to Chromium binary. Defaults to standard Mac installation path.',
    )
    parser.add_argument(
        "--chromium-driver-path",
        type=str,
        default="",
        help='Optional: The path to the Chromium WebDriver executable',
    )
    parser.add_argument(
        "--user-agent",
        type=str,
        default="",
        help="Optional: Specify a custom user agent. Useful for passing captcha in headless mode",
    )
    parser.add_argument(
        "--html-directory",
        type=str,
        help="The directory to save scraped posts as HTML files.",
    )

    return parser.parse_args()

def main():
    args = parse_args()
    
    if args.directory is None:
        args.directory = BASE_MD_DIR

    if args.html_directory is None:
        args.html_directory = BASE_HTML_DIR

    if args.url:
        # Single Substack processing...
        pass
    else:
        substacks = get_tracked_substacks()
        if not substacks:
            logging.error("No Substacks found to process")
            return

        for i, substack in enumerate(substacks):
            url = substack['url']
            is_premium = substack.get('premium', False)
            
            logging.info(f"Processing {url} ({i+1}/{len(substacks)}) - Premium: {is_premium}")
            
            try:
                if is_premium:
                    scraper = PremiumSubstackScraper(
                        base_substack_url=url,
                        md_save_dir=args.directory,
                        html_save_dir=args.html_directory,
                        chromium_binary=args.chromium_binary,
                        chromium_driver_path=args.chromium_driver_path
                    )
                else:
                    scraper = SubstackScraper(
                        base_substack_url=url,
                        md_save_dir=args.directory,
                        html_save_dir=args.html_directory
                    )
                scraper.scrape_posts(num_posts_to_scrape=args.number)
                
                # Add delay between different Substacks
                if i < len(substacks) - 1:  # If not the last Substack
                    delay = random.uniform(10, 15)  # Longer delay between Substacks
                    logging.info(f"Completed {url}. Sleeping for {delay:.1f} seconds before next Substack...")
                    sleep(delay)
                
            except Exception as e:
                logging.error(f"Error processing {url}: {e}")
                continue

if __name__ == "__main__":
    load_dotenv()
    main()