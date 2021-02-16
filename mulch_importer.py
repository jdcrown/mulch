import json
import re
import logging
import configparser
from dataclasses import dataclass
from dateutil.parser import parse
from intuitlib.client import AuthClient
from intuitlib.exceptions import AuthClientError
from quickbooks import QuickBooks
from quickbooks.objects.customer import Customer
from quickbooks.objects.item import Item
from quickbooks.objects.paymentmethod import PaymentMethod
from quickbooks.objects.salesreceipt import SalesReceipt
from quickbooks.exceptions import QuickbooksException
from quickbooks.exceptions import AuthorizationException
from prompter import prompt, yesno
from square.client import Client

sales_receipts = []

qb_client = None #client
config = configparser.ConfigParser()
config.read('settings.ini')
default = config['DEFAULT']
ENVIRONMENT = config['DEFAULT'].get('ENVIRONMENT', 'sandbox') #default to sandbox
if ENVIRONMENT == 'production':
    print("RUNNING IN PRODUCTION")
    PRODUCTION = config['production']
    CLIENT_ID = PRODUCTION.get('CLIENT_ID')
    CLIENT_SECRET = PRODUCTION.get('CLIENT_SECRET')
    COMPANY_ID = PRODUCTION.get('COMPANY_ID')
    REFRESH_TOKEN = PRODUCTION.get('REFRESH_TOKEN')
    SQUARE_BEARER_TOKEN = PRODUCTION.get('SQUARE_BEARER_TOKEN')
    SQUARE_LOCATION_ID = PRODUCTION.get('SQUARE_LOCATION_ID')
else:
    print("RUNNING IN SANDBOX")
    SANDBOX = config['sandbox']
    CLIENT_ID = SANDBOX.get('CLIENT_ID')
    CLIENT_SECRET = SANDBOX.get('CLIENT_SECRET')
    COMPANY_ID = SANDBOX.get('COMPANY_ID')
    REFRESH_TOKEN = SANDBOX.get('REFRESH_TOKEN')
    SQUARE_BEARER_TOKEN = SANDBOX.get('SQUARE_BEARER_TOKEN')
    SQUARE_LOCATION_ID = SANDBOX.get('SQUARE_LOCATION_ID')

DEFAULT_DONATION_PRODUCT = default.get('DefaultDonationProduct', 'Donation - T581')
AUTO_CREATE_CUSTOMERS = default.getboolean('AutoCreateCustomers')
BLACK_KEYS = default.get('black_keys', 'black')
BROWN_KEYS = default.get('brown_keys', 'brown|hardwood')
RED_KEYS = default.get('red_keys', 'red')
SPREAD_KEYS = default.get('spreading_keys', 'spread|spreading')
DONATION_KEYS = default.get('donation_keys', 'donate|donation')
SEARCH_KEYS = "|".join([BROWN_KEYS, RED_KEYS, SPREAD_KEYS, DONATION_KEYS, BLACK_KEYS])

logging_level = default.get('Logging', 'INFO')
if logging_level == 'DEBUG':
    logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)
else:
    logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)

#QB_BEARER_TOKEN = None #os.environ.get('BEARER_TOKEN')

PROCESSING_START_DATETIME = config['DEFAULT']['start_date']
PROCESSING_END_DATETIME = config['DEFAULT']['end_date']


SQUARE_HOST = "https://connect.squareup.com"

#These are regular expressions used to find matches in the square description so that we can get the description correct for quickbooks
# spread_pattern = re.compile('spreading|spread')
# donation_pattern = re.compile('donate|donation')
# brown_pattern = re.compile('brown|hardwood')
# black_pattern = re.compile('black')
# red_pattern = re.compile('red')

def authenticate_to_quickbooks():
    print("authorizing to Quickbooks...")
    auth_client = AuthClient(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        environment=ENVIRONMENT,
        redirect_uri='https://developer.intuit.com/v2/OAuth2Playground/RedirectUrl',
    )
    #url = auth_client.get_authorization_url(scopes=[Scopes.ACCOUNTING])

    print("finished authorizing to Quickbooks...")
    try:
        client = QuickBooks(
            auth_client=auth_client,
            refresh_token=REFRESH_TOKEN,
            company_id=COMPANY_ID,
        )
        print('finished connecting to Quickbooks...')
        return client
    except AuthClientError as e:
        logging.error("Cannot connect to quickbooks: Error [{}]".format(e.content))


