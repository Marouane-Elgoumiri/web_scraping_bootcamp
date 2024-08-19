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

def output_job_to_xls(data):
    wb = Workbook()
    job_sheet = wb.add_sheet("Jobs")
    headers = list(data[0].keys())
    for i in range(0, len(headers)):
        job_sheet.write(0, i, headers[i])
    for i in range(0, len(data)):
        job = data[i]
        values = list(job.values())
        for x in range(0, len(values)):
            job_sheet.write(i+1, x, values[x])

    wb.save("Remote_jobs.xls")

if __name__ == "__main__":
    json = get_job_postings()[1:]
    output_job_to_xls(json)