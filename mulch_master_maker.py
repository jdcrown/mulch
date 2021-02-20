import json
import csv
import re
import logging
import configparser
import pandas
from dataclasses import dataclass
from dataclasses import make_dataclass
from dateutil.parser import parse
from intuitlib.client import AuthClient
from intuitlib.exceptions import AuthClientError
from quickbooks import QuickBooks
from quickbooks.objects.base import PhoneNumber
from quickbooks.objects.base import Address
from quickbooks.objects.base import Ref
from quickbooks.objects.customer import Customer
from quickbooks.objects.account import Account
from quickbooks.objects.base import EmailAddress
from quickbooks.objects.detailline import DetailLine
from quickbooks.objects.item import Item
from quickbooks.objects.paymentmethod import PaymentMethod
from quickbooks.objects.salesreceipt import SalesReceipt
from quickbooks.exceptions import QuickbooksException
from quickbooks.exceptions import ValidationException
from prompter import prompt, yesno
import phonenumbers

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

else:
    print("RUNNING IN SANDBOX")
    SANDBOX = config['sandbox']
    CLIENT_ID = SANDBOX.get('CLIENT_ID')
    CLIENT_SECRET = SANDBOX.get('CLIENT_SECRET')
    COMPANY_ID = SANDBOX.get('COMPANY_ID')
    REFRESH_TOKEN = SANDBOX.get('REFRESH_TOKEN')

#AUTO_CREATE_CUSTOMERS = default.getboolean('AutoCreateCustomers')
BLACK_KEYS = default.get('black_keys', 'black')
BROWN_KEYS = default.get('brown_keys', 'brown|hardwood')
RED_KEYS = default.get('red_keys', 'red')
SPREAD_KEYS = default.get('spreading_keys', 'spread|spreading')
DONATION_KEYS = default.get('donation_keys', 'donate|donation')
SEARCH_KEYS = "|".join([BROWN_KEYS, RED_KEYS, SPREAD_KEYS, DONATION_KEYS, BLACK_KEYS])

rows = []

logging_level = default.get('Logging', 'INFO')
if logging_level == 'DEBUG':
    logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)
else:
    logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)

PROCESSING_START_DATETIME = config['DEFAULT']['start_date']
PROCESSING_END_DATETIME = config['DEFAULT']['end_date']

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


def lookup_deposit_account(account_name):
    try:
        default_deposit_account_result = Account.where("Active = True AND Name = '" + DEFAULT_DEPOSIT_ACCOUNT + "'", qb=qb_client)
        if default_deposit_account_result is not None:
            return default_deposit_account_result[0].Id
    except Exception as e:
        logging.error("Error assigning default account info [{}], Error:{}".format(DEFAULT_DEPOSIT_ACCOUNT, e.message))

def lookup_payment_method(payment_name):
    #Get the payment method (square)
    try:
        payment_count = PaymentMethod.count("Active = true and Name = '" + payment_name + "'", qb=qb_client)
        if payment_count == 1:
            payments = PaymentMethod.where("Active = true and Name = '" + payment_name + "'", qb=qb_client)
            return payments[0].Id
        else:
            logging.error("Please add the {} payment method to quickbooks before running this tool.".format(payment_name))
            exit(0)
    except Exception as e:
        logging.error("Error assigning default payment info [{}], Error:{}".format(payment_name, e.message))
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

def get_sales_receipts(start_date, end_date):
    qry = r"TxnDate >= '{}' AND TxnDate <= '{}'".format(str(parse(start_date).date()), str(parse(end_date).date()))
    try:
        srs = SalesReceipt.where(qry, qb=qb_client)
        logging.info("Found {} records to process.".format(len(srs)))
        return srs
    except ValidationException as ve:
        logging.error("Cannot process SalesReceipt query: Error: {}".format(ve.detail))



@dataclass
class MulchSalesReport:
    date: str = None
    customer_name: str = None
    customer_first: str = None
    customer_last: str = None
    customer_street: str = None
    customer_city: str = None
    customer_state: str = None
    customer_zip: str = None
    billing_street: str = None
    billing_city: str = None
    billing_state: str = None
    billing_zip: str = None

    customer_email = None
    customer_phone = None
    sr_record_id: str = None
    sr_product_name: str = None
    sr_product_qty: int = 0
    sr_product_sku: str = None
    sr_product_memo: str = None
    sr_product_price = None
    sr_total_price: float = None

    brown_qty: int = 0
    red_qty: int = 0
    black_qty: int = 0

    spread_date: str = None
    spread_qty: int = 0
    spread_notes: str = None

    donate_total: str = None

    payment_method_ref: object = None
    deposit_account_ref: object = None
    unit_income: str = None
    unit_sale: str = None
    scout_sale: str = None
    unit_sale: str = None

