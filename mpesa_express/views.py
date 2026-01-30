from datetime import datetime
import requests
import base64
import re
import json
import hashlib
import hmac
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required
import os
from django.conf import settings
from .forms import PaymentForm
import uuid

# ==================== Nestlink Configuration ====================
NESTLINK_API_SECRET = "40d66c73c9e25a66aaa18654"  # Your API secret
NESTLINK_BASE_URL = "https://api.nestlink.co.ke"
NESTLINK_CALLBACK_URL = "https://starrlnk.shop/nestlink/callback/"  # Your callback URL
NESTLINK_MERCHANT_ID = "your_merchant_id"  # Replace with your Nestlink merchant ID

# ==================== PWA Manifest data ====================
PWA_MANIFEST = {
    "name": "Starlink Kenya",
    "short_name": "Starlink",
    "description": "High-Speed Satellite Internet Payments - Powered by SpaceX",
    "start_url": "/",
    "display": "standalone",
    "background_color": "#0a0e17",
    "theme_color": "#3ecf8e",
    "orientation": "portrait",
    "scope": "/",
    "categories": ["business", "finance", "utilities"],
    "icons": [
        {
            "src": "/static/icons/icon-72x72.png",
            "sizes": "72x72",
            "type": "image/png",
            "purpose": "any maskable"
        },
        {
            "src": "/static/icons/icon-96x96.png",
            "sizes": "96x96",
            "type": "image/png",
            "purpose": "any maskable"
        },
        {
            "src": "/static/icons/icon-128x128.png",
            "sizes": "128x128",
            "type": "image/png",
            "purpose": "any maskable"
        },
        {
            "src": "/static/icons/icon-144x144.png",
            "sizes": "144x144",
            "type": "image/png",
            "purpose": "any maskable"
        },
        {
            "src": "/static/icons/icon-152x152.png",
            "sizes": "152x152",
            "type": "image/png",
            "purpose": "any maskable"
        },
        {
            "src": "/static/icons/icon-192x192.png",
            "sizes": "192x192",
            "type": "image/png",
            "purpose": "any maskable"
        },
        {
            "src": "/static/icons/icon-384x384.png",
            "sizes": "384x384",
            "type": "image/png",
            "purpose": "any maskable"
        },
        {
            "src": "/static/icons/icon-512x512.png",
            "sizes": "512x512",
            "type": "image/png",
            "purpose": "any maskable"
        }
    ]
}

# ==================== Helper Functions ====================
def format_phone_number(phone):
    """Format phone number for Nestlink"""
    phone = phone.replace("+", "").replace(" ", "").replace("-", "")
    if re.match(r"^254\d{9}$", phone):
        return phone
    elif phone.startswith("0") and len(phone) == 10:
        return "254" + phone[1:]
    elif len(phone) == 9 and phone.startswith("7"):
        return "254" + phone
    else:
        raise ValueError(f"Invalid phone number format: {phone}. Use format: 0712345678 or 254712345678")

def generate_transaction_id():
    """Generate unique transaction ID"""
    return f"STARLINK_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8].upper()}"

def make_nestlink_request(endpoint, data):
    """Make requests to Nestlink API"""
    headers = {
        "Content-Type": "application/json",
        "Api-Secret": NESTLINK_API_SECRET
    }
    
    url = f"{NESTLINK_BASE_URL}{endpoint}"
    
    try:
        print(f"🌐 Sending request to Nestlink API: {url}")
        print(f"📤 Request data: {data}")
        
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        print(f"🌐 Nestlink API Response Status: {response.status_code}")
        print(f"📥 Raw response text: {response.text}")
        
        if response.status_code not in [200, 201]:
            print(f"❌ Nestlink HTTP Error: {response.status_code}")
            print(f"❌ Response: {response.text}")
            return None
        
        try:
            response_data = response.json()
            print(f"✅ Nestlink API Response: {response_data}")
            return response_data
        except json.JSONDecodeError:
            print(f"⚠️ Response is not valid JSON: {response.text}")
            # Return as dict with raw text if not JSON
            return {"raw_text": response.text, "status_code": response.status_code}
        
    except requests.exceptions.Timeout:
        print("❌ Nestlink request timeout")
        return None
    except requests.exceptions.RequestException as e:
        print(f"❌ Nestlink network error: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error with Nestlink: {e}")
        return None

