import requests
import json
import re
import os
import logging
from dataclasses import dataclass
from dateutil.parser import parse
logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)
sales_receipts = []
troop91 = False
QB_BEARER_TOKEN = os.environ.get('BEARER_TOKEN')

#Production
#QB_COMPANY_ID = '193514844769229'
#QB_HOST = 'https://quickbooks.api.intuit.com'

#Sandbox
QB_COMPANY_ID = '123146273978409'
QB_HOST = 'https://sandbox-quickbooks.api.intuit.com'

SQUARE_HOST = "https://connect.squareup.com"


def square_money_to_decimal(price):
    return "{}.{}".format(str(price)[0:-2], str(price)[-2:])



def create_customer(sr):
    # Get the customer
    query_url = QB_HOST + "/v3/company/" + QB_COMPANY_ID + "/customer?minorversion=40"

    headers = {
        'User-Agent': 'QBOV3-OAuth2-Postman-Collection',
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + QB_BEARER_TOKEN,
        'Cookie': 'did=SHOPPER2_7134731dff568c8d3e09ab614daba0dcbd8cd5b4777c69d9dc7d78ce9312e23adfe33649643ee9278553b707844afa8c; s_cpm=%5B%5B\'accounts.youtube.com%20%5Bref%5D\'%2C\'1548096152833\'%5D%5D; dtLatC=537; rxVisitor=15480959750769176QSF3ROIA2OAGMM5B9UPVEIE6QSN6; dtSa=-; dtCookie=2$760391DC30722AD2F3CF0F4D4C8D8D1D|accounts.intuit.com|0; rxvt=1548114992965|1548113149981; dtPC=2$113149972_710h-vGDELIAPKHJOKCIJGWCKNBKNVMLJJMUAN; ivid_b=a677b02e-029d-48a7-8fa8-e50a023bb72c; ivid=643b0e2e-3bfe-4ec4-ae27-ef387d7dae44; qbn.pauth=e81a9d7a-128b-4c73-865e-999da7a39eb1; qbn.glogin=troop581scouting%40gmail.com; s_fid=089FAA3B59F81D6E-00AE0CD03531A52A; AppCenter_Ticket=6_bpeuvjapn_chfyrz_b_cjxzuwfby9cwhgd8r8ghhdgmn756_hd2y7bdxjzuzb9sqmv85h99h6vi83mju89wjs25isppds7426j4b_bpetkcw7n; amplitude_idundefinedintuit.com=eyJvcHRPdXQiOmZhbHNlLCJzZXNzaW9uSWQiOm51bGwsImxhc3RFdmVudFRpbWUiOm51bGwsImV2ZW50SWQiOjAsImlkZW50aWZ5SWQiOjAsInNlcXVlbmNlTnVtYmVyIjowfQ==; amplitude_id_1e35cf9786780b57cf805cd80925b103intuit.com=eyJkZXZpY2VJZCI6IjMxZjZjODhlLTc2NDctNGRhZi04M2Q1LTAxMzg4NzFjMGI1Y1IiLCJ1c2VySWQiOm51bGwsIm9wdE91dCI6ZmFsc2UsInNlc3Npb25JZCI6MTU1MTA2MzIxNzY1NCwibGFzdEV2ZW50VGltZSI6MTU1MTA2NDE5NDA5NiwiZXZlbnRJZCI6MCwiaWRlbnRpZnlJZCI6Nywic2VxdWVuY2VOdW1iZXIiOjd9; __utma=1.117625627.1548095975.1551060789.1551063217.10; __utmc=1; s_vi=[CS]v1|2E2309380507DCC3-4000010F60006344[CE]; ac_s_v8.5_appcenter=agbbpxct2lmdjvxypcrg45wj; qboeuid=81575653.5a03cd7feb24c; ius_session=2A81D71753CC47A7AE0F9941B91FA7D5; s_cc=true; ajs_anonymous_id=%22643b0e2e-3bfe-4ec4-ae27-ef387d7dae44%22; pauth.uuid.prd=e0cb5feb-d093-4c27-af1a-a619b3a67289; s_sq=%5B%5BB%5D%5D; qbn.ticket=V1-167-X0jijnb0d0paylucvc8m5m; qbn.tkt=V1-167-X0jijnb0d0paylucvc8m5m; qbn.authid=123146266514719; qbn.gauthid=123146266514719; qbn.agentid=123146266514719; qbn.uidp=1987d5da8012943f4b250fe19cb0fdfd0; qbn.parentid=50000003; qbn.account_chooser=NovUEMpbnBztvnpcLRUv0j0kNCKqzDMO8Twyfr___cKGEXCUvW8XFNcpWQTKQl-gsdfHPxDkk70C6L4x2gLJlRGZ-Fa1iAbUxuu8KCC3O-zK9neZXThFfP8wDL5Z7E648iRZZ8Y9NTZ7QwZ1MM8jkjyu8BPtiiOJfcZ77Zy0RuY5y5gGgoKG2bAj4oL4gRdrNJPCqmegmuDuzB2VcYbKe9D1DaXcbUBZI_qBoJ67AU0; userIdentifier=123146266514719; ADRUM=s=1613177150626&r=https%3A%2F%2Faccounts.intuit.com%2Findex.html%3F147445178; websdk_swiper_flags='
    }

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


    #revise customer here


    logging.debug("Customer Body Sent: {}".format(customer_body))

    customer_response = requests.request("POST", query_url, headers=headers, data=json.dumps(customer_body))
    customer_record = json.loads(customer_response.text)
    logging.debug("CustomerCreateRecordResponse raw: {}".format(customer_record))
    if customer_record.get('Fault'):
        logging.info("Customer [{}] error: {}".format(sr.customer_name, customer_record['Fault']['Error'][0]['Message']))

