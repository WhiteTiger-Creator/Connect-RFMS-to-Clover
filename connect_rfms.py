import os
import requests
from requests.auth import HTTPBasicAuth
from connect_clover import get_tender_by_id
import json
from datetime import datetime
from logging_config import setup_logger

logger = setup_logger()

os.makedirs("order_data", exist_ok=True)
PROCESSED_ORDERS_FILE = "order_data/processed_orders.json"

rfmsTypeMap = {
    "Cash": "cash",
    "Check": "check",
    "Credit Card": "creditcard",
    "Debit Card": "debitcard",
    "External Payment": "EXTERNAL"
}

# Begin session with RFMS API
def get_session(store, api_key):
    url = "https://api.rfms.online/v2/session/begin"
    logger.info(f"Sending POST request to {url} with Basic Auth")

    response = requests.post(url, auth=HTTPBasicAuth(store, api_key))

    logger.info(f"Status Code: {response.status_code}")
    logger.info(f"Response Headers: {response.headers}")
    logger.info(f"Response Body: {response.text}")

    if response.ok:
        data = response.json()
        if data.get("authorized"):
            session_token = data["sessionToken"]
            session_expires = data["sessionExpires"]
            logger.info(f"✅ Session Token: {session_token}")
            logger.info(f"⏰ Expires: {session_expires}")
            return session_token
        else:
            logger.error("❌ Not authorized.")
    else:
        logger.error(f"❌ Request failed with status code {response.status_code}")
    return None  # In case of failure

# Get all customers (returns stores list or other fields from the API response)
def get_all_customers(store, token):
    url = "https://api.rfms.online/v2/customers"
    logger.info(f"📡 Sending GET request to {url} with session token as Basic Auth")

    response = requests.get(url, auth=HTTPBasicAuth(store, token))

    logger.info(f"Status Code: {response.status_code}")
    logger.info(f"Response Headers: {response.headers}")
    logger.info(f"Response Body: {response.text}")

    if response.ok:
        data = response.json()
        logger.info(f"✅ Parsed Customer Fields: {data}")
        # Assuming the customers are part of the "stores" field in this case
        return data.get("stores", [])  # Adjust the field based on the actual data you want
    else:
        logger.error("❌ Failed to fetch customer values.")
        return None

# Get customer by ID
def get_customer_by_id(store, token, customer_id):
    url = f"https://api.rfms.online/v2/customer/{customer_id}"
    logger.info(f"📡 Sending GET request to {url} with session token as Basic Auth")

    response = requests.get(url, auth=HTTPBasicAuth(store, token))

    logger.info(f"Status Code: {response.status_code}")
    logger.info(f"Response Headers: {response.headers}")
    logger.info(f"Response Body: {response.text}")

    if response.ok:
        data = response.json()
        logger.info(f"✅ Parsed Customer Info for ID {customer_id}: {data}")
        return data
    else:
        logger.error(f"❌ Failed to fetch details for customer ID {customer_id}.")
        return None

# Get product codes
def get_product_codes(store, token):
    url = "https://api.rfms.online/v2/product/get/productcodes"
    logger.info(f"📡 Sending GET request to {url} with session token as Basic Auth")

    response = requests.get(url, auth=HTTPBasicAuth(store, token))

    logger.info(f"Status Code: {response.status_code}")
    logger.info(f"Response Headers: {response.headers}")
    logger.info(f"Response Body: {response.text}")

    if response.ok:
        data = response.json()
        logger.info(f"✅ Product Codes: {data}")
        return data
    else:
        logger.error("❌ Failed to fetch product codes.")
        return None

def get_products_by_code(store, api_key, product_code):
    url = "https://api.rfms.online/v2/product/find"
    headers = {"Content-Type": "application/json"}

    # page = 1
    all_products = []
    payload = {
        "productCode": product_code,
        "searchText": "STOCK CLOVER"
    }


    response = requests.post(url, auth=HTTPBasicAuth(store, api_key), headers=headers, json=payload)
    data = response.json()
    products = data.get("detail", [])
    if products:
        logger.info(f"✅ Total products found: {len(products)}")
        save_to_json(products, "product_data.json")
        return products
    else:
        logger.error(f"❌ No product at product code: {product_code}")

def timestamp_to_date(ms_timestamp):
    dt = datetime.fromtimestamp(ms_timestamp / 1000)
    return dt.strftime("%Y-%m-%d")

