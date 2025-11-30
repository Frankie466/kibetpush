from datetime import datetime
import requests
import base64
import re
import json
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .forms import PaymentForm



def home(request):
    return render(request, 'mpesa_express/index.html')

# M-Pesa API Credentials
MPESA_SHORTCODE = "5515540"
MPESA_PASSKEY = "9d1c2d098353f5790d13f2faca56ebc8ff4c98e5970f307908e19f04e38ce54c"
CONSUMER_KEY = "0VxpuiMStrKodudK2das68bxDGW7GduDHaAuLYJarUn0VJ8d"
CONSUMER_SECRET = "ji9gGA0u4aGH66wsqJaBEJ2rVn8wWNNfcUVthP65frDwMSkKSjIvhvAcdx0wU3p6"
MPESA_BASE_URL = "https://api.safaricom.co.ke"  # Live URL
CALLBACK_URL = "https://starrlnk.shop"

# Generate M-Pesa Access Token
def generate_access_token():
    try:
        credentials = f"{CONSUMER_KEY}:{CONSUMER_SECRET}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()

        headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/json",
        }
        response = requests.get(
            f"{MPESA_BASE_URL}/oauth/v1/generate?grant_type=client_credentials",
            headers=headers,
        ).json()

        if "access_token" in response:
            return response["access_token"]
        else:
            raise Exception("Access token missing in response.")

    except requests.RequestException as e:
        raise Exception(f"Failed to connect to M-Pesa: {str(e)}")

# Initiate STK Push
def initiate_push(phone, amount):
    try:
        token = generate_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        stk_password = base64.b64encode(
            (MPESA_SHORTCODE + MPESA_PASSKEY + timestamp).encode()
        ).decode()

        request_body = {
            "BusinessShortCode": MPESA_SHORTCODE,
            "Password": stk_password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerBuyGoodsOnline",
            "Amount": amount,
            "PartyA": phone,
            "PartyB": 4160709,
            "PhoneNumber": phone,
            "CallBackURL": CALLBACK_URL,
            "AccountReference": "account",
            "TransactionDesc": "payment for pundles",
        }

        response = requests.post(
            f"{MPESA_BASE_URL}/mpesa/stkpush/v1/processrequest",
            json=request_body,
            headers=headers,
        )

        response_data = response.json()

        return response_data

    except requests.exceptions.RequestException as e:
        return {"errorMessage": str(e)}
    except Exception as e:
        return {"errorMessage": "Unexpected error occurred."}

# Format Phone Number
def format_phone_number(phone):
    phone = phone.replace("+", "")
    if re.match(r"^254\d{9}$", phone):
        return phone
    elif phone.startswith("0") and len(phone) == 10:
        return "254" + phone[1:]
    else:
        raise ValueError("Invalid phone number format")

# Django View for AJAX STK Push Requests
@csrf_exempt
def mpesa_stk_push(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            phone = format_phone_number(data["phone_number"])
            amount = int(data["amount"])

            response = initiate_push(phone, amount)

            if response.get("ResponseCode") == "0":
                request.session["phone_number"] = phone  # Store phone in session
                return JsonResponse({"status": "success", "redirect_url": "/payment/pending/"})
            else:
                return JsonResponse({"status": "error", "message": response.get("errorMessage", "Failed to initiate payment.")})

        except ValueError as e:
            return JsonResponse({"status": "error", "message": str(e)})
        except Exception as e:
            return JsonResponse({"status": "error", "message": "An error occurred."})
    return JsonResponse({"status": "error", "message": "Invalid request method."})

def pending_payment(request):
    phone_number = request.session.get("phone_number", "")
    return render(request, "pending.html", {"phone_number": phone_number})
# M-Pesa Callback Handler
@csrf_exempt
def mpesa_callback(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
            print("M-Pesa Callback Data:", data)

            result_code = data['Body']['stkCallback']['ResultCode']
            if result_code == 0:
                print("Payment was successful.")
            else:
                print(f"Payment failed with error code: {result_code}")

            return JsonResponse({"status": "success"})
        except Exception as e:
            print("Error processing callback:", e)
            return JsonResponse({"status": "error"})
