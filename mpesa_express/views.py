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
CALLBACK_URL = "https://starrlnk.shop/mpesa/callback/"

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
            timeout=30
        ).json()

        if "access_token" in response:
            return response["access_token"]
        else:
            print(f"❌ Access token missing: {response}")
            raise Exception("Access token missing in response.")

    except requests.RequestException as e:
        print(f"❌ Failed to get access token: {str(e)}")
        raise Exception(f"Failed to connect to M-Pesa: {str(e)}")

# Initiate STK Push
def initiate_push(phone, amount):
    try:
        print(f"🔑 Generating access token...")
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
            "AccountReference": "Starlink Payment",
            "TransactionDesc": "Starlink Internet Package",
        }

        print(f"📤 Sending STK push to {phone} for Ksh {amount}")
        print(f"📦 Request body: {json.dumps(request_body, indent=2)}")

        response = requests.post(
            f"{MPESA_BASE_URL}/mpesa/stkpush/v1/processrequest",
            json=request_body,
            headers=headers,
            timeout=30
        )

        print(f"📥 Response Status: {response.status_code}")
        print(f"📥 Response Text: {response.text}")

        if response.status_code != 200:
            print(f"❌ HTTP Error: {response.status_code}")
            return {
                "errorMessage": f"HTTP Error {response.status_code}",
                "ResponseCode": "1"
            }

        response_data = response.json()
        
        # Log full response
        print(f"📊 Full Response Data: {json.dumps(response_data, indent=2)}")
        
        # Check for specific error fields
        if "errorCode" in response_data or "errorMessage" in response_data:
            error_msg = response_data.get("errorMessage") or response_data.get("errorCode", "Unknown error")
            print(f"❌ M-Pesa API Error: {error_msg}")
            return {
                "errorMessage": error_msg,
                "ResponseCode": "1"
            }
        
        # Check if it's a successful STK push response
        if "ResponseCode" in response_data:
            return response_data
        else:
            # If no ResponseCode field, something went wrong
            print(f"❌ No ResponseCode in response")
            return {
                "errorMessage": "Invalid response from M-Pesa",
                "ResponseCode": "1",
                "raw_response": response_data
            }

    except requests.exceptions.Timeout:
        print("❌ Request timeout")
        return {"errorMessage": "Request timeout. Please try again.", "ResponseCode": "1"}
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        return {"errorMessage": f"Network error: {str(e)}", "ResponseCode": "1"}
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return {"errorMessage": "Unexpected error occurred.", "ResponseCode": "1"}

# Format Phone Number
def format_phone_number(phone):
    phone = phone.replace("+", "").replace(" ", "").replace("-", "")
    if re.match(r"^254\d{9}$", phone):
        return phone
    elif phone.startswith("0") and len(phone) == 10:
        return "254" + phone[1:]
    elif len(phone) == 9 and phone.startswith("7"):
        return "254" + phone
    else:
        raise ValueError(f"Invalid phone number format: {phone}. Use format: 0712345678 or 254712345678")

# Django View for AJAX STK Push Requests
@csrf_exempt
def mpesa_stk_push(request):
    if request.method == "POST":
        try:
            print(f"📨 Received STK push request")
            data = json.loads(request.body)
            print(f"📝 Request data: {data}")
            
            phone = format_phone_number(data["phone_number"])
            amount = int(data["amount"])
            package_name = data.get("package_name", "Unknown Package")

            print(f"📱 Processing STK push for phone: {phone}, amount: {amount}, package: {package_name}")

            response = initiate_push(phone, amount)
            
            print(f"📊 STK Push Response: {response}")

            # Check if ResponseCode exists and is "0"
            if "ResponseCode" in response and response.get("ResponseCode") == "0":
                # Success - STK push sent to customer
                print(f"✅ STK Push successful! CheckoutRequestID: {response.get('CheckoutRequestID')}")
                
                # Store in session
                request.session["phone_number"] = phone
                request.session["checkout_request_id"] = response.get("CheckoutRequestID", "")
                request.session["merchant_request_id"] = response.get("MerchantRequestID", "")
                request.session["amount"] = amount
                request.session["package_name"] = package_name
                
                # Save session immediately
                request.session.save()
                
                return JsonResponse({
                    "status": "success", 
                    "redirect_url": "/payment/pending/",
                    "message": "STK push sent to your phone. Please check and enter your PIN.",
                    "checkout_request_id": response.get("CheckoutRequestID", "")
                })
            else:
                # Failed to initiate STK push
                error_message = response.get("errorMessage") or \
                               response.get("CustomerMessage") or \
                               response.get("ResponseDescription") or \
                               "Failed to initiate payment. Please try again."
                
                print(f"❌ STK Push failed: {error_message}")
                return JsonResponse({
                    "status": "error", 
                    "message": error_message,
                    "debug": response  # Include debug info
                })

        except ValueError as e:
            print(f"❌ Value error: {e}")
            return JsonResponse({"status": "error", "message": str(e)})
        except KeyError as e:
            print(f"❌ Missing key: {e}")
            return JsonResponse({"status": "error", "message": f"Missing field: {e}"})
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return JsonResponse({"status": "error", "message": "An error occurred. Please try again."})
    
    print(f"❌ Invalid request method: {request.method}")
    return JsonResponse({"status": "error", "message": "Invalid request method."})

