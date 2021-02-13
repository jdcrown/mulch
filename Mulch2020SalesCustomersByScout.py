from intuitlib.client import AuthClient
from quickbooks import QuickBooks
from quickbooks.objects.customer import Customer
from datetime import time
from quickbooks.objects.salesreceipt import SalesReceipt
import inspect

from intuitlib.enums import Scopes

#SANDBOX
# CLIENT_ID= 'Q0gi4IpcoE322BxbjIgtDEZhGnabOsnfWuTzgLL4UA768Zf559'
# CLIENT_SECRET = 'b3sDUGRyO18GcmgqDt2VDsH50ZePDhP8t2XyZ6jT'
# COMPANY_ID='123146273978409'
# REFRESH_TOKEN='AB11590594008hlMfVhaedDsriGmwO20xIql94TzCPf4YxZtys'

#PROD T581
CLIENT_ID= 'Q0qYrX2LrOfiA6vjGNzANtYXha9G8qnI03yX6cNqziCWHmrZld'
CLIENT_SECRET = 'YzeWqqEy03pnD1BlzZHWCCKyqIauRIXOclKCpCNm'
COMPANY_ID='193514844769229'
REFRESH_TOKEN='AB11592284379LUtspT5VkMyANMBdD3CjLkdMoH5WGdwW2C7V1'


print("authorizing...")
auth_client = AuthClient(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        environment='prod',
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


