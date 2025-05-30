import requests
import time
import json
from logging_config import setup_logger

logger = setup_logger()

# Clover credentials
base_url = "https://api.clover.com/v3"
token = "c6901d41-8084-c139-985e-0953990e7c48"
mid = "V58PN50E38DX1"

headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "authorization": f"Bearer {token}"
}

def create_customer(customer_data):
    url = f"{base_url}/merchants/{mid}/customers"

    data = {
        "firstName": customer_data["customerAddress"]["firstName"] or None,
        "lastName": customer_data["customerAddress"]["lastName"],
        "customerSince": int(time.time() * 1000),
        "addresses": [
            {
                "address1": customer_data["customerAddress"]["address1"],
                "city": customer_data["customerAddress"]["city"],
                "state": customer_data["customerAddress"]["state"],
                "zip": customer_data["customerAddress"]["postalCode"],
                "country": customer_data["customerAddress"].get("country") or "US"
            },
            {
                "address1": customer_data["shipToAddress"]["address1"],
                "city": customer_data["shipToAddress"]["city"],
                "state": customer_data["shipToAddress"]["state"],
                "zip": customer_data["shipToAddress"]["postalCode"],
                "country": customer_data["shipToAddress"].get("country") or "US"
            }
        ],
        "emailAddresses": [
            { "emailAddress": customer_data["email"] }
        ] if customer_data.get("email") else [],
        "phoneNumbers": [
            { "phoneNumber": customer_data["phone1"] },
            { "phoneNumber": customer_data["phone2"] }
        ],
        "metadata": {
            "businessName": customer_data["customerId"]
        }
    }

    logger.info(f"✅ sending data to create customer: {data}")
    response = requests.post(url, headers=headers, json=data)
    logger.info(f"Status: {response.status_code}")
    try:
        logger.info(f"Response: {response.json()}")
        response_json = response.json()
        return response_json.get('id')
    except Exception:
        logger.error(f"Non-JSON response: {response.text}")

def is_duplicate_customer(customer_id, existing_customers):
    customer_id_str = str(customer_id)  # Ensure it's a string

    for customer in existing_customers:
        existing_business_id = customer.get("metadata", {}).get("businessName")
        if existing_business_id == customer_id_str:
            return True

    return False

def check_miss_customer(all_customers, existing_customers):
    logger.info("check miss customer start")
    for exist_customer in existing_customers:
        exist_customer_id = exist_customer.get("metadata", {}).get("businessName")
        if not exist_customer_id:
            logger.warning(f"Missing businessName in metadata: {exist_customer}")
            continue

        found = any(str(cust.get("id")) == exist_customer_id for cust in all_customers)

        if not found:
            logger.info(f"exist customer id: {exist_customer_id} is missing in all customers, so we delete that customer in Clover account")
            delete_customer(exist_customer.get("id"))


def get_all_clover_customers():
    url = f"{base_url}/merchants/{mid}/customers?expand=addresses,emailAddresses,phoneNumbers,cards,metadata"

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        customers = data.get("elements", [])
        logger.info(f"✅ Retrieved {len(customers)} customers.")
        return customers
    except requests.RequestException as e:
        logger.error(f"❌ Error fetching customers: {e}")
        return []

def delete_order(order_id):
    url = f"{base_url}/merchants/{mid}/orders/{order_id}"
    response = requests.delete(url, headers=headers)

    if response.status_code == 200:
        logger.info(f"[✓] Successfully deleted order {order_id}")
        return True
    else:
        logger.error(f"[!] Failed to delete order {order_id}: {response.status_code} - {response.text}")
        return False

def delete_customer(customer_id):
    url = f"{base_url}/merchants/{mid}/customers/{customer_id}"
    response = requests.delete(url, headers=headers)

    if response.status_code == 200:
        logger.info(f"[✓] Successfully deleted customer {customer_id}")
        return True
    else:
        logger.error(f"[!] Failed to delete customer {customer_id}: {response.status_code} - {response.text}")
        return False

def get_customer_byId(customerId):
    url = f"{base_url}/merchants/{mid}/customers/{customerId}?expand=addresses,phoneNumbers,metadata"
    response = requests.get(url, headers=headers)
    logger.info(response.json())
    return response.json()

