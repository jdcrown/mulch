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
TROOP_KEYS = 't581|t91|t582|c91'
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

def load_subdivision_data():
    subdivision_data = {}
    with open('county_lookup_data_2021.csv', mode='r') as csv_file:
        csv_reader = csv.DictReader(csv_file)
        line_count = 0
        for row in csv_reader:
            if line_count == 0:
                line_count += 1
            line_count += 1
            subdivision_data[row['ST_NO'] + " " + row['ST_NAME']] = row['SUBDIV_NAME']
            subdivision_data.update()
        print(f'Processed {line_count} county data lines.')
    return subdivision_data

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
        srs = SalesReceipt.where(qry, qb=qb_client, max_results=1000)
        logging.info("Found {} records to process.".format(len(srs)))
        return srs
    except ValidationException as ve:
        logging.error("Cannot process SalesReceipt query: Error: {}".format(ve.detail))



@dataclass
class MulchSalesReport:
    date: str = None
    date_modified: str = None
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
    subdivision: str = None

    customer_email = None
    customer_phone = None
    sr_record_id: str = None
    sr_product_name: str = None
    sr_product_color: str = None
    sr_product_qty: int = 0
    sr_product_sku: str = None
    sr_product_memo: str = None
    sr_product_price = None
    sr_total_price: float = None
    sr_check_no: str = None
    sr_bags_qty: int = None

    brown_qty: int = 0
    red_qty: int = 0
    black_qty: int = 0

    spread_date: str = None
    spread_sale_no: str = None
    spread_check_no: str = None
    spread_qty: int = None
    spread_total: float = None
    spread_notes: str = None

    donate_total: str = None

    payment_method_ref: object = None
    deposit_account_ref: object = None
    unit_income: str = None
    unit_sale: str = None
    scout_sale: str = None
    unit_sale: str = None

    def to_dict(self, index):
        return {
            'Sale #': self.sr_record_id,
            'Date': self.date,
            'Income\nUnit': self.unit_income,
            'Sales Unit': self.unit_sale,
            'ScoutName': self.scout_sale,
            'CustomerName': self.customer_name,
            'Email Address': self.customer_email,
            'Telephone': self.customer_phone,
            'Billing Address': self.billing_street,
            'Delivery Address': self.customer_street,
            'CITY': self.customer_city,
            'ZIP': self.customer_zip,
            'Subdivision': self.subdivision,
            'Status': '',
            'run': '',
            'seq': '',
            'shares': '',
            'bags': self.sr_bags_qty, #"=Q{}+R{}+S{}".format(index, index, index),
            'color': self.sr_product_color,
            'Brown': self.brown_qty,
            'Black': self.black_qty,
            'Red': self.red_qty,
            'Delivery Notes': self.sr_product_memo,
            'reprint letter': '',
            'Mulch\nRevenue': '',
            'Total Paid thru Troops': self.sr_total_price,
            'Check No or Payment Type': self.sr_check_no,
            'Paypal\nM Square': '',
            'Paypal\nS Square': '',
            'Spread Sale #': self.spread_sale_no,
            'Spread\nCheck#': self.spread_check_no,
            'Spread\ncount': self.spread_qty,
            'Spread\nNotes': self.spread_notes,
            'Spread date': self.spread_date,
            'Unit\nPaid': self.unit_income,
            'Spread\nSales': self.spread_total,
            'Overpayments\nand donations':'',
            'unpaid\nshortage':'',
            'DONATION':'',
            'Mulch\n45+':'',
            'Mulch\n25-44':'',
            'Mulch\n20-24':'',
            'Mulch\n1-9':'',
            'Total Sales': '',
            'DateModified': self.date_modified
        }

def get_col_widths(dataframe):
    # First we find the maximum length of the index column
    idx_max = max([len(str(s)) for s in dataframe.index.values] + [len(str(dataframe.index.name))])
    # Then, we concatenate this to the max of the lengths of column name and its values for each column, left to right
    return [idx_max] + [max([len(str(s)) for s in dataframe[col].values] + [len(col)]) for col in dataframe.columns]



