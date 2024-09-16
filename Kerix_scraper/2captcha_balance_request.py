import requests

API_KEY = '48d879d5ca11d1f5ff14070cb4308a64'

def check_balance(api_key):
    url = f"http://2captcha.com/res.php?key={api_key}&action=getbalance&json=1"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if 'status' in data and data['status'] == 1:
            return data['request']
        else:
            return f"Error: {data['request']}"
    else:
        return f"HTTP Error: {response.status_code}"

if __name__ == "__main__":
    balance = check_balance(API_KEY)
    print(f"2Captcha Balance: {balance}")