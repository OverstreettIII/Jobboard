import os
from dotenv import load_dotenv
load_dotenv()

def get_exchange_rate(from_currency, to_currency):
    import requests
    API_KEY = os.environ.get("EXCHANGE_RATE_API_KEY")  # Lấy từ .env
    url = f"https://v6.exchangerate-api.com/v6/{API_KEY}/pair/{from_currency}/{to_currency}"
    try:
        print(f"[DEBUG] Requesting exchange rate: {from_currency} -> {to_currency} | URL: {url}")
        res = requests.get(url, timeout=5)
        print(f"[DEBUG] Exchange rate API status: {res.status_code}")
        if res.status_code == 200:
            data = res.json()
            print(f"[DEBUG] Exchange rate API response: {data}")
            return data.get("conversion_rate", 1.0)
        else:
            print(f"[WARNING] Exchange rate API returned status {res.status_code}: {res.text}")
    except Exception as e:
        print(f"[ERROR] Lấy tỷ giá thất bại: {e}")
    return 1.0
import requests
from datetime import datetime, timedelta
from core.models import Item, PushLog

def convert_days_left_to_date(days_left_str):
    try:
        days = int(days_left_str.split()[0])
        today = datetime.now()
        target_date = today + timedelta(days=days)
        return target_date.strftime('%Y-%m-%d')
    except Exception:
        return None

def get_token():
    login_url = "https://jobboard.beess.store/api/login"
    login_payload = {"email": "bee.test123@gmail.com", "password": "google"}
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }
    res = requests.post(login_url, json=login_payload, headers=headers)
    if res.status_code != 200:
        print("Login failed! Status code:", res.status_code)
        print("Response text:", res.text)
        raise Exception("Login failed")
    try:
        return res.json()["data"]["token"]
    except Exception as e:
        print("Login response is not valid JSON:", res.text)
        raise e

def push_item(item, company_id):
        # Cho phép truyền token thủ công, nếu không sẽ tự login
        if company_id and isinstance(company_id, str):
            token = company_id
        else:
            try:
                token = get_token()
            except Exception as e:
                PushLog.objects.create(item=item, success=False, http_status=0, response=str(e))
                print(f"[ERROR] Không lấy được token: {e}")
                return

        api_url = "https://jobboard.beess.store/api/problems"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        import re
        deadline = convert_days_left_to_date(item.day_left)
        industry = item.skills.split(',')[0].strip() if item.skills else ""
        # Ngân sách: lấy đơn vị tiền, số lớn nhất, chuyển sang VND
        budget_str = str(item.budget) if item.budget else ""
        currency = "VND"
        budget_lower = budget_str.lower()
        if "usd" in budget_lower:
            currency = "USD"
        elif "eur" in budget_lower:
            currency = "EUR"
        elif "aud" in budget_lower:
            currency = "AUD"
        elif "jpy" in budget_lower:
            currency = "JPY"
        elif "krw" in budget_lower:
            currency = "KRW"
        elif "rub" in budget_lower:
            currency = "RUB"
        elif "inr" in budget_lower:
            currency = "INR"
        elif "gbp" in budget_lower:
            currency = "GBP"
        elif "sgd" in budget_lower:
            currency = "SGD"
        elif "cad" in budget_lower:
            currency = "CAD"
        print(f"[DEBUG] Budget string: {budget_str}, detected currency: {currency}")
        num_match = re.findall(r"[\d.]+", budget_str)
        print(f"[DEBUG] Extracted numbers from budget: {num_match}")
        budget_num = max([float(n.replace(",", "")) for n in num_match]) if num_match else 0
        print(f"[DEBUG] Max budget number: {budget_num}")
        rate = 1.0
        fallback_rates = {
            "USD": 24000,
            "EUR": 26000,
            "INR": 320,
            "GBP": 30500,
            "JPY": 160,
            "KRW": 18,
            "RUB": 270,
            "SGD": 18000,
            "CAD": 17500,
        }
        fallback_rate = fallback_rates.get(currency, 1.0)
        if currency != "VND":
            rate_api = get_exchange_rate(currency, "VND")
            print(f"[DEBUG] API rate for {currency}->VND: {rate_api}, fallback: {fallback_rate}")
            # Luôn dùng API, chỉ fallback nếu API lỗi hoặc trả về < 1
            if not rate_api or rate_api < 1:
                print(f"[WARNING] Using fallback rate for {currency}: {fallback_rate}")
                rate = fallback_rate
            else:
                rate = rate_api
        budget_vnd = int(budget_num * rate)
        print(f"[DEBUG] Final budget in VND: {budget_vnd}")
        if currency != "VND" and budget_vnd < budget_num:
            print(f"[WARNING] Budget VND < budget_num, using fallback rate again")
            budget_vnd = int(budget_num * fallback_rate)
        #
        expertise = (item.skills or "")[:1000]
        # Chuẩn hóa description: giữ xuống dòng, loại bỏ khoảng trắng dư
        import re
        description = item.description or ""
        # Thay nhiều dấu xuống dòng liên tiếp bằng 1 xuống dòng
        description = re.sub(r"[\r\n]+", "\n", description)
        # Loại bỏ khoảng trắng dư đầu/cuối mỗi dòng
        description = "\n".join([line.strip() for line in description.splitlines()])
        # Loại bỏ nhiều dòng trống liên tiếp
        description = re.sub(r"(\n\s*){2,}", "\n", description)
        payload = {
            "title": item.title or "",
            "description": description,
            "industry": industry,
            "expertise_required": expertise,
            "budget": str(round(budget_vnd, 0)),
            "deadline": deadline or "",
            "status": "open"
        }
        try:
            res = requests.post(api_url, json=payload, headers=headers)
            success = res.status_code == 200
            try:
                response_json = res.json()
            except Exception:
                response_json = res.text
            PushLog.objects.create(item=item, success=success, http_status=res.status_code, response=str(response_json))
            if success:
                item.pushed = True
                item.save()
            print(f"Pushed item {item.id}: {res.status_code} - {response_json}")
        except Exception as e:
            PushLog.objects.create(item=item, success=False, http_status=0, response=str(e))
            print(f"[ERROR] Push thất bại: {e}")

def push_all_items():
    # Chỉ push những job có score > 7 điểm
    items = Item.objects.filter(pushed=False, score__gt=7)
    for item in items:
        push_item(item, None)

# Sử dụng:
# from core.push_api import push_all_items
# push_all_items(company_id=123)