#def update_customer_info(sr):
    #This updates the quickbooks customer. It will check to see if the address, phone or email has changes
    #and if it has, then it prompts to update the customer record for address, but automatically moves the

def square_money_to_decimal(price):
    return "{}.{}".format(str(price)[0:-2], str(price)[-2:])

def create_customer(sr):
    # Get the customer

    customer = Customer()
    customer_body = {
          "GivenName": sr.customer_first,
          "FamilyName": sr.customer_last,
          "FullyQualifiedName": sr.customer_name,
          "PrimaryEmailAddr": {
            "Address": sr.customer_email
          },
          "DisplayName": sr.customer_name,
          #"Suffix": "Jr",
          #"Title": "Mr",
          #"MiddleName": "B",
          "Notes": sr.memo,
          "PrimaryPhone": {
            "FreeFormNumber": sr.customer_phone
          },
          #"CompanyName": "King Groceries",
          "BillAddr": {
            "CountrySubDivisionCode": sr.customer_state,
            "City": sr.customer_city,
            "PostalCode": sr.customer_zip,
            "Line1": sr.customer_street,
            "Country": "USA"
          },
          "ShipAddr": {
            "CountrySubDivisionCode": sr.customer_state,
            "City": sr.customer_city,
            "PostalCode": sr.customer_zip,
            "Line1": sr.customer_street,
            "Country": "USA"
          }
        }
    customer = customer.from_json(customer_body)

    #revise customer here

    logging.debug("Customer Body Sent: {}".format(customer_body))
    try:
        customer.save(qb_client)
        logging.debug("New Customer Info: {}".format(customer.to_json()))
        return customer
    except QuickbooksException as e:
        logging.error("Errot saving new customer. [{}]".format(e.detail))
        return None

def lookup_payment_method(payment_name):
    #Get the payment method (square)

    payment_count = PaymentMethod.count("Active = true and Name = '" + payment_name + "'", qb=qb_client)
    if payment_count == 1:
        payments = PaymentMethod.where("Active = true and Name = '" + payment_name + "'", qb=qb_client)
        return payments[0].Id
    else:
        logging.error("Please add the 'Sqaure' payment method to quickbooks before running this tool.")
        exit(0)

def lookup_product(product_name):
    #Get the Item
    #items = Item.all(qb=qb_client)
    item_count = Item.count("Name = '" + product_name + "'", qb=qb_client)
    if item_count == 1:
        items = Item.where("Name = '" + product_name + "'", qb=qb_client)
        return items[0].Id
    else:
        logging.error("Product name: [{}] not found. Please add this product to quickbook before this record can be added".format(product_name))