def lookup_payment_method(payment_name):
    #Get the customer
    query_url = QB_HOST + "/v3/company/" + QB_COMPANY_ID + "/query?minorversion=4"

    payload = "Select * from PaymentMethod where Active = true and Name = '" + payment_name + "'"

    headers = {
        'User-Agent': 'QBOV3-OAuth2-Postman-Collection',
        'Accept': 'application/json',
        'Content-Type': 'application/text',
        'Authorization': 'Bearer ' + QB_BEARER_TOKEN,
        'Cookie': 'did=SHOPPER2_7134731dff568c8d3e09ab614daba0dcbd8cd5b4777c69d9dc7d78ce9312e23adfe33649643ee9278553b707844afa8c; s_cpm=%5B%5B\'accounts.youtube.com%20%5Bref%5D\'%2C\'1548096152833\'%5D%5D; dtLatC=537; rxVisitor=15480959750769176QSF3ROIA2OAGMM5B9UPVEIE6QSN6; dtSa=-; dtCookie=2$760391DC30722AD2F3CF0F4D4C8D8D1D|accounts.intuit.com|0; rxvt=1548114992965|1548113149981; dtPC=2$113149972_710h-vGDELIAPKHJOKCIJGWCKNBKNVMLJJMUAN; ivid_b=a677b02e-029d-48a7-8fa8-e50a023bb72c; ivid=643b0e2e-3bfe-4ec4-ae27-ef387d7dae44; qbn.pauth=e81a9d7a-128b-4c73-865e-999da7a39eb1; qbn.glogin=troop581scouting%40gmail.com; s_fid=089FAA3B59F81D6E-00AE0CD03531A52A; AppCenter_Ticket=6_bpeuvjapn_chfyrz_b_cjxzuwfby9cwhgd8r8ghhdgmn756_hd2y7bdxjzuzb9sqmv85h99h6vi83mju89wjs25isppds7426j4b_bpetkcw7n; amplitude_idundefinedintuit.com=eyJvcHRPdXQiOmZhbHNlLCJzZXNzaW9uSWQiOm51bGwsImxhc3RFdmVudFRpbWUiOm51bGwsImV2ZW50SWQiOjAsImlkZW50aWZ5SWQiOjAsInNlcXVlbmNlTnVtYmVyIjowfQ==; amplitude_id_1e35cf9786780b57cf805cd80925b103intuit.com=eyJkZXZpY2VJZCI6IjMxZjZjODhlLTc2NDctNGRhZi04M2Q1LTAxMzg4NzFjMGI1Y1IiLCJ1c2VySWQiOm51bGwsIm9wdE91dCI6ZmFsc2UsInNlc3Npb25JZCI6MTU1MTA2MzIxNzY1NCwibGFzdEV2ZW50VGltZSI6MTU1MTA2NDE5NDA5NiwiZXZlbnRJZCI6MCwiaWRlbnRpZnlJZCI6Nywic2VxdWVuY2VOdW1iZXIiOjd9; __utma=1.117625627.1548095975.1551060789.1551063217.10; __utmc=1; s_vi=[CS]v1|2E2309380507DCC3-4000010F60006344[CE]; ac_s_v8.5_appcenter=agbbpxct2lmdjvxypcrg45wj; qboeuid=81575653.5a03cd7feb24c; ius_session=2A81D71753CC47A7AE0F9941B91FA7D5; s_cc=true; ajs_anonymous_id=%22643b0e2e-3bfe-4ec4-ae27-ef387d7dae44%22; pauth.uuid.prd=e0cb5feb-d093-4c27-af1a-a619b3a67289; s_sq=%5B%5BB%5D%5D; qbn.ticket=V1-167-X0jijnb0d0paylucvc8m5m; qbn.tkt=V1-167-X0jijnb0d0paylucvc8m5m; qbn.authid=123146266514719; qbn.gauthid=123146266514719; qbn.agentid=123146266514719; qbn.uidp=1987d5da8012943f4b250fe19cb0fdfd0; qbn.parentid=50000003; qbn.account_chooser=NovUEMpbnBztvnpcLRUv0j0kNCKqzDMO8Twyfr___cKGEXCUvW8XFNcpWQTKQl-gsdfHPxDkk70C6L4x2gLJlRGZ-Fa1iAbUxuu8KCC3O-zK9neZXThFfP8wDL5Z7E648iRZZ8Y9NTZ7QwZ1MM8jkjyu8BPtiiOJfcZ77Zy0RuY5y5gGgoKG2bAj4oL4gRdrNJPCqmegmuDuzB2VcYbKe9D1DaXcbUBZI_qBoJ67AU0; userIdentifier=123146266514719; ADRUM=s=1613177150626&r=https%3A%2F%2Faccounts.intuit.com%2Findex.html%3F147445178; websdk_swiper_flags='
    }

    item_response = requests.request("POST", query_url, headers=headers, data=payload)
    item_record = json.loads(item_response.text)
    logging.debug("PaymentItemRecord: {}".format(item_record))
    if item_record.get('QueryResponse') \
            and item_record['QueryResponse']['PaymentMethod'] \
            and len(item_record['QueryResponse']['PaymentMethod']) == 1:
        return item_record['QueryResponse']['PaymentMethod'][0]['Id']

