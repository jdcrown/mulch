# Mulch Importer Tool

##### This tool was built for Mulch Madness to extract orders from square's API and massage the data and insert it into quickbooks.



## Setting up your environment

###Install Miniconda
1. get the latest download from your environment https://docs.conda.io/en/latest/miniconda.html
2. create a working directory and download this code to it
3. open a new terminal window and from that new directory verify conda is installed
    
    `conda --version`
    
4. create and activate your new environment
    
    `conda env create -n mulch -f environment.yml`
    `conda activate mulch`

###Configure it

Copy the `settings.ini.sample` file a new one called `settings.ini`

####Get the key and secret from quickbooks
1. Go to https://developer.intuit.com/app/developer/playground and click on `T581 Mulch Sandbox`
2. Copy the `client id` and `client secret` into the settings.ini file under the SANDBOX section
3. On the webpage, click all check boxes, then click `Get Authorization Code`, then click `Get Tokens`
4. Scroll all the way down to the section **Refresh access token** and copy the `Refresh Token` into your `settings.ini` file in the same section.

This token should be good for 24 hours. If it expires, you may need to do this over again.

Repeat 1-4 for the **production** secrets, but we will test this working first.

####Get the key from your square site

1. Go to your square developer site: https://developer.squareup.com/apps
2. Click the plus box to *create an application*. Name the application.
3. Click open and choose `production` at the top. Copy the **production access token** and add this to the **settings.ini** file

####Configure remaining default items in your settings.ini file
* DryRun = yes; use this to enable a dry run to the sandbox quickbooks account first. Highly recommended.
* AutoCreateCustomers = yes; This will autocreate customers that are missing. But the software will prompt first.
* DefaultDonationProduct = Donation - T581
* Logging = INFO; Set this to DEBUG if you want verbos logging
* environment = sandbox; use this to enable a dry run to the sandbox quickbooks account first. Highly recommended. 
* start_date = 2020-11-13T00:00; start date that it will begin to process orders from square.
* end_date = 2021-02-15T23:59; end date it will process orders from square.


---

###Run it

`python mulch_importer.py`