def create_item_with_color(product):
    item_name = product["styleName"]
    product_id = product["id"]
    price = int(product["defaultPrice"] * 100)
    sku = product.get("styleNumber", item_name.replace(" ", "-").upper())
    color = product['colors'][0]
    color_id = color['id']

    # Store both in the code field
    code = f"RFMS:{product_id}:{color_id}"

    # Item creation with embedded productId in code
    item_payload = {
        "name": item_name,
        "price": price,
        "code": code,  # Embed productId
    }

    item_resp = requests.post(
        f"{base_url}/merchants/{mid}/items",
        headers=headers,
        json=item_payload
    )

    if item_resp.status_code not in (200, 201):
        logger.info(f"[!] Failed to create item: {item_resp.text}")
        return

    item_data = item_resp.json()
    item_id = item_data["id"]
    logger.info(f"[✓] Created item '{item_name}' with id {item_id}")

    # Create a modifier group for the color(s)
    group_payload = {"name": f"{item_name} Colors"}
    group_resp = requests.post(
        f"{base_url}/merchants/{mid}/modifier_groups",
        headers=headers,
        json=group_payload
    )

    if group_resp.status_code not in (200, 201):
        logger.info(f"[!] Failed to create modifier group: {group_resp.text}")
        return

    group_id = group_resp.json()["id"]
    logger.info(f"[✓] Created modifier group for '{item_name}'")

    # Create modifiers for each color and embed colorId
    for color in product.get("colors", []):
        modifier_payload = {
            "name": color["colorName"],
            "alternateName": f"RFMS_COLOR:{color['id']}",
            "price": 0
        }

        mod_resp = requests.post(
            f"{base_url}/merchants/{mid}/modifier_groups/{group_id}/modifiers",
            headers=headers,
            json=modifier_payload
        )

        if mod_resp.status_code in (200, 201):
            logger.info(f"[✓] Created modifier: {color['colorName']}")
        else:
            logger.info(f"[!] Failed to create modifier '{color['colorName']}': {mod_resp.text}")

    # Assign modifier group to the item
    assign_payload = {
        "elements": [
            {
                "modifierGroup": {"id": group_id},
                "item": {"id": item_id}
            }
        ]
    }

    assign_resp = requests.post(
        f"{base_url}/merchants/{mid}/item_modifier_groups",
        headers=headers,
        json=assign_payload
    )

    if assign_resp.status_code in (200, 201):
        logger.info(f"[✓] Assigned modifier group to item {item_id}")
        return item_id
    else:
        logger.info(f"[!] Failed to assign modifier group: {assign_resp.text}")

    return item_id

def is_duplicate_product(product, clover_items):
    """
    Check if the product with specific product_id and color_id already exists in Clover.
    """
    product_id = product["id"]
    color_id = product["colors"][0]["id"]
    generated_code = f"RFMS:{product_id}:{color_id}"

    for item in clover_items:
        if item.get("code") == generated_code:
            update_item_with_color(product, item.get("id"))
            logger.info(f"✅ Update product in Clover for id successful: {item.get("id")}")
            return True

    logger.info(f"✅ No duplicate found for code: {generated_code}")
    return False

def update_item_with_color(product, item_id):
    price = int(product["defaultPrice"] * 100)

    item_payload = {
        "price": price,
    }

    item_resp = requests.post(
        f"{base_url}/merchants/{mid}/items/{item_id}",
        headers=headers,
        json=item_payload
    )

    if item_resp.status_code not in (200, 201):
        logger.info(f"[!] Failed to update item: {item_resp.text}")
        return

    logger.info(f"[✓] Updated item with id {item_id}")

    return item_id


def extract_rfms_info(item):
    # Get productId and colorId from code
    code = item.get("code", "")
    product_id = color_id = None

    if code.startswith("RFMS:"):
        parts = code.split(":")
        if len(parts) == 3:
            product_id = parts[1]
            color_id = parts[2]

    # Get unit price in dollars
    unit_price = item.get("price", 0) / 100

    return {
        "productId": product_id,
        "colorId": color_id,
        "unitPrice": unit_price
    }