def lookup_product(product_name):
    #Get the customer
    query_url = QB_HOST + "/v3/company/" + QB_COMPANY_ID + "/query?minorversion=4"

    payload = "Select * from Item where Name = '" + product_name + "'"

    headers = {
        'User-Agent': 'QBOV3-OAuth2-Postman-Collection',
        'Accept': 'application/json',
        'Content-Type': 'application/text',
        'Authorization': 'Bearer ' + QB_BEARER_TOKEN,
        'Cookie': 'did=SHOPPER2_7134731dff568c8d3e09ab614daba0dcbd8cd5b4777c69d9dc7d78ce9312e23adfe33649643ee9278553b707844afa8c; s_cpm=%5B%5B\'accounts.youtube.com%20%5Bref%5D\'%2C\'1548096152833\'%5D%5D; dtLatC=537; rxVisitor=15480959750769176QSF3ROIA2OAGMM5B9UPVEIE6QSN6; dtSa=-; dtCookie=2$760391DC30722AD2F3CF0F4D4C8D8D1D|accounts.intuit.com|0; rxvt=1548114992965|1548113149981; dtPC=2$113149972_710h-vGDELIAPKHJOKCIJGWCKNBKNVMLJJMUAN; ivid_b=a677b02e-029d-48a7-8fa8-e50a023bb72c; ivid=643b0e2e-3bfe-4ec4-ae27-ef387d7dae44; qbn.pauth=e81a9d7a-128b-4c73-865e-999da7a39eb1; qbn.glogin=troop581scouting%40gmail.com; s_fid=089FAA3B59F81D6E-00AE0CD03531A52A; AppCenter_Ticket=6_bpeuvjapn_chfyrz_b_cjxzuwfby9cwhgd8r8ghhdgmn756_hd2y7bdxjzuzb9sqmv85h99h6vi83mju89wjs25isppds7426j4b_bpetkcw7n; amplitude_idundefinedintuit.com=eyJvcHRPdXQiOmZhbHNlLCJzZXNzaW9uSWQiOm51bGwsImxhc3RFdmVudFRpbWUiOm51bGwsImV2ZW50SWQiOjAsImlkZW50aWZ5SWQiOjAsInNlcXVlbmNlTnVtYmVyIjowfQ==; amplitude_id_1e35cf9786780b57cf805cd80925b103intuit.com=eyJkZXZpY2VJZCI6IjMxZjZjODhlLTc2NDctNGRhZi04M2Q1LTAxMzg4NzFjMGI1Y1IiLCJ1c2VySWQiOm51bGwsIm9wdE91dCI6ZmFsc2UsInNlc3Npb25JZCI6MTU1MTA2MzIxNzY1NCwibGFzdEV2ZW50VGltZSI6MTU1MTA2NDE5NDA5NiwiZXZlbnRJZCI6MCwiaWRlbnRpZnlJZCI6Nywic2VxdWVuY2VOdW1iZXIiOjd9; __utma=1.117625627.1548095975.1551060789.1551063217.10; __utmc=1; s_vi=[CS]v1|2E2309380507DCC3-4000010F60006344[CE]; ac_s_v8.5_appcenter=agbbpxct2lmdjvxypcrg45wj; qboeuid=81575653.5a03cd7feb24c; ius_session=2A81D71753CC47A7AE0F9941B91FA7D5; s_cc=true; ajs_anonymous_id=%22643b0e2e-3bfe-4ec4-ae27-ef387d7dae44%22; pauth.uuid.prd=e0cb5feb-d093-4c27-af1a-a619b3a67289; s_sq=%5B%5BB%5D%5D; qbn.ticket=V1-167-X0jijnb0d0paylucvc8m5m; qbn.tkt=V1-167-X0jijnb0d0paylucvc8m5m; qbn.authid=123146266514719; qbn.gauthid=123146266514719; qbn.agentid=123146266514719; qbn.uidp=1987d5da8012943f4b250fe19cb0fdfd0; qbn.parentid=50000003; qbn.account_chooser=NovUEMpbnBztvnpcLRUv0j0kNCKqzDMO8Twyfr___cKGEXCUvW8XFNcpWQTKQl-gsdfHPxDkk70C6L4x2gLJlRGZ-Fa1iAbUxuu8KCC3O-zK9neZXThFfP8wDL5Z7E648iRZZ8Y9NTZ7QwZ1MM8jkjyu8BPtiiOJfcZ77Zy0RuY5y5gGgoKG2bAj4oL4gRdrNJPCqmegmuDuzB2VcYbKe9D1DaXcbUBZI_qBoJ67AU0; userIdentifier=123146266514719; ADRUM=s=1613177150626&r=https%3A%2F%2Faccounts.intuit.com%2Findex.html%3F147445178; websdk_swiper_flags='
    }

    item_response = requests.request("POST", query_url, headers=headers, data=payload)
    item_record = json.loads(item_response.text)
    logging.debug("ItemRecord: {}".format(item_record))
    if item_record.get('QueryResponse') \
            and item_record['QueryResponse']['Item'] \
            and len(item_record['QueryResponse']['Item']) == 1:
        return item_record['QueryResponse']['Item'][0]['Id']