# ==================== Nestlink Payment Functions ====================
def initiate_nestlink_payment(phone, amount, package_name):
    """Initiate payment via Nestlink"""
    try:
        print(f"🔄 Initiating Nestlink payment for {phone}, amount: {amount}")
        
        # Generate unique transaction ID
        transaction_id = generate_transaction_id()
        
        # Prepare payment request data according to Nestlink API documentation
        payment_data = {
            "phone": phone,
            "amount": amount,
            "local_id": transaction_id,
            "transaction_desc": f"Starlink {package_name} Package Payment"
        }
        
        print(f"📤 Sending to Nestlink API: {payment_data}")
        
        # Make API request to /runPrompt endpoint
        response = make_nestlink_request("/runPrompt", data=payment_data)
        
        # Check if response exists and has successful status
        # Nestlink returns "status": True for success, not "status": "success"
        if response and response.get("status") == True:
            print(f"✅ Nestlink payment initiated successfully")
            print(f"📋 Response: {response}")
            
            # Extract CheckoutRequestID and MerchantRequestID from response
            checkout_request_id = response.get("data", {}).get("CheckoutRequestID", "")
            merchant_request_id = response.get("data", {}).get("MerchantRequestID", "")
            
            # Store transaction data (you might want to save to database)
            transaction_data = {
                "transaction_id": transaction_id,
                "phone": phone,
                "amount": amount,
                "package_name": package_name,
                "status": "pending",
                "created_at": datetime.now().isoformat(),
                "checkout_request_id": checkout_request_id,
                "merchant_request_id": merchant_request_id,
                "response_code": response.get("data", {}).get("ResponseCode", ""),
                "response_description": response.get("data", {}).get("ResponseDescription", "")
            }
            
            return {
                "status": "success",
                "message": response.get("msg", "Payment prompt sent successfully"),
                "transaction_id": transaction_id,
                "checkout_request_id": checkout_request_id,
                "merchant_request_id": merchant_request_id,
                "nestlink_response": response,
                "transaction_data": transaction_data
            }
        else:
            # Check for different error response formats
            error_message = response.get("msg") if response else "API request failed"
            if not error_message:
                error_message = response.get("message", "Failed to initiate payment")
            
            print(f"❌ Nestlink payment failed: {error_message}")
            return {
                "status": "error",
                "message": error_message,
                "transaction_id": transaction_id,
                "raw_response": response
            }
            
    except Exception as e:
        print(f"❌ Error initiating Nestlink payment: {e}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "message": f"Unexpected error: {str(e)}"
        }

# ==================== PWA Views ====================
@require_GET
def manifest_view(request):
    """Serve PWA manifest.json"""
    return JsonResponse(PWA_MANIFEST)