def get_employee_by_id(emp_id, expand=None):
    url = f"{base_url}/merchants/{mid}/employees/{emp_id}"
    
    params = {}
    if expand:
        params["expand"] = expand  # Example: "roles,shifts"

    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        logger.info(f"[✓] Retrieved employee {emp_id}")
        return response.json()
    else:
        logger.error(f"[!] Failed to fetch employee {emp_id}: {response.status_code} - {response.text}")
        return None

def get_orders(expand=None):
    url = f"{base_url}/merchants/{mid}/orders"

    params = {}
    if expand:
        params["expand"] = expand

    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        orders = response.json().get("elements", [])
        logger.info(f"[✓] Retrieved {len(orders)} orders")
        for order in orders:
            logger.info(f"→ Order ID: {order['id']}, Title: {order.get('title')}, Total: {order.get('total')}")
        return orders
    else:
        logger.error(f"[!] Failed to get orders: {response.status_code} - {response.text}")
        return []


def get_order_details(order_id):
    url = f"{base_url}/merchants/{mid}/orders/{order_id}?expand=lineItems,customers,payments"

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        order_details = response.json()
        # logger.info(f"[✓] Order Details for {order_id}:")
        # logger.info(json.dumps(order_details, indent=2))
        return order_details
    else:
        logger.error(f"[!] Failed to fetch order details: {response.status_code} - {response.text}")
        return None