def create_order(sr):
    #Get the sales receipt

    sales_receipt = SalesReceipt()
    sr_body = {
          "domain": "QBO",
          "Balance": 0,
          "CustomerRef": {
            "name": "",
            "value": "6"
          },
          "CustomerMemo": {
            "value": ""
          },
          "sparse": "false",
          "Line": [
            {
              #"Description": "Custom Design",
              "DetailType": "SalesItemLineDetail",  #required
              "SalesItemLineDetail": {
                "Qty": 1,
                #"UnitPrice": 75,
                "ItemRef": {    #required
                  "value": "44" #black mulch (1-9)
                }
              },
              "LineNum": 1,
              "Amount": 0,
            }
          ],
          "CustomField": [
              {
                  "DefinitionId": "1",
                  "Name": "Scout Credit",
                  "Type": "StringType",
                  "StringValue": ""
              }
          ],
          "PaymentMethodRef": {
              "value": lookup_payment_method('square')
          },
          "CustomerMemo": {
              "value": sr.memo
          },
    }

    customers_count = Customer.count("Active=true and DisplayName LIKE '%" + sr.customer_last + "'", qb=qb_client)

    if customers_count == 0:
        # create a new customer?
        if AUTO_CREATE_CUSTOMERS:
            answer = yesno("Customer [{}] not found. Create the customer?".format(sr.customer_name))
            if answer:
                logging.warning("Creating the customer [{}] in quickbooks.".format(sr.customer_name))
                customer = create_customer(sr)
                if customer is not None:
                    customers_count = 1
        else:
            logging.warning("Customer [{}] not found. Not creating customer due to settings.".format(sr.customer_name))

    if customers_count == 1:
        #we have found a customer
        customers = Customer.where("Active=true and DisplayName LIKE '%" + sr.customer_last + "'", qb=qb_client)
        customer_id = customers[0].Id
        customer_name = customers[0].DisplayName
        logging.debug("Customer id: {}".format(customer_id))

       # update_customer_info(sr)

        sr_body['CustomerRef']['value'] = customer_id
        sr_body['CustomerRef']['name'] = customer_name
        sr_body['Line'][0]['Amount'] = sr.total_price
        product_id = lookup_product(sr.product_name)
        sr_body['Line'][0]['SalesItemLineDetail']['ItemRef']['value'] = product_id
        sr_body['Line'][0]['SalesItemLineDetail']['Qty'] = sr.product_qty
        sr_body['Line'][0]['SalesItemLineDetail']['UnitPrice'] = sr.product_price
        logging.debug("Revised Customer: {}".format(sr_body))
        #print("SR Body: {}".format(sr_body))

        #post a new one
        sales_receipt = sales_receipt.from_json(sr_body)

        sales_receipt.TxnDate = sr.date

        #check for duplicates
        #get all customer sales receipts
        duplicate = False
        srs = SalesReceipt.filter(CustomerRef = customer_id, qb=qb_client)
        for asr in srs:
            #print(asr.Line[0].SalesItemLineDetail['ItemRef']['name'])
            if asr.Line[0].SalesItemLineDetail['ItemRef']['name'] == sr.product_name \
                and asr.Line[0].SalesItemLineDetail['Qty'] == sr.product_qty \
                and float(asr.TotalAmt) == float(sr.total_price):
                logging.warning("found a duplicate for this customer: {} on {} for item: {}, qty: {}, total: {}. skipping...".format(sr.customer_name,sr.date,sr.product_name, sr.product_qty, sr.total_price))
                duplicate = True
        #add the item
        if not duplicate:
            try:
                sales_receipt.save(qb_client)
                logging.debug("SentBody: {}".format(json.dumps(sr_body)))
                logging.info("Successful entry of SalesReceipt: [{}] into quickbooks. OrderId:[{}], Item:[{}], Qty:[{}], Total:[{}]".format(sr.customer_last,sales_receipt.Id,sr.product_name,sr.product_qty,sr.total_price))
            except QuickbooksException as e:
                logging.error("An error saving the sales_receipt: {}".format(e.detail))
    elif customers_count > 1:
        logging.warning("More than one customer matches name: [{}]. Cannot process record. Skipping.".format(sr.customer_last))
    else:
        print("no customer found")


def extract_item(sr,quantity,item_name,variation):
    #calcuate quantities smarter
    #tier1
    if quantity > 0 and quantity <= 9:
        tier = " (1-9)"
    elif quantity >= 10 and quantity <= 24:
        tier = " (10-24)"
    elif quantity >= 25 and quantity <= 44:
        tier = " (25-44)"
    elif quantity > 44:
        tier = " (45+)"
    else:
        tier = ""
    sr.product_qty = quantity
    #color



    if re.findall(BLACK_KEYS,item_name.lower()):
        sr.product_name = "Black Mulch" + tier
    elif re.findall(BROWN_KEYS,item_name.lower()):
        sr.product_name = "Brown Mulch" + tier
    elif re.findall(RED_KEYS,item_name.lower()):
        sr.product_name = "Red Mulch" + tier
    elif re.findall(SPREAD_KEYS,item_name.lower()):
        if 'March 20' in variation:
            sr.product_name = "Spreading 3-20"
        elif 'March 21' in variation:
            sr.product_name = "Spreading 3-21"
        elif 'March 27' in variation:
            sr.product_name = "Spreading 3-27"
        elif 'March 28' in variation:
            sr.product_name = "Spreading 3-28"
        elif 'April 10' in variation:
            sr.product_name = "Spreading 4-10"
        elif 'April 11' in variation:
            sr.product_name = "Spreading 4-11"
        else:
            #Peg it to the middle of the week so we have more time to work on the spreading for the else orders
            sr.product_name = "Spreading 3-27"
        sr.product_qty = quantity
    elif re.findall(DONATION_KEYS,item_name.lower()):
        sr.product_name = DEFAULT_DONATION_PRODUCT
    return sr