def pending_payment(request):
    phone_number = request.session.get("phone_number", "")
    amount = request.session.get("amount", 0)
    package_name = request.session.get("package_name", "")
    checkout_id = request.session.get("checkout_request_id", "")
    
    context = {
        "phone_number": phone_number,
        "amount": amount,
        "package_name": package_name,
        "checkout_id": checkout_id,
    }
    
    print(f"📄 Rendering pending page with context: {context}")
    return render(request, "mpesa_express/pending.html", context)

# M-Pesa Callback Handler
@csrf_exempt
def mpesa_callback(request):
    if request.method == "POST":
        try:
            # Log the incoming data for debugging
            raw_body = request.body.decode("utf-8")
            print(f"📞 Raw callback received: {raw_body}")
            
            data = json.loads(raw_body)
            print("📋 Parsed M-Pesa Callback Data:", json.dumps(data, indent=2))

            # Extract relevant information
            callback = data.get('Body', {}).get('stkCallback', {})
            result_code = callback.get('ResultCode', 1)  # Default to error if missing
            checkout_request_id = callback.get('CheckoutRequestID', '')
            merchant_request_id = callback.get('MerchantRequestID', '')
            
            if result_code == 0:
                # Successful payment
                metadata = callback.get('CallbackMetadata', {}).get('Item', [])
                
                print(f"✅ Payment Successful!")
                print(f"   CheckoutRequestID: {checkout_request_id}")
                print(f"   MerchantRequestID: {merchant_request_id}")
                
                # Extract transaction details
                transaction_details = {}
                for item in metadata:
                    name = item.get('Name', '')
                    value = item.get('Value', '')
                    transaction_details[name] = value
                    print(f"   {name}: {value}")
                
                # Here you should:
                # 1. Update your database
                # 2. Mark payment as complete
                # 3. Send confirmation email/SMS
                # 4. Trigger any post-payment actions
                
                print(f"💰 Transaction completed successfully!")
                
            else:
                # Failed payment
                result_desc = callback.get('ResultDesc', 'Unknown error')
                print(f"❌ Payment Failed!")
                print(f"   CheckoutRequestID: {checkout_request_id}")
                print(f"   MerchantRequestID: {merchant_request_id}")
                print(f"   ResultCode: {result_code}")
                print(f"   ResultDesc: {result_desc}")

            # ⭐⭐⭐ CRITICAL: Safaricom expects EXACTLY this response ⭐⭐⭐
            response = JsonResponse({
                "ResultCode": 0,      # ← Must be 0 to acknowledge receipt
                "ResultDesc": "Success"  # ← Must be "Success"
            })
            print(f"📤 Sending callback response: {response.content}")
            return response
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON decode error: {e}")
            print(f"❌ Raw body that caused error: {request.body}")
            # Still return success to Safaricom to avoid retries
            return JsonResponse({
                "ResultCode": 0,
                "ResultDesc": "Success"
            })
            
        except Exception as e:
            print(f"❌ Error processing callback: {e}")
            import traceback
            traceback.print_exc()
            # Still return success to Safaricom
            return JsonResponse({
                "ResultCode": 0,
                "ResultDesc": "Success"
            })
    
    print(f"⚠ Non-POST request to callback: {request.method}")
    # If not POST, still return proper format
    return JsonResponse({
        "ResultCode": 0,
        "ResultDesc": "Success"
    })