def create_order():
    url = f"{base_url}/merchants/{mid}/orders"
    
    payload = {
        "title": "Sample Test Order",
        "state": "open",  # or "locked" / "completed"
        "note": "Test order created via API",
        "clientCreatedTime": int(time.time() * 1000)
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code in (200, 201):
        order = response.json()
        logger.info(f"[✓] Created order: {order.get('id')}")
        logger.info(json.dumps(order, indent=2))
        return order
    else:
        logger.error(f"[!] Failed to create order: {response.status_code} - {response.text}")
        return None
    
def get_tender_ids():
    # Fetch available tenders
    url = f"{base_url}/merchants/{mid}/tenders"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        tenders = response.json().get("elements", [])
        return tenders
    else:
        logger.error(f"[!] Failed to fetch tenders: {response.status_code} - {response.text}")
        return []
    
def get_tender_by_id(tender_id):
    # Clover API endpoint to get tender by ID
    url = f"{base_url}/merchants/{mid}/tenders/{tender_id}"

    # Send GET request to Clover API to fetch tender details
    response = requests.get(url, headers=headers)

    # Check for successful response
    if response.status_code == 200:
        return response.json()  # Return tender details as a JSON object
    else:
        return {"error": f"Failed to get tender: {response.status_code} - {response.text}"}

def post_payment_to_order(order_id, tender_id, amount_in_cents):
    # Post a payment to the specified order
    url = f"{base_url}/merchants/{mid}/orders/{order_id}/payments"

    # Build the payment payload
    payload = {
        "tender": {
            "id": tender_id
        },
        "amount": amount_in_cents,  # Total amount paid in cents
        "tipAmount": 0,             # Optional, if there is a tip
        "taxAmount": 0,             # Optional, if there is tax
        "externalPaymentId": f"ext-{int(time.time())}",  # Use an external reference for the payment
        "offline": False,
        "result": "Success"  # Mark the result as success
    }

    logger.info(f"Sending payment to order {order_id}: {payload}")
    response = requests.post(url, headers=headers, json=payload)

    if response.status_code in (200, 201):
        logger.info(f"[✓] Payment posted to order {order_id}")
        return response.json()
    else:
        logger.error(f"[!] Failed to post payment to order {order_id}: {response.status_code} - {response.text}")
        return None

def attach_customer_to_order(order_id, customer_id):
    url = f"{base_url}/merchants/{mid}/orders/{order_id}"
    customer_detail = get_customer_byId(customer_id)
    payload = {
        "id": order_id,
        "customers": [
            {
                "id": customer_id,
                "customerAddress": customer_detail["addresses"]["elements"][0],
                "shipToAddress": customer_detail["addresses"]["elements"][1]
            }
        ]
    }

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code in (200, 201):
        logger.info(f"[✓] Attached customer {customer_id} to order {order_id}")
    else:
        logger.error(f"[!] Failed to attach customer: {response.status_code} - {response.text}")

def add_line_item_to_order(order_id, item_id, price_in_cents, quantity=1):
    url = f"{base_url}/merchants/{mid}/orders/{order_id}/line_items"

    payload = {
        "item": { "id": item_id },
        "price": price_in_cents,
        "quantity": quantity
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code in (200, 201):
        logger.info(f"[✓] Added line item to order {order_id}")
        return response.json()
    else:
        logger.error(f"[!] Failed to add line item: {response.status_code} - {response.text}")
        return None

def get_item_by_id(item_id):
    url = f"{base_url}/merchants/{mid}/items/{item_id}"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        logger.info(f"[✓] Fetched item {item_id}")
        return response.json()
    else:
        logger.info(f"[!] Failed to fetch item {item_id}: {response.status_code} - {response.text}")
        return None

def fetch_all_clover_items():
    response = requests.get(
        f"{base_url}/merchants/{mid}/items?limit=1000",
        headers=headers
    )
    if response.status_code == 200:
        return response.json().get("elements", [])
    else:
        logger.warning(f"❌ Failed to fetch Clover items: {response.text}")
        return []


def check_miss_product(all_products, existing_items):
    logger.info("check miss product start")

    rfms_ids = {str(p["id"]) for p in all_products}

    for item in existing_items:
        code = item.get("code", "")
        if not code.startswith("RFMS:"):
            continue

        try:
            _, product_id, _ = code.split(":")
        except ValueError:
            logger.warning(f"[!] Invalid code format: {code}")
            continue

        if product_id not in rfms_ids:
            item_id = item.get("id")
            logger.info(f"[→] Deleting item not in RFMS: {item_id}")

            cleanup_modifier_groups(item_id)
            delete_item(item_id)

def delete_item(item_id):
    url = f"{base_url}/merchants/{mid}/items/{item_id}"
    response = requests.delete(url, headers=headers)

    if response.status_code == 200:
        logger.info(f"[✓] Successfully deleted item {item_id}")
        return True
    else:
        logger.error(f"[!] Failed to delete item {item_id}: {response.status_code} - {response.text}")
        return False

def cleanup_modifier_groups(item_id):
    groups = get_modifier_groups_by_item(item_id)

    for group in groups:
        group_id = group.get("id")
        if not group_id:
            continue

        # Delete all modifiers in this group
        modifiers = get_modifiers_by_group(group_id)
        for mod in modifiers:
            mod_id = mod.get("id")
            if not mod_id:
                continue

            mod_url = f"{base_url}/merchants/{mid}/modifier_groups/{group_id}/modifiers/{mod_id}"
            del_resp = requests.delete(mod_url, headers=headers)

            if del_resp.status_code == 200:
                logger.info(f"[✓] Deleted modifier {mod_id} from group {group_id}")
            else:
                logger.warning(f"[!] Failed to delete modifier {mod_id}: {del_resp.text}")

        # Delete the modifier group
        group_url = f"{base_url}/merchants/{mid}/modifier_groups/{group_id}"
        group_del_resp = requests.delete(group_url, headers=headers)

        if group_del_resp.status_code == 200:
            logger.info(f"[✓] Deleted modifier group {group_id}")
        else:
            logger.warning(f"[!] Failed to delete modifier group {group_id}: {group_del_resp.text}")

def get_modifier_groups_by_item(item_id):
    url = f"{base_url}/merchants/{mid}/modifier_groups?filter=item.id={item_id}"
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        logger.warning(f"[!] Failed to get modifier groups for item {item_id}")
        return []

    return response.json().get("elements", [])

def get_modifiers_by_group(group_id):
    url = f"{base_url}/merchants/{mid}/modifiers?filter=modifierGroup.id={group_id}"
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        logger.warning(f"[!] Failed to get modifiers for group {group_id}")
        return []

    return response.json().get("elements", [])