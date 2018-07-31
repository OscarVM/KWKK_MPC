# -*- coding: utf-8 -*-
"""
Created on Fri Jun 01 12:37:14 2018

@author: INES
"""

import pylab as pl
from datetime import datetime, timedelta
import pytz
import webpage as web
cet = pytz.timezone('Europe/Amsterdam')
pl.close("all")

epexread = True
date = datetime.now()
dt = 4
n = 97


def price_to_15min(dt, Input_list ): #Don´t interpolate values but repeat the same value i+(dt-1) times e.g  1,2,3,4 = 1,1,1,1,2,2,2,2,3,3,3.....
    sz=int(Input_list.size)          #dt = 4 for 15 min
    Split_list = []
    for i in range(sz):
        Split_list =  pl.append(Split_list,pl.ones(dt)*Input_list[i])
    return Split_list 



price_today=[]
price_tomorrow=[]
intprice_15m = []
bsell = 0.151
bbuy = 0.297
#    date = cet.localize(datetime.datetime(2018, 5, 9))
#    date = datetime.now()
date_plus = date + timedelta(days=1)

## ---retrieve the day ahead information by scrapping the DA webpage...
da_page = web.DayAheadWebpage()
da_page.set_date(cet.localize(date_plus))
da_page.download_page()
da_page.parse()
##--Filter the info to a list of both
for row in  da_page.basepeak_de.iterrows():
    if (row[1]['time_stamp'].date() == date.date()):
#            print(row[1]['price_base'])
        bprice_today = float(web.nat2none(row[1]['price_base']))
    if (row[1]['time_stamp'].date() == date_plus.date()):
        bprice_tomorrow = float(web.nat2none(row[1]['price_base']))

for row in da_page.hours_de.iterrows():
    if row[1]['time_stamp'].date() == date.date():
        price_today.append(float(web.nat2none(row[1]['price'])))
        
    if row[1]['time_stamp'].date() == (date_plus.date()):
        price_tomorrow.append(float(web.nat2none(row[1]['price'])))
 
#    print(price_today)
#    print(price_tomorrow)
#    cost_buy = pl.append((pl.array(price_today)/1000.)+ bprice_today/1000.,(pl.array(price_tomorrow)/1000.)+ bprice_tomorrow/1000.) 
#    cost_buy =  pl.append((pl.array(price_today)/1000.)+ bbuy ,(pl.array(price_tomorrow)/1000.)+ bbuy) 
#    cost_sell = pl.append((pl.array(price_today)/1000.)+ bsell,(pl.array(price_tomorrow)/1000.)+ bsell)

epexdt = date.time().hour*dt + int(date.time().minute/(60/dt))
#    da_buy15 = price_to_15min(dt,cost_buy)
#    da_buy15 = da_buy15[epexdt:(n-1)+epexdt]
#    
#    da_sell15 = price_to_15min(dt,cost_sell)
#    da_sell15 = da_sell15[epexdt:(n-1)+epexdt]

 ## ---retrieve the intraday information by scrapping the Intradaycontiniuos webpage...
int_page = web.IntradayWebpageDE()
int_page.set_date(cet.localize(date))
int_page.download_page()
int_page.parse()

#    print (int_page.df)
for row in int_page.df.iterrows():
    if row[1]['time_stamp'].date() == date.date():
        if (row[1]['time_stamp_end'].minute - row[1]['time_stamp'].minute) == 15 or (row[1]['time_stamp_end'].minute - row[1]['time_stamp'].minute)==-45:
            intprice_15m.append(float(web.nat2none(row[1]['weighted_avg'])))
 


print(intprice_15m)
    
##-------------- condense the data to a (n-1 length list )

  #-- transform pricetomorrow to 15 min

if len(price_tomorrow)<(24):
    price_tomorrow = intprice_15m
else:
    price_tomorrow = price_to_15min(dt,pl.array(price_tomorrow))
    
print(price_tomorrow)   
 
cost_buy =  pl.append((pl.array(intprice_15m)/1000.)+ bbuy ,(pl.array(price_tomorrow)/1000.)+ bbuy) 
cost_sell = pl.append((pl.array(intprice_15m)/1000.)+ bsell,(pl.array(price_tomorrow)/1000.)+ bsell) 

da_buy15 = cost_buy[epexdt:(n-1)+epexdt]
da_sell15 = cost_sell[epexdt:(n-1)+epexdt]