def process_order(sr):

    #Get the customer
    query_url = QB_HOST + "/v3/company/" + QB_COMPANY_ID + "/query?minorversion=4"

    #payload = "select * from Customer where DisplayName = '" + sr.customer_name + "'"
    payload = "select * from Customer Where Active=true and DisplayName LIKE '%" + sr.customer_last + "'"

    headers = {
        'User-Agent': 'QBOV3-OAuth2-Postman-Collection',
        'Accept': 'application/json',
        'Content-Type': 'application/text',
        'Authorization': 'Bearer ' + QB_BEARER_TOKEN,
        'Cookie': 'did=SHOPPER2_7134731dff568c8d3e09ab614daba0dcbd8cd5b4777c69d9dc7d78ce9312e23adfe33649643ee9278553b707844afa8c; s_cpm=%5B%5B\'accounts.youtube.com%20%5Bref%5D\'%2C\'1548096152833\'%5D%5D; dtLatC=537; rxVisitor=15480959750769176QSF3ROIA2OAGMM5B9UPVEIE6QSN6; dtSa=-; dtCookie=2$760391DC30722AD2F3CF0F4D4C8D8D1D|accounts.intuit.com|0; rxvt=1548114992965|1548113149981; dtPC=2$113149972_710h-vGDELIAPKHJOKCIJGWCKNBKNVMLJJMUAN; ivid_b=a677b02e-029d-48a7-8fa8-e50a023bb72c; ivid=643b0e2e-3bfe-4ec4-ae27-ef387d7dae44; qbn.pauth=e81a9d7a-128b-4c73-865e-999da7a39eb1; qbn.glogin=troop581scouting%40gmail.com; s_fid=089FAA3B59F81D6E-00AE0CD03531A52A; AppCenter_Ticket=6_bpeuvjapn_chfyrz_b_cjxzuwfby9cwhgd8r8ghhdgmn756_hd2y7bdxjzuzb9sqmv85h99h6vi83mju89wjs25isppds7426j4b_bpetkcw7n; amplitude_idundefinedintuit.com=eyJvcHRPdXQiOmZhbHNlLCJzZXNzaW9uSWQiOm51bGwsImxhc3RFdmVudFRpbWUiOm51bGwsImV2ZW50SWQiOjAsImlkZW50aWZ5SWQiOjAsInNlcXVlbmNlTnVtYmVyIjowfQ==; amplitude_id_1e35cf9786780b57cf805cd80925b103intuit.com=eyJkZXZpY2VJZCI6IjMxZjZjODhlLTc2NDctNGRhZi04M2Q1LTAxMzg4NzFjMGI1Y1IiLCJ1c2VySWQiOm51bGwsIm9wdE91dCI6ZmFsc2UsInNlc3Npb25JZCI6MTU1MTA2MzIxNzY1NCwibGFzdEV2ZW50VGltZSI6MTU1MTA2NDE5NDA5NiwiZXZlbnRJZCI6MCwiaWRlbnRpZnlJZCI6Nywic2VxdWVuY2VOdW1iZXIiOjd9; __utma=1.117625627.1548095975.1551060789.1551063217.10; __utmc=1; s_vi=[CS]v1|2E2309380507DCC3-4000010F60006344[CE]; ac_s_v8.5_appcenter=agbbpxct2lmdjvxypcrg45wj; qboeuid=81575653.5a03cd7feb24c; ius_session=2A81D71753CC47A7AE0F9941B91FA7D5; s_cc=true; ajs_anonymous_id=%22643b0e2e-3bfe-4ec4-ae27-ef387d7dae44%22; pauth.uuid.prd=e0cb5feb-d093-4c27-af1a-a619b3a67289; s_sq=%5B%5BB%5D%5D; qbn.ticket=V1-167-X0jijnb0d0paylucvc8m5m; qbn.tkt=V1-167-X0jijnb0d0paylucvc8m5m; qbn.authid=123146266514719; qbn.gauthid=123146266514719; qbn.agentid=123146266514719; qbn.uidp=1987d5da8012943f4b250fe19cb0fdfd0; qbn.parentid=50000003; qbn.account_chooser=NovUEMpbnBztvnpcLRUv0j0kNCKqzDMO8Twyfr___cKGEXCUvW8XFNcpWQTKQl-gsdfHPxDkk70C6L4x2gLJlRGZ-Fa1iAbUxuu8KCC3O-zK9neZXThFfP8wDL5Z7E648iRZZ8Y9NTZ7QwZ1MM8jkjyu8BPtiiOJfcZ77Zy0RuY5y5gGgoKG2bAj4oL4gRdrNJPCqmegmuDuzB2VcYbKe9D1DaXcbUBZI_qBoJ67AU0; userIdentifier=123146266514719; ADRUM=s=1613177150626&r=https%3A%2F%2Faccounts.intuit.com%2Findex.html%3F147445178; websdk_swiper_flags='
    }

    sr_body = {
          "domain": "QBO",
          "Balance": 0,
          "CustomerRef": {
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
          }
        }


    customer_response = requests.request("POST", query_url, headers=headers, data=payload)
    customer_record = json.loads(customer_response.text)
    logging.debug("CustomerRecord: {}".format(customer_record))
    if customer_record.get('QueryResponse') \
            and customer_record['QueryResponse']['Customer'] \
            and len(customer_record['QueryResponse']['Customer']) == 1:
        #we have found a customer
        customer_id = customer_record['QueryResponse']['Customer'][0]['Id']
        logging.debug("Customer id: {}".format(customer_id))

        sr_body['CustomerRef']['value'] = customer_id
        sr_body['Line'][0]['Amount'] = sr.total_price
        if 'donate' in sr.product_name.lower():
            sr_body['Line'][0]['SalesItemLineDetail']['Qty'] = '1'
            sr_body['Line'][0]['SalesItemLineDetail']['UnitPrice'] = sr.total_price
        else:
            sr_body['Line'][0]['SalesItemLineDetail']['Qty'] = sr.product_qty
            sr_body['Line'][0]['SalesItemLineDetail']['UnitPrice'] = sr.product_price
            product_id = lookup_product(sr.product_name)
            sr_body['Line'][0]['SalesItemLineDetail']['ItemRef']['value'] = product_id
        logging.debug("Revised Customer: {}".format(sr_body))
        #print("SR Body: {}".format(sr_body))

        #post a new one
        create_sr_url = QB_HOST + "/v3/company/" + QB_COMPANY_ID + "/salesreceipt?minorversion=4"
        logging.debug("SendBody: {}".format(json.dumps(sr_body)))
        headers['Content-Type'] = 'application/json'
        sr_response = requests.request("POST", create_sr_url, headers=headers, data=json.dumps(sr_body))
        logging.debug("SalesReceiptResponse: {}".format(sr_response.text))
        sales_receipt_response = json.loads(sr_response.text)
        if sales_receipt_response.get('SalesReceipt') and sales_receipt_response['SalesReceipt']['Id']:
            logging.info("Successful entry of Customer: [{}] into quickbooks. OrderId:[{}], Item:[{}], Qty:[{}], Total:[{}]".format(sr.customer_name,sales_receipt_response['SalesReceipt']['Id'],sr.product_name,sr.product_qty,sr.total_price))
    elif customer_record['QueryResponse'] and len(str(customer_record['QueryResponse']['Customer'])) > 1:
        logging.warning("More than one customer matches name: [{}]. Cannot process record. Skipping.".format(sr.customer_last))
    else:
        #create a new customer?
        logging.warning("Need to create a customer [{}] in quickbooks first.".format(sr.customer_name))
        create_customer(sr)

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

    spread_pattern = re.compile('spreading')
    donation_pattern = re.compile('donate')

    if 'black' in item_name:
        sr.product_name = "Black Mulch" + tier
    elif item_name in ["brown", "hardwood"]:
        sr.product_name = "Brown Mulch" + tier
    elif item_name in ["red"]:
        sr.product_name = "Red Mulch" + tier
    elif spread_pattern.match(item_name):
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
    elif donation_pattern.match(item_name):
        if troop91:
            sr.product_name = 'Donation - T91'
        else:
            sr.product_name = 'Donation - T581'
    return sr

