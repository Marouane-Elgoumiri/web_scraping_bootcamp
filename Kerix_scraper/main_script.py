import time
import csv
import os
from dotenv import load_dotenv
import sys
from tqdm import tqdm
from process_upload import extract_links_and_info
from process_upload import process_and_upload
     
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
        urls = [row[0] for row in reader]
        
    for url in tqdm(urls, desc="Scraping URLs"):
        extract_links_and_info(url, output_csv)

    total_urls = len(urls)
    for i, url in enumerate(urls):
        extract_links_and_info(url, output_csv)
        progress = int((i + 1) / total_urls * 100)
        print(f"Progress: {progress}%", flush=True)
        sys.stdout.flush()     
        
    with open(output_csv, 'r', newline='') as csvfile:
        reader = csv.reader(csvfile)
        row_count = sum(1 for row in reader) - 1
    end_time = time.time()  
    duration = (end_time - start_time)/60  
    Accuracy = (row_count/506)*100 
    print(f"Scraped {row_count} companies in {duration:.2f} min")
    print(f"Accuracy of {Accuracy:.2f}%")

    mongo_uri = os.getenv("MONGO_URI")
    db_name = os.getenv("DB_NAME")
    collection_name = os.getenv("COLLECTION_NAME")

    process_and_upload(urls, output_csv, mongo_uri, db_name, collection_name)