@dataclass
class MulchSalesReceipt:
    date: str = None
    customer_name: str = None
    customer_first: str = None
    customer_last: str = None
    customer_street: str = None
    customer_city: str = None
    customer_state: str = None
    customer_zip: str = None
    customer_email = None
    customer_phone = None
    payment_type: str = "Square"
    product_name: str = None
    product_qty: int = None
    product_sku: str = None
    memo: str = None
    product_price = None
    total_price: float = None

def main():
    try:
        client = Client(
            square_version='2021-01-21',
            access_token=SQUARE_BEARER_TOKEN,
            environment='production', )
    except Exception as e:
        logging.error("Cannot connect to square : {}".format(e.message))

    body = {}
    body['location_ids'] = [SQUARE_LOCATION_ID]    # Just using one
    body['limit'] = 200
    body['query'] = {}
    body['query']['filter'] = {}
    body['query']['filter']['state_filter'] = {}
    body['query']['filter']['state_filter']['states'] = ['OPEN']
    body['query']['filter']['date_time_filter'] = {}
    body['query']['filter']['date_time_filter']['created_at'] = {}
    body['query']['filter']['date_time_filter']['created_at']['start_at'] = PROCESSING_START_DATETIME
    body['query']['filter']['date_time_filter']['created_at']['end_at'] = PROCESSING_END_DATETIME
    body['query']['filter']['fulfillment_filter'] = {}
    body['query']['filter']['fulfillment_filter']['fulfillment_types'] = ['SHIPMENT']
    body['query']['filter']['fulfillment_filter']['fulfillment_states'] = ['PROPOSED']
    body['return_entries'] = True
    body['query']['sort'] = {}
    body['query']['sort']['sort_field'] = 'CREATED_AT'
    body['query']['sort']['sort_order'] = 'ASC'
    body['query']['filter']['customer_filter'] = {}
    orders_api = client.orders
    orders_raw = orders_api.search_orders(body)

    if orders_raw.is_success():
        print(orders_raw.body)
    elif orders_raw.is_error():
        print(orders_raw.errors)

    all_orders = orders_raw.body.get('order_entries')
    if all_orders: print("Found [{}] orders in square to process.".format(len(all_orders)))
    for order_cursor in all_orders:
        order = orders_api.retrieve_order(order_cursor['order_id']).body['order']
        created_on = parse(order.get('created_at')).date()

        #check only from a certain time forward
        if created_on >= parse(PROCESSING_START_DATETIME).date() and created_on < parse(PROCESSING_END_DATETIME).date():
        #if order.get('id') == 'Hv5nLw567WQcPMvyEFRvbttF7BeZY': #me
        #if order.get('id') == 'vtwmcNbBlJCJ15WXoPQIuQVzYucZY': #sissy
        #if order.get('id') == '9q78JCThpddGoaPBemt3ukD33DIZY': #unregistered user
        #if order.get('id') == 'vJOMD95Etuokh4F2nKfO19mtFOUZY': #unregistered user

            logging.info("Processing Order: {}".format(order))

            if 'line_items' in order:
                for item in order['line_items']:
                    sr = MulchSalesReceipt()
                    logging.debug("Processing Line Item: {}".format(item))
                    if 'name' in item:
                        #print(item0)
                        if re.findall(SEARCH_KEYS, item['name'].lower()):
                            process_order = True
                            logging.debug("Processing Line Item: {}".format(item))
                            item_name = item['name'].lower()
                            item_quantity = int(item['quantity'])
                            item_variation = item['variation_name']
                            # get customer for order if we have a customer id
                            if bool(order.get('customer_id', None)):
                                logging.info(
                                    "Processing Square customer id: [{}], order id:[{}], details: [Item:{}, variation:{}, quantity:{}]".format(order['customer_id'],
                                                                                                order['id'], item_name, item_variation, item_quantity))
                                customer_id = order['customer_id']
                                payment_id = order['tenders'][0]['id']
                                try:
                                    payments_api = client.payments
                                    payment_raw = payments_api.get_payment(payment_id)
                                    if payment_raw.is_success():
                                        payment = payment_raw.body['payment']
                                        logging.debug("Payment Raw: {}".format(payment))
                                        sr.customer_street = payment['shipping_address']['address_line_1']
                                        sr.customer_state = payment['shipping_address']['administrative_district_level_1']
                                        sr.customer_city = payment['shipping_address']['locality']
                                        sr.customer_zip = payment['shipping_address']['postal_code']
                                        sr.customer_email = payment['buyer_email_address']
                                    else:
                                        logging.error(
                                            "Cannot find square payment for payment_id: [{}]".format(payment_id))
                                        process_order = False
                                except Exception as e:
                                    logging.error("Error finding square payment for payment_id: [{}], msg:[{}]".format(payment_id, e.message))
                                    process_order = False
                                try:
                                    customers_api = client.customers
                                    customer_raw = customers_api.retrieve_customer(customer_id)
                                    if customer_raw.is_success():
                                        customer = customer_raw.body['customer']
                                        logging.debug("Customer Response: {}".format(customer))
                                        sr.customer_first = format(customer['given_name'])
                                        sr.customer_last = customer['family_name']
                                        sr.customer_name = "{} {}".format(customer['given_name'], customer['family_name'])
                                        sr.customer_phone = customer.get('phone_number', None)
                                    else:
                                        logging.error("Cannot process square customer id: [{}]".format(customer_id))
                                        process_order = False
                                except Exception as e:
                                    logging.error("Error processing square customer id: [{}], msg: {}".format(customer_id, e.message))
                                    process_order = False
                                if order['fulfillments'][0].get('shipment_details') and order['fulfillments'][0]['shipment_details'].get('shipping_note'):
                                    sr.memo = order['fulfillments'][0]['shipment_details']['shipping_note']

                            else:  # otherwise get the customer from the order itself (customer not registered)
                                logging.info(
                                    "Processing Square (non-registered customer): order id:[{}], createdOn: [{}]".format(order['id'], order['created_at']))

                                logging.debug("getting from fulfillments")
                                sr.customer_name = order['fulfillments'][0]['shipment_details']['recipient']['display_name']
                                sr.customer_last = sr.customer_name.split(' ')[-1]
                                sr.customer_first = sr.customer_name.split(' ')[0]
                                sr.customer_street = order['fulfillments'][0]['shipment_details']['recipient']['address'][
                                    'address_line_1']
                                sr.customer_city = order['fulfillments'][0]['shipment_details']['recipient']['address'][
                                    'locality']
                                sr.customer_state = order['fulfillments'][0]['shipment_details']['recipient']['address'][
                                    'administrative_district_level_1']
                                sr.customer_zip = order['fulfillments'][0]['shipment_details']['recipient']['address'][
                                    'postal_code']
                                sr.customer_email = order['fulfillments'][0]['shipment_details']['recipient']['email_address']
                                sr.customer_phone = order['fulfillments'][0]['shipment_details']['recipient']['phone_number']
                                sr.memo = order['fulfillments'][0]['shipment_details']['shipping_note']


                            #print("matched: {}".format(item0))
                            # item_name = item['name'].lower()
                            # item_quantity = int(item['quantity'])
                            # item_variation = item['variation_name']

                            #now we have a clean line item for mulch. Build the object out for importing into quickbooks
                            if process_order:
                                sr = extract_item(sr, item_quantity, item_name, item_variation)
                                sr.date = order['created_at']
                                sr.product_price = square_money_to_decimal(item['base_price_money']['amount'])
                                sr.total_price = square_money_to_decimal(item['total_money']['amount'])
                                create_order(sr)
                                logging.debug(sr)
                            else:
                                logging.error("Cannot process Order for orderid [{}]. Either the customer or the payment cannot be found in square...skipping".format(order['id']))

qb_client = authenticate_to_quickbooks()
if qb_client:
    main()
else:
    print("Cannot connect to quickbooks. Check your keys and tokens")