import csv
import logging
from pymongo import MongoClient
import hashlib
import random
import time
import bs4
import csv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium_stealth import stealth
import os
from twocaptcha import TwoCaptcha
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from dotenv import load_dotenv 

load_dotenv()

NO_THREADS = 8
RETRY_LIMIT = 3
TIMEOUT = 60 

load_dotenv()
api_key = os.getenv('API_KEY')

CACHE_DIR = 'cache'
os.makedirs(CACHE_DIR, exist_ok=True)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
]

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_random_user_agent():
    return random.choice(USER_AGENTS)

def setup_driver():
    options = Options()
    options.headless = True

    # options.add_argument("--headless")  
    # options.add_argument("--disable-gpu")
    # options.add_argument("--no-sandbox")  
    # options.add_argument("--disable-dev-shm-usage") 
    options.add_argument(f"user-agent={get_random_user_agent()}")
   
    service = Service(executable_path=ChromeDriverManager().install(), log_path='chromedriver.log')
    driver = webdriver.Chrome(service=service, options=options)
    stealth(driver,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
    )
    return driver

solver = TwoCaptcha(api_key)

def solve_captcha(driver, site_key, url):
    try:
        result = solver.recaptcha(sitekey=site_key, url=url)
        driver.execute_script(f'document.getElementById("g-recaptcha-response").innerHTML="{result["code"]}";')
        driver.find_element(By.CSS_SELECTOR, "#captcha__frame").submit()
        WebDriverWait(driver, TIMEOUT).until(EC.url_changes(url))
    except Exception as e:
        logging.error(f"Error solving CAPTCHA: {e}")

def random_delay():
    time.sleep(random.uniform(1, 3)) 

def get_cache_filename(url):
    url_hash = hashlib.md5(url.encode()).hexdigest()
    return os.path.join(CACHE_DIR, f"{url_hash}.html")

def get_page_html(url, retries=0):
    cache_filename = get_cache_filename(url)
    if os.path.exists(cache_filename):
        logging.info(f"Loading from cache: {url}")
        with open(cache_filename, 'r', encoding='utf-8') as file:
            return file.read()
    
    driver = setup_driver()
    try:
        random_delay()
        driver.get(url)
        if "captcha-delivery.com" in driver.page_source:
            logging.info("CAPTCHA detected, solving...")
            page_source = driver.page_source
            logging.debug(page_source)
            driver.save_screenshot('captcha_page.png')
            iframe = driver.find_element(By.TAG_NAME, 'iframe')
            driver.switch_to.frame(iframe)
            WebDriverWait(driver, TIMEOUT).until(EC.presence_of_element_located((By.CSS_SELECTOR, '#captcha__frame')))
            site_key = driver.find_element(By.CSS_SELECTOR, '#captcha__frame').get_attribute('data-sitekey')
            solve_captcha(driver, site_key, url)
            driver.switch_to.default_content()
        
        WebDriverWait(driver, TIMEOUT).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        html = driver.page_source
        with open(cache_filename, 'w', encoding='utf-8') as file:
            file.write(html)
        return html
    except Exception as e:
        logging.error(f"Error getting page HTML: {e}")
        if retries < RETRY_LIMIT:
            logging.info(f"Retrying... ({retries + 1}/{RETRY_LIMIT})")
            return get_page_html(url, retries + 1)
        return None
    finally:
        driver.quit()

def extract_companies_info(url):
    html = get_page_html(url)
    if not html:
        return None

    soup = bs4.BeautifulSoup(html, 'html.parser')
    
    phone = soup.find('p', class_='label-tel')
    phone = phone.get_text(strip=True) if phone else 'N/A'

    fax_button = soup.find('button', class_='faxCli')
    fax_section = fax_button.find_next('div', class_='collapse') if fax_button else None
    fax_tag = fax_section.find('p', class_='label-tel') if fax_section else None
    fax = fax_tag.get_text(strip=True) if fax_tag else 'N/A'

    website = soup.find('a', class_='btn btn-down website')
    website = website.get('href') if website else 'N/A'
    
    address = soup.find('p', class_='card-text')
    address = address.get_text(strip=True) if address else 'N/A'
    
    title = soup.find('h1', class_='card-title card-title-md mt-2')
    title = title.get_text(strip=True) if title else None
    
    activity_block = soup.find('div', class_='card-body pb-0')
    activity_section = activity_block.find_next('h5', style="font-family:'Lato', sans-serif;font-weight: bold;color:#000000;font-size:15px") if activity_block else None
    activity = activity_section.find_next('p').get_text(strip=True) if activity_section else 'N/A'
    
    manager = soup.find('p', class_='par-list')
    manager = manager.get_text(strip=True) if manager else 'N/A'
    
    if not title:
        return None

    return [title, phone, fax, website, address, activity, manager]

def extract_links_and_info(url, output_csv):
    page_number = 1
    links = set()
    base_url = 'https://www.kerix.net'
    while True:
        paginated_url = url if page_number == 1 else f"{url}?page={page_number}"
        html = get_page_html(paginated_url)
        if not html:
            break
        
        soup = bs4.BeautifulSoup(html, 'html.parser')
        card_bodies = soup.find_all('div', class_='card-body')
        if not card_bodies:
            break
        for card in card_bodies:
            anchors = card.find_all('a', class_='btn-success btn btn-sm bg-green-light pull-right animate__animated animate__pulse mt-2')
            for a in anchors:
                href = a.get('href')
                if href:
                    full_link = base_url + href
                    links.add(full_link)
            
        next_button = soup.find('a', class_='page-link', rel="next")
        if not next_button:
            break
        page_number += 1
    
    with ThreadPoolExecutor(max_workers=NO_THREADS) as executor: 
        futures = [executor.submit(extract_companies_info, link) for link in links]
        with open(output_csv, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            for future in as_completed(futures):
                try:
                    company_info = future.result()
                    if company_info:
                        writer.writerow(company_info)
                except Exception as e:
                    logging.error(f"Error processing company info: {e}")

def send_csv_to_mongodb(csv_file, mongo_uri, db_name, collection_name):
    client = MongoClient(mongo_uri)
    db = client[db_name]
    collection = db[collection_name]
    
    # Create a unique index on the Title field
    collection.create_index('Title', unique=True)
    
    unique_titles = set()
    unique_data = []

    with open(csv_file, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            title = row.get('Title')
            if title and title not in unique_titles:
                unique_titles.add(title)
                unique_data.append(row)
    
    if unique_data:
        try:
            collection.insert_many(unique_data, ordered=False)
            print(f"Inserted {len(unique_data)} unique records into MongoDB collection '{collection_name}'")
        except errors.BulkWriteError as e:
            # Handle duplicate key errors
            write_errors = e.details['writeErrors']
            print(f"Bulk write error: {len(write_errors)} duplicates found.")
            for error in write_errors:
                print(f"Duplicate entry found for Title: {error['op']['Title']}")
    else:
        print("No unique data found in CSV file")
            
    client.close()

def process_and_upload(urls, output_csv, mongo_uri, db_name, collection_name):
    unique_titles = set()
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = [executor.submit(extract_companies_info, link) for link in urls]
        with open(output_csv, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            for future in as_completed(futures):
                try:
                    company_info = future.result()
                    if company_info and company_info[0] not in unique_titles:
                        writer.writerow(company_info)
                        unique_titles.add(company_info[0])
                except Exception as e:
                    logging.error(f"Error processing company info: {e}")

    
    send_csv_to_mongodb(output_csv, mongo_uri, db_name, collection_name)