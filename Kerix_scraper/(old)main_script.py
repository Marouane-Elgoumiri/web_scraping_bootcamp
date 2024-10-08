import random
import time
import bs4
from requests import Session
from twocaptcha import TwoCaptcha
from datetime import datetime
import csv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium_stealth import stealth
import os
from dotenv import load_dotenv
import time

load_dotenv()
api_key = os.getenv('API_KEY')


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
]

def get_random_user_agent():
    return random.choice(USER_AGENTS)

def setup_driver():
    options = Options()
    options.headless = True
    options.add_argument(f"user-agent={get_random_user_agent()}")
    service = Service(log_path='chromedriver.log')
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
        WebDriverWait(driver, 10).until(EC.url_changes(url))
    except Exception as e:
        print(f"Error solving CAPTCHA: {e}")

session = Session()
session.headers.update({"User-Agent": get_random_user_agent()})

def random_delay():
    time.sleep(random.uniform(1, 5))

def get_page_html(url):
    driver = setup_driver()
    try:
        random_delay()
        driver.get(url)
        if "captcha-delivery.com" in driver.page_source:
            print("CAPTCHA detected, solving...")
            # Print page source for debugging
            page_source = driver.page_source
            print(page_source)
            # Take a screenshot for debugging
            driver.save_screenshot('tg')
            # Switch to the iframe containing the CAPTCHA
            iframe = driver.find_element(By.TAG_NAME, 'iframe')
            driver.switch_to.frame(iframe)
            # Wait for the CAPTCHA element to be present
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, '#captcha__frame')))
            site_key = driver.find_element(By.CSS_SELECTOR, '#captcha__frame').get_attribute('data-sitekey')
            solve_captcha(driver, site_key, url)
            # Switch back to the main content
            driver.switch_to.default_content()
        
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        html = driver.page_source
        return html
    except Exception as e:
        print(f"Error getting page HTML: {e}")
        return None
    finally:
        driver.quit()

def extract_companies_info(url):
    html = get_page_html(url)
    if not html:
        return None

    soup = bs4.BeautifulSoup(html, 'html.parser')
    
    # Extracting the required information
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
    title = title.get_text(strip=True) if title else 'N/A'
    
    activity_block = soup.find('div', class_='card-body pb-0')
    activity_section = activity_block.find_next('h5', style="font-family:'Lato', sans-serif;font-weight: bold;color:#000000;font-size:15px") if activity_block else None
    activity = activity_section.find_next('p').get_text(strip=True) if activity_section else 'N/A'
    
    manager = soup.find('p', class_='par-list')
    manager = manager.get_text(strip=True) if manager else 'N/A'
    
    return [title, phone, fax, website, address, activity, manager]

def extract_links_and_info(url, output_csv):
    page_number = 1
    links = set()
    base_url = 'https://www.kerix.net'
    with open(output_csv, 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)
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
        
        for link in links:
            company_info = extract_companies_info(link)
            if company_info:
                writer.writerow(company_info)

if __name__ == "__main__":
    start_time = time.time()
    output_folder = 'results'
    os.makedirs(output_folder, exist_ok=True)
    output_csv = os.path.join(output_folder, 'companies_info.csv')
    with open(output_csv, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Title', 'Phone', 'Fax','Website','Address', 'Activity', 'Manager'])  

    urls_folder = './urls'
    urls_file = os.path.join(urls_folder, 'scraping_urls.csv')
    
    with open(urls_file, newline='') as csvfile:
        reader = csv.reader(csvfile, delimiter=',')
        for row in reader:
            url = row[0]
            extract_links_and_info(url, output_csv)
            
    with open(output_csv, 'r', newline='') as csvfile:
        reader = csv.reader(csvfile)
        row_count = sum(1 for row in reader) - 1
    end_time = time.time()  
    duration = end_time - start_time    
    Accuracy = (row_count/175)*100 
    print(f"Scraped {row_count} companies in {duration:.2f} seconds")
    print(f"Acccuracy of {Accuracy:.2f}%")
    