@require_GET
def service_worker(request):
    """Serve service worker"""
    sw_path = os.path.join(settings.BASE_DIR, 'static/js/serviceworker.js')
    
    try:
        with open(sw_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        # Default service worker content
        content = """
        const CACHE_NAME = 'starlink-cache-v1.0';
        const OFFLINE_URL = '/offline/';
        
        self.addEventListener('install', event => {
            event.waitUntil(
                caches.open(CACHE_NAME)
                    .then(cache => cache.addAll([
                        '/',
                        OFFLINE_URL,
                        '/static/icons/icon-192x192.png'
                    ]))
            );
        });
        
        self.addEventListener('fetch', event => {
            if (event.request.mode === 'navigate') {
                event.respondWith(
                    fetch(event.request)
                        .catch(() => caches.match(OFFLINE_URL))
                );
                return;
            }
            event.respondWith(
                caches.match(event.request)
                    .then(response => response || fetch(event.request))
            );
        });
        """
    
    response = HttpResponse(content, content_type='application/javascript')
    response['Service-Worker-Allowed'] = '/'
    return response

def offline_view(request):
    """Offline page"""
    return render(request, 'mpesa_express/offline.html')

# ==================== Main Views ====================
def home(request):
    """Home page with PWA context"""
    context = {
        'pwa_enabled': True,
        'app_name': 'Starlink Kenya',
        'theme_color': '#3ecf8e',
        'background_color': '#0a0e17',
    }
    return render(request, 'mpesa_express/index.html', context)

def pending_payment(request):
    """Pending payment page with PWA support"""
    phone_number = request.session.get("phone_number", "")
    amount = request.session.get("amount", 0)
    package_name = request.session.get("package_name", "")
    transaction_id = request.session.get("transaction_id", "")
    checkout_request_id = request.session.get("checkout_request_id", "")
    
    context = {
        "phone_number": phone_number,
        "amount": amount,
        "package_name": package_name,
        "transaction_id": transaction_id,
        "checkout_request_id": checkout_request_id,
        'pwa_enabled': True,
        "payment_provider": "nestlink"
    }
    
    return render(request, "mpesa_express/pending.html", context)

# ==================== Nestlink API Views ====================
@csrf_exempt
def nestlink_payment(request):
    """Handle payment requests via Nestlink"""
    if request.method == "POST":
        try:
            print(f"📨 Received Nestlink payment request")
            data = json.loads(request.body)
            print(f"📝 Request data: {data}")
            
            phone = format_phone_number(data["phone_number"])
            amount = int(data["amount"])
            package_name = data.get("package_name", "Unknown Package")

            print(f"📱 Processing Nestlink payment for phone: {phone}, amount: {amount}, package: {package_name}")

            response = initiate_nestlink_payment(phone, amount, package_name)
            
            print(f"📊 Nestlink Payment Response: {response}")

            if response.get("status") == "success":
                # Success - Payment initiated
                print(f"✅ Nestlink payment initiated successfully!")
                print(f"   Transaction ID: {response.get('transaction_id')}")
                print(f"   CheckoutRequestID: {response.get('checkout_request_id')}")
                print(f"   MerchantRequestID: {response.get('merchant_request_id')}")
                
                # Store in session
                request.session["phone_number"] = phone
                request.session["transaction_id"] = response.get("transaction_id", "")
                request.session["checkout_request_id"] = response.get("checkout_request_id", "")
                request.session["merchant_request_id"] = response.get("merchant_request_id", "")
                request.session["amount"] = amount
                request.session["package_name"] = package_name
                
                # Save session immediately
                request.session.save()
                
                return JsonResponse({
                    "status": "success", 
                    "redirect_url": "/payment/pending/",
                    "message": response.get("message", "Payment prompt sent to your phone. Please complete the payment."),
                    "transaction_id": response.get("transaction_id", ""),
                    "checkout_request_id": response.get("checkout_request_id", ""),
                    "merchant_request_id": response.get("merchant_request_id", "")
                })
            else:
                # Failed to initiate payment
                error_message = response.get("message", "Failed to initiate payment. Please try again.")
                
                print(f"❌ Nestlink payment failed: {error_message}")
                return JsonResponse({
                    "status": "error", 
                    "message": error_message,
                    "debug": response.get("raw_response", {})
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

@csrf_exempt
def nestlink_callback(request):
    """Handle Nestlink payment callback"""
    if request.method == "POST":
        try:
            # Log the incoming data for debugging
            raw_body = request.body.decode("utf-8")
            print(f"📞 Raw Nestlink callback received: {raw_body}")
            
            data = json.loads(raw_body)
            print("📋 Parsed Nestlink Callback Data:", json.dumps(data, indent=2))

            # Extract transaction details based on M-Pesa callback structure (since Nestlink seems to use M-Pesa format)
            # Based on the response, it looks like Nestlink is returning M-Pesa formatted data
            stk_callback = data.get('Body', {}).get('stkCallback', {})
            
            if stk_callback:
                # This is M-Pesa STK push callback format
                result_code = stk_callback.get('ResultCode', 1)
                checkout_request_id = stk_callback.get('CheckoutRequestID', '')
                merchant_request_id = stk_callback.get('MerchantRequestID', '')
                result_desc = stk_callback.get('ResultDesc', '')
                
                if result_code == 0:
                    # Successful payment
                    print(f"✅ Nestlink Payment Successful!")
                    print(f"   CheckoutRequestID: {checkout_request_id}")
                    print(f"   MerchantRequestID: {merchant_request_id}")
                    print(f"   ResultDesc: {result_desc}")
                    
                    # Extract transaction details
                    callback_metadata = stk_callback.get('CallbackMetadata', {}).get('Item', [])
                    for item in callback_metadata:
                        name = item.get('Name', '')
                        value = item.get('Value', '')
                        print(f"   {name}: {value}")
                    
                    print(f"💰 Nestlink transaction completed successfully!")
                    
                    # TODO: Update your database with successful payment
                    # TODO: Send confirmation email/SMS to customer
                    # TODO: Activate customer's subscription
                    
                else:
                    # Failed payment
                    print(f"❌ Nestlink Payment Failed!")
                    print(f"   CheckoutRequestID: {checkout_request_id}")
                    print(f"   MerchantRequestID: {merchant_request_id}")
                    print(f"   ResultCode: {result_code}")
                    print(f"   ResultDesc: {result_desc}")
                    
                    # TODO: Update your database with failed payment
                    # TODO: Notify customer about failed payment
            else:
                # Try alternative callback format
                status = data.get('status', '').lower()
                transaction_id = data.get('local_id', '') or data.get('transaction_id', '')
                phone = data.get('phone', '')
                amount = data.get('amount', 0)
                
                if status in ['success', 'completed']:
                    print(f"✅ Nestlink Payment Successful! (Alternative format)")
                    print(f"   Transaction ID: {transaction_id}")
                    print(f"   Phone: {phone}")
                    print(f"   Amount: {amount}")
                elif status in ['failed', 'cancelled']:
                    print(f"❌ Nestlink Payment Failed! (Alternative format)")
                    print(f"   Transaction ID: {transaction_id}")
                    print(f"   Phone: {phone}")
                    print(f"   Amount: {amount}")

            # Return success response to Nestlink (M-Pesa format)
            response = JsonResponse({
                "ResultCode": 0,
                "ResultDesc": "Success"
            })
            
            print(f"📤 Sending callback response: {response.content}")
            return response
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON decode error: {e}")
            print(f"❌ Raw body that caused error: {request.body}")
            return JsonResponse({
                "ResultCode": 0,
                "ResultDesc": "Success"
            })
            
        except Exception as e:
            print(f"❌ Error processing Nestlink callback: {e}")
            import traceback
            traceback.print_exc()
            return JsonResponse({
                "ResultCode": 0,
                "ResultDesc": "Success"
            })
    
    print(f"⚠ Non-POST request to callback: {request.method}")
    return JsonResponse({
        "ResultCode": 0,
        "ResultDesc": "Success"
    })

# ==================== Payment Status Check ====================
@csrf_exempt
def check_payment_status(request):
    """Check payment status (for frontend polling)"""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            checkout_request_id = data.get("checkout_request_id", "")
            transaction_id = data.get("transaction_id", "")
            
            if not checkout_request_id and not transaction_id:
                return JsonResponse({"status": "error", "message": "CheckoutRequestID or TransactionID required"})
            
            # Note: Nestlink might use M-Pesa's query endpoint
            # For now, we'll return pending status
            # You should implement actual status checking
            
            return JsonResponse({
                "status": "success",
                "payment_status": "pending",  # Placeholder - update with actual status
                "transaction_id": transaction_id,
                "checkout_request_id": checkout_request_id,
                "message": "Payment status check - implement actual Nestlink status API"
            })
                
        except Exception as e:
            print(f"❌ Error checking payment status: {e}")
            return JsonResponse({
                "status": "error",
                "message": "Error checking payment status"
            })
    
    return JsonResponse({"status": "error", "message": "Invalid request method"})