from __future__ import print_function
##NOTES/CREDS
##################################

import requests
import base64
import pandas as pd
import pprint
import smtplib
import httplib2
import os
import mysql.connector
import time
from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage
import argparse
from datetime import date, datetime
from email.mime.text import MIMEText

app_token = 'yourapptoken'
consumer_key = 'yourconsumerkey'
consumer_secret = 'yoursecret'
stubhub_username = 'testuser@gmail.com'
stubhub_password = 'stubhubpassword'

combo = consumer_key + ':' + consumer_secret
basic_authorization_token = base64.b64encode(combo)

url = 'https://api.stubhub.com/login'
headers = {
        'Content-Type':'application/x-www-form-urlencoded',
        'Authorization':'Basic '+basic_authorization_token,}
body = {
        'grant_type':'password',
        'username':stubhub_username,
        'password':stubhub_password,
        'scope':'PRODUCTION'}

r = requests.post(url, headers=headers, data=body)

token_respoonse = r.json()
access_token = token_respoonse['access_token']
user_GUID = r.headers['X-StubHub-User-GUID']

try:
  flags argparse.ArguementParser(parents=[tools.argparser]).parse_args()
except ImportError:
  flags = None
SCOPES = 'https://www.googleapis.com/auth/spreadsheets.readonly'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Google Sheets API Python Quickstart'

def get_credentials():
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
        'sheets.googleapis.com-python-quickstart.json')
    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else: # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials

def main():
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    discoveryUrl = ('https://sheets.googleapis.com/$discovery/rest?'
                'version=v4')
    service = discovery.build('sheets', 'v4', http=http,
                              discoveryServiceUrl=discoveryUrl)
    spreadsheetId = 'googlespreadID'
    rangeName = 'datarange'
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheetId, range=rangeName).execute()
    values = result.get('values', [])
    print(values)
    #if not values:
       # print('No data found.')
    #else:
        #print('EventId, ShowDate, PricePaid')
        #for row in values:
        # Print columns A and E, which correspond to indices 0 and 4.
            #print('%s, %s, %s' % (row[8], row[4],row[2]))
    return values

values = main()
eventid = {}
showname ={}
PricePaid = {}
RawShowDate = {}
Venue ={}
SoldPrice = {}
SoldDate = {}
cnx = mysql.connector.connect(user='root',password='sqlpassword',host='localhost',database='yourdatabase')
cursor = cnx.cursor()
for row in values:
  showname = row[0]
  eventid = row[8]
  PricePaid = row[2]
  #THIS RETURNS SOMETHING LIKE YYYY/MM/DD
  RawShowDate = row[4]
  SoldPrice = row[6]
  SoldDate = row[5]
  if eventid is not None:
    if SoldPrice != '':
      #how to deal with already sold tickets? needs to update rows
      pass
    else:
      try:
        inventory_url = 'https://api.stubhub.com/search/inventory/v1'
        data = {'eventid':eventid}
        info_url = 'https://api.stubhub.com/catalog/events/v2/' + eventid
        headers['Authorization'] = 'Bearer ' + access_token
        headers['Accept'] = 'application/json'
        headers['Accept-Encoding'] = 'application/json'
        inventory = requests.get(inventory_url, headers=headers, params=data)
        info = requests.get(info_url, headers=headers)
        inv = inventory.json()
        inf = info.json()
        #pprint.pprint(inv['listing'])
        for t in inv['listing']:
            for k,v in t.items():
                if k == 'currentPrice':
                    t['amount'] = v['amount']
        listing = inv['listing']
        information = inf['venue']
        listing_df = pd.DataFrame(listing)
        #quanlowest = listing_df('quantity')
        #quanlow = quanlowest[0]
        #inf_df = pd.DataFrame(inf)
        venue = information['name']
        ##THIS CONVERSION SUCKS
        amounts = listing_df['amount'].tolist()
        amounti = min(amounts)
        #tdate = datetime.now().date()
        #today = tdate.isoformat()
        ShowDate = datetime.strptime(RawShowDate,'%m/%d/%Y')
        today = datetime.now().date().isoformat()
        ##GET VENUE INFO
        #info_url = 'https://api.stubhub.com/catalog/events/v2/' + '9632661'
        #nfo = requests.get(info_url, headers=headers)
        #pprint.pprint(info.json())
        #inf = info.json()
        #information = inf['venue']
        venue = information['name']
        cursor.execute("insert into masterii (ShowName, EventId,CurrentPrice, Qdate,PricePaid,Venue,ShowDate) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                       (showname,eventid,amounti,today,PricePaid,venue,ShowDate))
        cnx.commit()
        time.sleep(10)
      except:
        print('No Tickets Available on Stub for '+ eventid)
  else:
    pass

## EMAIL OUT CODE - To format I must use HTML.
##################################
def email():
  from email.mime.text import MIMEText
  from email.mime.multipart import MIMEMultipart
  today = [datetime.now().date().isoformat()]
  headate = datetime.now().date().strftime("%m-%d-%Y")
  sql = 'SELECT ShowName,PricePaid,CurrentPrice,ShowDate,Venue FROM masterii where qDate IN (%s)'
  cursor.execute(sql,today)
  data = cursor.fetchall()
  dataf = pd.DataFrame(data)
  dataf.columns=['ShowName','PricePaid','CurrentPrice','ShowDate','Venue']
  fromaddr='myemail'
  toaddr = ['user1','user2']
  #toaddr = ['codykessler@gmail.com']
  msg = MIMEMultipart('alternative')
  msg['Subject']= "Daily Price Report" + ' ' + headate
  msg['From'] = fromaddr
  msg['To'] = ", ".join(toaddr)
  text = dataf.to_string()
  gmailuser = 'codykessler@gmail.com'
  gmailpassword = 'oumtcypzcobixmvt'
  html = dataf.to_html(index=False,justify='left')
  part1 = MIMEText(text,'plain')
  part2 = MIMEText(html,'html')
  msg.attach(part1)
  msg.attach(part2)
  try:
      server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
      server.ehlo()
      server.login(gmailuser, gmailpassword)
      server.sendmail(fromaddr,toaddr,msg.as_string())
      server.close()
      print('Email sent!')
  except:
      print('Something went wrong...')

email()
cnx.close()