def get_rfms_customer_by_id(customer_id, store, api_key):
    url = f"https://api.rfms.online/v2/customer/{customer_id}"
    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.get(url, auth=HTTPBasicAuth(store, api_key), headers=headers)
        
        if response.status_code == 200:
            customer_data = response.json()
            logger.info(f"✅ Customer {customer_id} fetched successfully.")
            return customer_data
        else:
            logger.error(f"❌ Failed to fetch customer {customer_id}: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.exception("Exception occurred while fetching customer from RFMS.")
        return None
    
def get_payments_by_order_number(store, api_key, order_number):
    url = f"https://api.rfms.online/v2/order/payments/{order_number}"
    headers = {"Content-Type": "application/json"}

    logger.info(f"💳 Fetching payments for order number {order_number} from {url}")

    try:
        response = requests.get(url, auth=HTTPBasicAuth(store, api_key), headers=headers)

        logger.info(f"Status Code: {response.status_code}")
        logger.info(f"Response Body: {response.text}")

        if response.status_code == 200:
            payments = response.json()
            logger.info(f"✅ Payments retrieved: {payments}")
            return payments
        else:
            logger.error(f"❌ Failed to retrieve payments for order {order_number}: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.exception(f"❌ Exception while retrieving payments for order {order_number}.")
        return None
    
def post_payment_to_rfms(store, api_key, rfms_order_id, order_detail, rfms_lineitem):
    try:
        
        tender_id = order_detail["payments"]["elements"][0]["tender"]["id"]
        tender = get_tender_by_id(tender_id)
        order_number = order_detail.get("id", "PO-UNKNOWN")
        logger.info(f"✅ tender type: {rfmsTypeMap[tender["label"]]}")
        # Prepare the payment payload
        payment_payload = {
            "documentNumber": rfms_order_id,
            "paymentMethod": rfmsTypeMap[tender["label"]],
            "paymentAmount": rfms_lineitem["unitPrice"] * 100,
            "approvalCode": order_detail["payments"]["elements"][0]["externalPaymentId"],
            "receiptAccountId": "12",
            "paymentFee": "0.1",
            "paymentReference": order_number
        }

        # RFMS payment API URL
        url = "https://api.rfms.online/v2/payment"
        headers = {"Content-Type": "application/json"}

        # Make the POST request to RFMS
        response = requests.post(
            url,
            auth=HTTPBasicAuth(store, api_key),
            headers=headers,
            json=payment_payload
        )

        # Check the response from RFMS
        if response.status_code == 200:
            logger.info(f"✅ Payment successfully recorded for order {order_number}. Response: {response.json()}")
        elif response.status_code == 202:
            # If the response is 'waiting', store the messageId and retry later
            message_id = response.json().get("detail")
            logger.info(f"⏳ Store response is 'waiting'. Message ID: {message_id}.")
            return message_id
        else:
            logger.error(f"❌ Failed to record payment for order {order_number}. Status: {response.status_code} - {response.text}")
            return None

    except Exception as e:
        logger.exception(f"❌ Exception while posting payment to RFMS for order {order_number}: {e}")
        return None

def push_order_to_rfms(store, api_key, clover_order, rfms_customer, results):
    try:

        # Extract customer info
        sold_to = {
            "customerId": int(rfms_customer['metadata']['businessName'])
            # "firstName": rfms_customer.get('firstName', ''),
            # "lastName":rfms_customer.get('lastName', 'Unknown'),
            # "address1": rfms_customer['addresses']['elements'][0].get("address1", ""),
            # "address2": rfms_customer['addresses']['elements'][0].get("address2", ""),
            # "city": rfms_customer['addresses']['elements'][0].get("city", ""),
            # "state": rfms_customer['addresses']['elements'][0].get("state", ""),
            # "postalCode": rfms_customer['addresses']['elements'][0].get("zip", ""),
            # "phoneNumber": rfms_customer['phoneNumbers']['elements'][0].get("phoneNumber", "")
        }

        ship_to = {
            "customerId": int(rfms_customer['metadata']['businessName']),
            "firstName": rfms_customer.get('firstName', ''),
            "lastName":rfms_customer.get('lastName', 'Unknown'),
            "address1": rfms_customer['addresses']['elements'][1].get("address1", ""),
            "address2": rfms_customer['addresses']['elements'][1].get("address2", ""),
            "city": rfms_customer['addresses']['elements'][1].get("city", ""),
            "state": rfms_customer['addresses']['elements'][1].get("state", ""),
            "postalCode": rfms_customer['addresses']['elements'][1].get("zip", ""),
            "phoneNumber": rfms_customer['phoneNumbers']['elements'][0].get("phoneNumber", "")
        }

        po_number = clover_order.get("id", "PO-UNKNOWN")

        line_items = []
        for rfms_line in results:
            line_items.append({
                "productId": rfms_line["productId"],
                "colorId": rfms_line["colorId"],
                "quantity": 1,
                "unitPrice": rfms_line["unitPrice"]
            })

        # Build RFMS order payload
        order_payload = {
            "poNumber": po_number,
            "jobNumber": f"Clover-{po_number}",
            "soldTo": sold_to,
            "shipTo": ship_to,
            "orderDate": timestamp_to_date(clover_order["createdTime"]),
            "publicNotes": clover_order.get("note", ""),
            "notes": f"Paid in Clover - Order ID: {po_number}",
            "lines": line_items,
            "salesperson1": "CASH SALE",  # Set salesperson to CASH SALE
            "estimatedDeliveryDate": timestamp_to_date(clover_order["createdTime"])  # Same as order date
        }

        url = "https://api.rfms.online/v2/order/create"
        headers = {"Content-Type": "application/json"}
        response = requests.post(
            url,
            auth=HTTPBasicAuth(store, api_key),
            headers=headers,
            json=order_payload
        )

        logger.info(f"📦 Sending order payload: {order_payload}")

        if response.status_code == 200:
            logger.info("✅ Order successfully created in RFMS.")
            try:
                response_data = response.json()
            except ValueError:
                logger.error("❌ Response is not valid JSON: %s", response.text)
                return None

            logger.info(f"Response: {response_data}")

            order_id = response_data.get('result')  # Just use the string directly
            return order_id
        else:
            logger.error(f"❌ Failed to create order: {response.status_code} - {response.text}")

    except Exception as e:
        logger.exception("❌ Exception while pushing order to RFMS.")

def get_all_orders(store, api_key):
    url = "https://api.rfms.online/v2/order"
    headers = {"Content-Type": "application/json"}

    logger.info(f"📋 Fetching all orders from {url}")

    try:
        response = requests.get(url, auth=HTTPBasicAuth(store, api_key), headers=headers)

        logger.info(f"Status Code: {response.status_code}")
        logger.info(f"Response Body: {response.text}")

        if response.status_code == 200:
            data = response.json()
            logger.info("✅ All orders retrieved successfully.")
            return data.get("orders", [])  # adjust key if needed based on response structure
        else:
            logger.error(f"❌ Failed to retrieve orders: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        logger.exception("❌ Exception while retrieving all orders.")
        return []
    
def get_order_by_number(store, api_key, order_number, lock_order=False):
    lock_flag = "true" if lock_order else "false"
    url = f"https://api.rfms.online/v2/order/{order_number}?locked={lock_flag}"
    headers = {"Content-Type": "application/json"}

    logger.info(f"🔍 Fetching order #{order_number} with lock={lock_flag}")

    try:
        response = requests.get(url, auth=HTTPBasicAuth(store, api_key), headers=headers)

        logger.info(f"Status Code: {response.status_code}")
        logger.info(f"Response Headers: {response.headers}")
        logger.info(f"Response Body: {response.text}")

        if response.status_code == 200:
            data = response.json()
            logger.info(f"✅ Order {order_number} retrieved successfully.")
            return data
        else:
            logger.error(f"❌ Failed to fetch order {order_number}: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.exception(f"❌ Exception while retrieving order {order_number}.")
        return None

def load_processed_orders():
    if not os.path.exists(PROCESSED_ORDERS_FILE):
        return set()
    with open(PROCESSED_ORDERS_FILE, "r") as f:
        return set(json.load(f))

def save_processed_order(order_id):
    processed = load_processed_orders()
    processed.add(order_id)
    with open(PROCESSED_ORDERS_FILE, "w") as f:
        json.dump(list(processed), f)

# Save customer data to a JSON file
def save_to_json(data, filename):
    try:
        os.makedirs("data", exist_ok=True)
        filepath = os.path.join("data", filename)
        with open(filepath, "w", encoding="utf-8") as json_file:
            json.dump(data, json_file, indent=4)
        logger.info(f"✅ Data saved to {filepath}")
    except Exception as e:
        logger.error(f"❌ Failed to save data to file: {e}")