@dataclass
class SalesReceipt:
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


url = SQUARE_HOST + "/v2/orders/search"
payload="{\n  \"location_ids\": [\n  \t\"EXMEGPYWHET3P\"\n  \t],\n  \t \"query\": {\n      \"filter\": {\n      \t\"customer_ids\": [\n      \t\t\"{{customer_id}}\"\n      \t\t]\n      }\n    }\n}"
headers = {
  'Content-Type': 'application/json',
  'Authorization': 'Bearer EAAAEVKtyYvqSGmrYQAX63-Tq2PtozZC7uZisIEuvkximfBDuY8G71akI8dnIm_5'
}

#get transaction
response = requests.request("POST", url, headers=headers, data=payload)


key_list = ['black', 'red', 'hardwood', 'brown', 'spread', 'donate', 'donation']
all_orders = json.loads(response.text)

for order in all_orders['orders']:

    created_on = parse(order.get('created_at')).date()
    #check only from a certain time forward
    #if created_on >= parse('2020-11-01').date() and created_on < parse('2021-02-14').date():
    #if order.get('id') == 'Hv5nLw567WQcPMvyEFRvbttF7BeZY': #me
    if order.get('id') == 'vtwmcNbBlJCJ15WXoPQIuQVzYucZY': #sissy
        logging.debug("Order: {}".format(order))
        if 'line_items' in order:
            #line_items = order['line_items']
            for item in order['line_items']:
                sr = SalesReceipt()
                logging.debug("Processing Line Item: {}".format(item))
                if 'name' in item:
                    #print(item0)
                    reg_list = map(re.compile, key_list)

                    if any(regex.match(item['name'].lower()) for regex in reg_list):
                        logging.debug("Processing Line Item: {}".format(item))
                        # get customer for order if we have a customer id
                        if bool(order.get('customer_id', None)):
                            customer_id = order['customer_id']
                            tenders_id = order['tenders'][0]['id']
                            payment_url = SQUARE_HOST + "/v2/payments/" + tenders_id
                            payment_raw = requests.request("GET", payment_url, headers=headers, data=payload)
                            payment = json.loads(payment_raw.text)['payment']
                            logging.debug("Payment Raw: {}".format(payment))
                            sr.customer_street = payment['shipping_address']['address_line_1']
                            sr.customer_state = payment['shipping_address']['administrative_district_level_1']
                            sr.customer_city = payment['shipping_address']['locality']
                            sr.customer_zip = payment['shipping_address']['postal_code']
                            sr.customer_email = payment['buyer_email_address']
                            customer_url = SQUARE_HOST + "/v2/customers/" + customer_id
                            customer_raw = requests.request("GET", customer_url, headers=headers, data=payload)
                            customer = json.loads(customer_raw.text)['customer']
                            logging.debug("Customer Response: {}".format(customer))
                            sr.customer_first = format(customer['given_name'])
                            sr.customer_last = customer['family_name']
                            sr.customer_name = "{} {}".format(customer['given_name'], customer['family_name'])
                            sr.customer_phone = customer.get('phone_number', None)

                        else:  # otherwise get the customer from the order itself (customer not registered)
                            logging.debug("getting from fulfillments")
                            sr.customer_name = order['fulfillments'][0]['shipment_details']['recipient']['display_name']
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


                        #print("matched: {}".format(item0))
                        item_name = item['name'].lower()
                        item_quantity = int(item['quantity'])
                        item_variation = item['variation_name']

                        #now we have a clean line item for mulch. Build the object out for importing into quickbooks

                        sr = extract_item(sr, item_quantity, item_name, item_variation)
                        sr.date = order['created_at']
                        sr.product_price = square_money_to_decimal(item['base_price_money']['amount'])
                        sr.total_price = square_money_to_decimal(item['total_money']['amount'])
                        process_order(sr)
                        logging.debug(sr)
