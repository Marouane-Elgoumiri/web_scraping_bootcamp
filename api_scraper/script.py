import requests
import xlwt
from xlwt import Workbook
import smtplib
from os.path import basename
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
from email.utils import COMMASPACE, formatdate

BASE_URL = "https://remoteok.com/api"
USER_AGENTS = "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:129.0) Gecko/20100101 Firefox/129.0"
REQUEST_HEADER = {
    'User-Agent': USER_AGENTS,
    'Accept-Language':'en-US, en;q=0.5',
}
def get_job_postings():
    response = requests.get(url=BASE_URL, headers=REQUEST_HEADER)
    return response.json()

if __name__ == "__main__":
    json = get_job_postings()[1]
    print(json)