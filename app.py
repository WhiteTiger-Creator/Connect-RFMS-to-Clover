from connect_rfms import *
from connect_clover import *
from datetime import datetime
import json
from logging_config import setup_logger

logger = setup_logger()

# Store credentials
store = "store-5bdc724d88af4c468f2b2e03af1724aa"
api_key = "2960f43f9a20484b8a531665695639cf"

def fetch_allCustomers(session_token):
    # get all customers and push customers to clover
    customer_ids = []
    all_customers = get_all_customers(store, session_token)
    clover_customers = get_all_clover_customers()
    save_to_json(clover_customers, f"clover_customers.json")
    check_miss_customer(all_customers, clover_customers)
    if all_customers:
        customer_details = []
        for customer in all_customers:
            customer_id = customer.get("id")
            if is_duplicate_customer(customer_id, clover_customers):
                logger.warning(f"⚠️ Duplicate Customer data : {customer_id}, So we don't push this customer")
                continue
            if customer_id:
                customer_data = get_customer_by_id(store, session_token, customer_id)
                if customer_data:
                    full_customer = customer_data.get("result")
                    customer_details.append(full_customer)
                    customer_id = create_customer(full_customer)
                    customer_ids.append(customer_id)
                    customer = get_customer_byId(customer_id)
                    save_to_json(customer, f"customer_{customer_id}.json")
        if customer_details:
            save_to_json(customer_details, "all_customer_data.json")
        else:
            logger.error("No customer details were fetched.")
    else:
        logger.error("Failed to fetch all customers.")

def fetch_allProducts(session_token):
    # get all products and push products to clover
    item_ids = []
    all_product_details = []
    all_products = get_product_codes(store, session_token)
    save_to_json(all_products, "all_product_data.json")
    cloverItems = fetch_all_clover_items()
    save_to_json(cloverItems, "cloverItems.json")

    if all_products:
        for product in all_products["productCodes"]:
            code = product.get("productCode")
            if code:
                logger.info(f"📦 Fetching products for code: {code}")
                products = get_products_by_code(store, session_token, code)
                if products:
                    all_product_details.extend(products)

        check_miss_product(all_product_details, cloverItems)
        if all_product_details:
            save_to_json(all_product_details, "all_product_details.json")
            logger.info(f"✅ Saved product data for {len(all_product_details)} items.")
            for product in all_product_details:
                if is_duplicate_product(product, cloverItems):
                    logger.warning(f"⚠️ Duplicate product data , So we don't push this product")
                    continue

                clover_item_id = create_item_with_color(product)
                item_ids.append(clover_item_id)
        else:
            logger.warning("⚠️ No product data was returned.")
    else:
        logger.warning("⚠️ Failed to fetch all products")

def Process_Orders(session_token):
        # # get all orders from clover
        all_orders = get_orders("employee,payments,refunds,credits,voids,payment.tender,payment.cardTransaction,lineItems,customers,serviceCharge,discounts,orderType,lineItems.discounts,lineItems.modifications")
        save_to_json(all_orders, "all_order_data.json")

        
        processed_orders = load_processed_orders()

        # # get exployee by id
        # if all_orders:
        #     for order in all_orders:
        #         if 'employee' in order and order['employee']:
        #             employee = get_employee_by_id(order['employee']['id'], "roles,shifts")
        #             save_to_json(employee, f"employee_{order['employee']['id']}.json")
        #         else:
        #             print("No employee data found in order.")

        all_order_details = []

        #push order to rfms include item, customer ...
        if all_orders:
            for order in all_orders:
                order_id = order.get("id")
                if order_id:
                    if order_id in processed_orders:
                        logger.info(f"⏩ Order {order_id} already processed. Skipping.")
                        continue
                    logger.info(f"📦 Fetching order details with order id: {order_id}")
                    order_detail = get_order_details(order_id)
                    if order_detail.get("customers") is not None and order_detail["customers"].get("elements"):
                        results = []
                        for line_item in order_detail["lineItems"]["elements"]:
                            item_id = line_item["item"]["id"]
                            item = get_item_by_id(item_id)
                            if item is None:
                                logger.warning(f"⚠️ Item not found for ID {item_id}, skipping.")
                                continue  # or handle gracefully
                            # Inject Clover-specific info if needed (e.g., itemCode, price)
                            item["code"] = line_item.get("itemCode", "")
                            item["price"] = line_item.get("price", 0)

                            rfms_info = extract_rfms_info(item)
                            results.append(rfms_info)
                        save_to_json(results, "order_results.json")
                        logger.info(f"📦 Fetching results : {results}")
                        customer = get_customer_byId(order_detail["customers"]["elements"][0]["id"])
                        save_to_json(customer, "order_customer.json")
                        logger.info(f"📦 Fetching customer : {customer}")
                        logger.info(f"📦 Fetching result : {results}")
                        if customer['message'] == "Not Found":
                            logger.warning(f"⚠️ No matching Customer : {customer}")
                            continue
                        if results == []:
                            logger.warning(f"⚠️ No results : {results}")
                            continue
                        rfms_order_id = push_order_to_rfms(store, session_token, order_detail, customer, results)
                        if rfms_order_id != None:
                            save_processed_order(order_id)

                        # post_payment_to_rfms(store, session_token, rfms_order_id, order_detail, results)
                        # payment = get_payments_by_order_number(store, session_token, rfms_order_id)
                        # if payment:
                        #     filename = f"payment_{rfms_order_id}.json"
                        #     save_to_json(payment, filename)

                        all_order_details.append(order_detail)
                        order_detail = get_order_by_number(store, session_token, rfms_order_id, lock_order=False)
                        if order_detail:
                            filename = f"order_{rfms_order_id}.json"
                            save_to_json(order_detail, filename)
                    
                    else:
                        # Continue if "customers" is None or empty
                        logger.info("No customers found. Continuing with other operations.")

            if all_order_details:
                save_to_json(all_order_details, "all_order_details.json")
                logger.info(f"✅ Saved order detail data for {len(all_order_details)} orders.")
            else:
                logger.warning("⚠️ No order data was returned.")

def main():
    session_token = get_session(store, api_key)
    if session_token:

        logger.info(f"✅ [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting order sync: Fetching all orders from Clover and pushing to RFMS")
        Process_Orders(session_token)

        logger.info(f"✅ [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting customer sync: Fetching all customers from RFMS and pushing to Clover")
        fetch_allCustomers(session_token)

        logger.info(f"✅ [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting product sync: Fetching all products from RFMS and pushing to Clover")
        fetch_allProducts(session_token)

    else:
        logger.error("No session token available.")

if __name__ == "__main__":
    main()