from intuitlib.client import AuthClient
from quickbooks import QuickBooks
from quickbooks.objects.customer import Customer
from datetime import time
import csv
from quickbooks.objects.salesreceipt import SalesReceipt
from quickbooks.objects.invoice import Invoice
import inspect

from intuitlib.enums import Scopes

#[sandbox]
CLIENT_ID= <clientid>       #more comments
CLIENT_SECRET = <secret>
COMPANY_ID='123146273978409'
REFRESH_TOKEN=
SQUARE_BEARER_TOKEN=<token>

#[production]
CLIENT_ID= <clientid>
CLIENT_SECRET = <secret>
COMPANY_ID='193514844769229'
REFRESH_TOKEN=<token>
SQUARE_BEARER_TOKEN=<token>


print("authorizing...")
auth_client = AuthClient(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        environment='sandbox',
        redirect_uri='http://localhost:5000/callback',
    )
url = auth_client.get_authorization_url(scopes=[Scopes.ACCOUNTING])
print("finished authorizing...")

print('running api call...' + url)

client = QuickBooks(
         auth_client=auth_client,
         refresh_token=REFRESH_TOKEN,
         company_id=COMPANY_ID,
     )
print('finished connecting')

last_year_sales = SalesReceipt.query(f"SELECT * FROM salesreceipt where TxnDate > '2018-12-01' and TxnDate < '2019-06-01' MAXRESULTS 1000", qb=client)
last_years_customer_sales = {}

#print(f"Scout, Customer, Phone, Email")
for sale in last_year_sales:
    #print(f"LastCustomerName: {sale.CustomerRef.name}, LastCustomerID:{sale.CustomerRef.value}")
    last_years_customer_sales.update({sale.CustomerRef.value: sale.ClassRef})

# Now get this year sales

this_year_sales = SalesReceipt.query(f"SELECT * FROM salesreceipt where TxnDate > '2019-12-01' and TxnDate < '2020-06-01' MAXRESULTS 1000", qb=client)
#cnt = 0
this_years_customer_sales = {}

for sale in this_year_sales:
    #cnt += 1
    #print(f"CustomerName: {sale.CustomerRef.name}, CustomerID:{sale.CustomerRef.value}, Scout: {sale.CustomField[0].StringValue}")
    this_years_customer_sales.update({sale.CustomerRef.value: sale.CustomField[0].StringValue})

this_years_customer_invoices = {}
#this years invoices (from square)
this_year_invoices = Invoice.query(f"SELECT * FROM Invoice where TxnDate > '2019-12-01' and TxnDate < '2020-06-01' MAXRESULTS 1000", qb=client)

for invoice in this_year_invoices:
    print(f"InvoiceCustomerName: {invoice.CustomerRef.name}, InvoiceCustomerID:{invoice.CustomerRef.value}, InvoiceScout: {invoice.CustomField[0].StringValue}")
    this_years_customer_invoices.update({invoice.CustomerRef.value: invoice.CustomField[0].StringValue})

#now find the difference
#list(set(temp1) - set(temp2))

# #print out last year, then this year
# for last_key, last_value in last_years_customer_sales.items():
#     print(f"last_key:{last_key}, last value:{last_value}")
#
# #print out last year, then this year
# for this_key, this_value in this_years_customer_sales.items():
#     print(f"this_key:{this_key}, this value:{this_value}")

print(f"{len(last_years_customer_sales.keys())}, {len(this_years_customer_sales.keys())}, {len(this_years_customer_invoices.keys())}")

diff_sales = set(last_years_customer_sales.keys()) - set(this_years_customer_sales.keys())
diff_sales = diff_sales - set(this_years_customer_invoices.keys())

# Now that we have the diff lets find the customer name and scout

with open('customers_sold_in_2019_but_not_sold_in_2020.csv', 'w', newline='') as csvfile:
    mulch_writer = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    mulch_writer.writerow(['scout', 'customerName', 'customerPhone', 'customerEmail'])
    for diff in diff_sales:
        customer = Customer.get(diff, qb=client)

        #print(f"DiffCustomerName: {customer.DisplayName}, diffItem:{diff}, scout:{last_years_customer_sales[diff]}, contactPhone:{customer.PrimaryPhone}, customerEmail:{customer.PrimaryEmailAddr}")
        mulch_writer.writerow([last_years_customer_sales[diff], customer.DisplayName,  customer.PrimaryPhone, customer.PrimaryEmailAddr])



