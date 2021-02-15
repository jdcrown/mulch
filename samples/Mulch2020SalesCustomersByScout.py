from intuitlib.client import AuthClient
from quickbooks import QuickBooks
from quickbooks.objects.customer import Customer
from datetime import time
from quickbooks.objects.salesreceipt import SalesReceipt
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
        redirect_uri='https://developer.intuit.com/v2/OAuth2Playground/RedirectUrl',
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

sales = SalesReceipt.query(f"SELECT * FROM salesreceipt where MetaData.CreateTime > '2019-12-01' MAXRESULTS 1000", qb=client)
cnt = 0

print(f"Scout, Customer, Phone, Email")
for sale in sales:
    cnt += 1
    scout = sale.CustomField[0].StringValue
    if len(scout) == 0:
        scout = "none"
    else:
        scout = scout.replace(',',': ')

    customer = Customer.get(sale.CustomerRef.value, qb=client)
    print(f"{scout},{customer.DisplayName},{customer.PrimaryPhone},{customer.PrimaryEmailAddr}")