def save_to_excel(list_of_rows):
    x = [vars(s) for s in list_of_rows]

    df = pandas.DataFrame([s.to_dict(index+2) for index, s in enumerate(list_of_rows)])

    # # Create a Pandas Excel writer using XlsxWriter as the engine.
    writer = pandas.ExcelWriter('mulch_master.xlsx', engine='xlsxwriter')

    #get access to the workbook for styling
    workbook = writer.book

    #
    # # Convert the dataframe to an XlsxWriter Excel object.
    df.to_excel(writer, sheet_name='Sheet1', index=False)
    #
    # # Close the Pandas Excel writer and output the Excel file.

    blue_background = workbook.add_format({'bg_color': '#8DB3E2', 'font_color': 'black'})

    #Now style the columns
    worksheet = writer.sheets['Sheet1']
    worksheet.set_column('O:O', None, blue_background)

    #column width
    for i, width in enumerate(get_col_widths(df)):
        worksheet.set_column(i-1, i-1, width)

    #turn on filtering
    worksheet.autofilter(0, 0, df.shape[0], df.shape[1])


    writer.save()


def process_data():
    rows = []
    subdivision_data = load_subdivision_data()

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
                    raw_street_lookup = sr.customer_street.split(' ')[0:-1]
                    street_lookup = ' '.join(raw_street_lookup).strip().upper()
                    sr.subdivision = subdivision_data.get(street_lookup)

                if c.BillAddr is not None:
                    sr.billing_street = c.BillAddr.Line1
                    sr.billing_city = c.BillAddr.City
                    sr.billing_state = c.BillAddr.CountrySubDivisionCode
                    sr.billing_zip = c.BillAddr.PostalCode

                sr.customer_phone = c.PrimaryPhone
                sr.customer_email = c.PrimaryEmailAddr


                #sales receipt
                sr.date = receipt.TxnDate
                sr.sr_record_id = receipt.DocNumber
                sr.date_modified = receipt.MetaData['LastUpdatedTime']
                sr.sr_total_price = float(r.Amount)
                scout_credit = receipt.CustomField[0]
                if scout_credit.StringValue != '':

                    credit = scout_credit.StringValue.split(':')
                    if len(credit) > 1:
                        sr.unit_sale = credit[0].upper()
                        sr.scout_sale = credit[1].strip()
                    elif len(credit) == 1:
                        if re.findall(TROOP_KEYS, credit[0].lower()):
                            sr.unit_sale = credit[0].upper()
                        else:
                            sr.scout_sale = credit[0].strip()
                    else:
                        sr.scout_sale = scout_credit.StringValue.strip()

                if receipt.CustomerMemo is not None:
                    sr.sr_product_memo = receipt.CustomerMemo['value']
                deposit_account = receipt.DepositToAccountRef
                if deposit_account is not None:
                    sr.unit_income = deposit_account.name
                sr.sr_check_no = receipt.PaymentRefNum
                #sales receipt line item
                qty = r.SalesItemLineDetail['Qty']
                #sr.sr_product_qty = qty
                item = Item.get(r.SalesItemLineDetail['ItemRef']['value'], qb=qb_client)
                sr.sr_product_sku = item.Sku
                sr.sr_product_name = item.Name
                sr.sr_product_price = r.SalesItemLineDetail['UnitPrice']

                #color
                item_name = sr.sr_product_name.lower()
                if re.findall(BROWN_KEYS, item_name):
                    sr.brown_qty = qty
                    sr.sr_product_color = 'Brown'
                elif re.findall(RED_KEYS,item_name):
                    sr.red_qty = qty
                    sr.sr_product_color = 'Red'
                elif re.findall(BLACK_KEYS,item_name):
                    sr.black_qty = qty
                    sr.sr_product_color = 'Black'
                elif re.findall(SPREAD_KEYS,item_name):
                    sr.spread_qty = qty
                    sr.spread_check_no = sr.sr_check_no
                    sr.spread_sale_no = receipt.DocNumber
                    sr.spread_total = sr.sr_total_price
                    sr.spread_date = item.Name
                    if receipt.CustomerMemo is not None:
                        sr.sr_product_memo = receipt.CustomerMemo['value']
                elif re.findall(DONATION_KEYS,item_name):
                    sr.donate_total = sr.sr_total_price
                    sr.sr_product_memo = ''

                sr.sr_bags_qty = sr.black_qty + sr.brown_qty + sr.red_qty



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