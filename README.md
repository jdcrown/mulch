# Mulch Importer Tool

##### This tool was built for Mulch Madness to extract orders from square's API and massage the data and insert it into quickbooks.

### Duplicate detection

* The duplicate detection works at both the customer and Sales Receipt levels. On the customer, the tool uses the customer **last name**.  If multiple customers with the same last name are discovered, the tool logs the discrepancy and moves to the next customer. 

*Note: This could work better, but sometimes the customer moves to a new address, changes a phone or email and this duplicate detection would not catch this either. So for now we just flag this and move on.*

* For the sales receipt duplication, the tool keys off of customer id, product name, date and quantity. If all those match, we likely have a duplicate. Otherwise it automatically enters a new order for the customer.

### Customer adds

The tool will automatically add a new customer if the **last name** is not found in the quickbooks database. The tool will, under this circumstace, prompt the user to continue or abort this sales order. If you add this customer manually, then next time the tool runs, it will add the sales order.

### Customer moves/changes (TODO)

* If the customer is found, then the tool will compare the address in the database by `<house number> <first token>` in the address. If this is a discrepancy, it prompts the user to make the change or not.
* If the phone number is a mismatch and there is a new one, it just replaces it and moves the old one to the 2nd phone field in the customer record.
* If the email is a mismatch and there is a new one, then it just replaces it wihtout prompting and moves it to the 2nd email field in the customer record.

## Setting up your environment

### Install Miniconda
1. get the latest download from your environment https://docs.conda.io/en/latest/miniconda.html
2. create a working directory and download this code to it
3. open a new terminal window and from that new directory verify conda is installed
    
    `conda --version`
    
4. cd (change directory) to the directory where your project files are. You should see the environment.yml file there.
    
5. create and activate your new environment
    
    `conda env create -n mulch -f environment.yml`

    `conda activate mulch`

### Configure it

Copy the `settings.ini.sample` file to a new one called `settings.ini`

#### Get the key and secret from quickbooks
1. Go to https://developer.intuit.com/app/developer/playground and click on *T581 Mulch Sandbox*

    *Note: If you don't have a developer account contact jcrown@gmail.com for one that is linked to T581 Mulch.*
2. Copy the `client id` and `client secret` into the settings.ini file under the SANDBOX section
3. On the webpage, click all check boxes, then click `Get Authorization Code`, then click `Get Tokens`
4. Scroll all the way down to the section **Refresh access token** and copy the `Refresh Token` into your `settings.ini` file in the same section.

This token should be good for 24 hours. If it expires, you may need to do this over again.

Repeat 1-4 for the **production** secrets, but we will test this working with *sandbox* first.

#### Get the key from your square site

This app will only read data from production. It will not write to it.

1. Sign in to your square account first.
2. Go to your square developer site: https://developer.squareup.com/apps
3. Click the plus box to *create an application*. Name the application.
4. Click open and choose **`production`** at the top. Copy the **production access token** and add this to the **settings.ini** file
5. On the left menu, click **locations** . Copy the `location ID` to your `settings.ini` file.

#### Configure remaining default items in your settings.ini file
* AutoCreateCustomers = yes; This will auto-create customers that are missing. But the software will prompt first.
* DefaultDonationProduct = Donation - T581
* Logging = INFO; Set this to DEBUG if you want verbos logging
* environment = sandbox; use this to enable a dry run to the sandbox quickbooks account first. Highly recommended. 
* start_date = 2020-11-13T00:00; start date that it will begin to process orders from square.
* end_date = 2021-02-15T23:59; end date it will process orders from square.
* Keys : These are filters that are set to look for the product types in square.
  * brown_keys=hardwood|brown
  * red_keys=red
  * black_keys=black
  * donation_keys=donate|donation
  * spreading_keys=spread|spreading

---

### Run it

`python mulch_importer.py`