def save_to_excel(list_of_rows):

    df = pandas.DataFrame([vars(s) for s in list_of_rows])
    cols = "date, customer_name222, customer_first, customer_last, customer_street, customer_city, customer_state, customer_zip, billing_street, billing_city, billing_state, billing_zip, sr_record_id, sr_product_name, sr_product_qty, sr_product_sku, sr_product_memo, sr_total_price, brown_qty, red_qty, black_qty, spread_date, spread_qty, spread_notes, donate_total, payment_method_ref, deposit_account_ref, unit_income, unit_sale, scout_sale, customer_phone, customer_email, sr_product_price"
    y = list(csv.reader(cols.splitlines()))

    df.columns = y[0]
    #df = pandas.DataFrame(list_of_rows, columns=['a','b','c','d','e','f','g','h','i'])
    print(df)
    # Create a Pandas dataframe from the data.
    # df = pd.DataFrame({'Data': [10, 20, 30, 20, 15, 30, 45]})
    #
    # # Create a Pandas Excel writer using XlsxWriter as the engine.
    writer = pandas.ExcelWriter('mulch_master.xlsx', engine='xlsxwriter')
    #
    # # Convert the dataframe to an XlsxWriter Excel object.
    df.to_excel(writer, sheet_name='Sheet1', index=False)
    #
    # # Close the Pandas Excel writer and output the Excel file.
    writer.save()


def process_data():
    rows = []
    sales_receipts = get_sales_receipts(PROCESSING_START_DATETIME, PROCESSING_END_DATETIME)
    for receipt in sales_receipts:

        for r in receipt.Line:
            if r.Id is not None:
                sr = MulchSalesReport()

                #customer
                c = Customer.get(receipt.CustomerRef.value, qb=qb_client)
                sr.customer_name = c.DisplayName
                sr.customer_first = c.GivenName
                sr.customer_last = c.FamilyName

                if c.ShipAddr is not None:
                    sr.customer_street = c.ShipAddr.Line1
                    sr.customer_city = c.ShipAddr.City
                    sr.customer_state = c.ShipAddr.CountrySubDivisionCode
                    sr.customer_zip = c.ShipAddr.PostalCode

                if c.BillAddr is not None:
                    sr.billing_street = c.BillAddr.Line1
                    sr.billing_city = c.BillAddr.City
                    sr.billing_state = c.BillAddr.CountrySubDivisionCode
                    sr.billing_zip = c.BillAddr.PostalCode

                sr.customer_phone = c.PrimaryPhone
                sr.customer_email = c.PrimaryEmailAddr

                #sales receipt
                sr.date = receipt.TxnDate
                sr.sr_record_id = receipt.Id
                scout_credit = receipt.CustomField[0]
                if scout_credit.StringValue != '':
                    sr.scout_sale = scout_credit.StringValue
                if receipt.CustomerMemo is not None:
                    sr.sr_product_memo = receipt.CustomerMemo['value']
                deposit_account = receipt.DepositToAccountRef
                if deposit_account is not None:
                    sr.unit_income = deposit_account.name

                #sales receipt line item
                qty = r.SalesItemLineDetail['Qty']
                sr.sr_product_qty = qty
                item = Item.get(r.SalesItemLineDetail['ItemRef']['value'], qb=qb_client)
                sr.sr_product_sku = item.Sku
                sr.sr_product_name = item.Name
                sr.sr_product_price = r.SalesItemLineDetail['UnitPrice']
                #color
                item_name = sr.sr_product_name.lower()
                if re.findall(BROWN_KEYS, item_name):
                    sr.brown_qty = qty
                elif re.findall(RED_KEYS,item_name):
                    sr.red_qty = qty
                elif re.findall(BLACK_KEYS,item_name):
                    sr.black_qty = qty
                elif re.findall(SPREAD_KEYS,item_name):
                    sr.spread_qty = qty
                    if receipt.CustomerMemo is not None:
                        sr.sr_product_memo = receipt.CustomerMemo['value']
                elif re.findall(DONATION_KEYS,item_name):
                    sr.donate_total = sr.sr_total_price



                #Reports
                #result = qb_client.get_report('TransactionListByTagType')
                #print(result)

        print('.', end='')
        rows.append(sr)
    return rows

def main():
    #Setup some quickbooks defaults
    default_pament_method_ref = lookup_payment_method('Square')
    rows = process_data()
    save_to_excel(rows)


qb_client = authenticate_to_quickbooks()
if qb_client:
    main()
else:
    print("Cannot connect to quickbooks. Check your keys and tokens")