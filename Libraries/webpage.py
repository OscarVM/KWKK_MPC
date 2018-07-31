# -*- coding: utf-8 -*-

import requests
import time
import datetime
from bs4 import BeautifulSoup
import pandas
import pytz
import sys
cet = pytz.timezone('Europe/Amsterdam')


class Webpage:
    def __init__(self):
        self.html = None
        self.url = None
        self.date = None
        self.df = pandas.DataFrame()
        self.df_hourly = pandas.DataFrame()
        self.table = None
        self.html_soup = None

    def download_page(self):
        self.make_url()
        fail = True
        while fail:
            try:
                r = requests.get(self.url)
                r.encoding = 'utf-8'
                self.html = r.text
                fail = False
            except:
                print('DL Failed, wait 60 sec')
                time.sleep(60)

    def set_date(self, date):
        self.date = date

    def date1(self):
        date = self.table.find('th', 'date', colspan=self.config['date1_colspan']).contents[0]
        date = (datetime.datetime.strptime(date, '%d/%m/%Y'))
        return date

    def date2(self):
        date = self.table.find('th', 'date', colspan=self.config['date2_colspan']).contents[0]
        date = (datetime.datetime.strptime(date, '%d/%m/%Y'))
        return date

    def find_base(self):
        bases = self.table.find_all('th', 'date', colspan=self.config['base_colspan'])
        self.base1 = clear_string(bases[0].contents[0].replace('Base: ', ''))
        base2 = clear_string(bases[1].contents[0].replace('Base: ', ''))
#       print(base1,base2)

    def find_peaks(self):
        peaks = self.table.find_all('th', 'date', colspan=self.config['peak_colspan'])
        peak1 = clear_string(peaks[0].contents[0].replace('Peak: ', ''))
        peak2 = clear_string(peaks[1].contents[0].replace('Peak: ', ''))
#        print(peak1,peak2)

class IntrayDayWebpage(Webpage):
    url_trunk = 'http://www.epexspot.com/en/market-data/intradaycontinuous/intraday-table/'
    type_identifier = 'intraday'

    def make_url(self):
        url_date = str(self.date.date())
        self.url = self.url_trunk + url_date + '/' + self.country_identifier + '/'

    def parse(self):
        self.html_soup = BeautifulSoup(self.html, "lxml")
        self.table = self.html_soup.find('table')
        self.parse_tables()
        self.find_base()
        self.find_peaks()

    def parse_tables(self):
        self.df = pandas.DataFrame()
        self.df_hourly = pandas.DataFrame()
        for row in self.table.find_all('tr'):
            time_tag = row.find('td', 'title', colspan=None)
            if time_tag is not None:
                time_start = clear_string(time_tag.contents[0].split('-')[0])
                time_end = clear_string(time_tag.contents[0].split('-')[1])
                values = row.find_all('td', None)
                if len(time_start) == 2:
                    ts1_start = (self.date1() + datetime.timedelta(hours=int(time_start)))
                    ts1_end = (self.date1() + datetime.timedelta(hours=int(time_end)))
                    ts2_start = (self.date2() + datetime.timedelta(hours=int(time_start)))
                    ts2_end = (self.date2() + datetime.timedelta(hours=int(time_end)))
                    self.df_hourly = self.df_hourly.append(self.day1_to_dict(values, ts1_start, ts1_end), ignore_index=True)
                    self.df_hourly = self.df_hourly.append(self.day2_to_dict(values, ts2_start, ts2_end), ignore_index=True)
                elif len(time_start) == 5:
                    time_start = time_start.split(':')
                    time_end = time_end.split(':')
                    ts1_start = self.date1() + datetime.timedelta(hours=int(time_start[0]), minutes=int(time_start[1]))
                    ts1_end = self.date1() + datetime.timedelta(hours=int(time_end[0]), minutes=int(time_end[1]))
                    ts2_start = self.date2() + datetime.timedelta(hours=int(time_start[0]), minutes=int(time_start[1]))
                    ts2_end = self.date2() + datetime.timedelta(hours=int(time_end[0]), minutes=int(time_end[1]))
                    self.df = self.df.append(self.day1_to_dict(values, ts1_start, ts1_end), ignore_index=True)
                    self.df = self.df.append(self.day2_to_dict(values, ts2_start, ts2_end), ignore_index=True)
        self.df_hourly = self.df_hourly.sort_values(by=['time_stamp'])
        self.df_hourly = self.df_hourly.set_index('time_stamp_end').tz_localize('UTC')
        self.df_hourly.reset_index(inplace=True)
        self.df_hourly = self.df_hourly.set_index('time_stamp').tz_localize('UTC')
        self.df_hourly.reset_index(inplace=True)
        self.df_hourly = self.df_hourly.sort_values(by=['time_stamp'])

        self.df = self.df.sort_values(by=['time_stamp'])
        self.df = self.df.set_index('time_stamp_end').tz_localize('UTC')
        self.df.reset_index(inplace=True)
        self.df = self.df.set_index('time_stamp').tz_localize('UTC')
        self.df.reset_index(inplace=True)
        self.df = self.df.sort_values(by=['time_stamp'])


class IntradayWebpageFR(IntrayDayWebpage):
    country_identifier = 'FR'
    config = {'date1_colspan': '8',
              'date2_colspan': '7',
              'peak_colspan': '4',
              'base_colspan': '3'}

    def day1_to_dict(self, values, time_start, time_end):
        return {'time_stamp': time_start,
                'time_stamp_end': time_end,
                'low': clear_string(values[3].contents[0]),
                'high': clear_string(values[4].contents[0]),
                'last': clear_string(values[5].contents[0]),
                'weighted_avg': clear_string(values[6].contents[0]),
                'index': clear_string(values[7].contents[0]),
                'id3_price': clear_string(values[8].contents[0]),
                'buy_volume': clear_string(values[9].contents[0]),
                'sell_volume': clear_string(values[10].contents[0])}

    def day2_to_dict(self, values, time_start, time_end):
        return {'time_stamp': time_start,
                'time_stamp_end': time_end,
                'low': clear_string(values[12].contents[0]),
                'high': clear_string(values[13].contents[0]),
                'last': clear_string(values[14].contents[0]),
                'weighted_avg': clear_string(values[15].contents[0]),
                'index': clear_string(values[16].contents[0]),
                'id3_price': clear_string(values[17].contents[0]),
                'buy_volume': clear_string(values[18].contents[0]),
                'sell_volume': clear_string(values[19].contents[0])}


class IntradayWebpageDE(IntrayDayWebpage):
    country_identifier = 'DE'
    config = {'date1_colspan': '9',
              'date2_colspan': '8',
              'peak_colspan': '5',
              'base_colspan': '3'}

    def day1_to_dict(self, values, time_start, time_end):
        return {'time_stamp': time_start,
                'time_stamp_end': time_end,
                'low': clear_string(values[3].contents[0]),
                'high': clear_string(values[4].contents[0]),
                'last': clear_string(values[5].contents[0]),
                'weighted_avg': clear_string(values[6].contents[0]),
                'index': clear_string(values[7].contents[0]),
                'id3_price': clear_string(values[8].contents[0]),
                'id1_price': clear_string(values[9].contents[0]),
                'buy_volume': clear_string(values[10].contents[0]),
                'sell_volume': clear_string(values[11].contents[0])}

    def day2_to_dict(self, values, time_start, time_end):
        return {'time_stamp': time_start,
                'time_stamp_end': time_end,
                'low': clear_string(values[13].contents[0]),
                'high': clear_string(values[14].contents[0]),
                'last': clear_string(values[15].contents[0]),
                'weighted_avg': clear_string(values[16].contents[0]),
                'index': clear_string(values[17].contents[0]),
                'id3_price': clear_string(values[18].contents[0]),
                'id1_price': clear_string(values[19].contents[0]),
                'buy_volume': clear_string(values[20].contents[0]),
                'sell_volume': clear_string(values[21].contents[0])}


class IntradayWebpageCH(IntradayWebpageFR):
    country_identifier = 'CH'
    config = {'date1_colspan': '7',
              'date2_colspan': '6',
              'peak_colspan': '3',
              'base_colspan': '3'}

    def day1_to_dict(self, values, time_start, time_end):
        return {'time_stamp': time_start,
                'time_stamp_end': time_end,
                'low': clear_string(values[3].contents[0]),
                'high': clear_string(values[4].contents[0]),
                'last': clear_string(values[5].contents[0]),
                'weighted_avg': clear_string(values[6].contents[0]),
                'index': clear_string(values[7].contents[0]),
                'buy_volume': clear_string(values[8].contents[0]),
                'sell_volume': clear_string(values[9].contents[0])}

    def day2_to_dict(self, values, time_start, time_end):
        return {'time_stamp': time_start,
                'time_stamp_end': time_end,
                'low': clear_string(values[11].contents[0]),
                'high': clear_string(values[12].contents[0]),
                'last': clear_string(values[13].contents[0]),
                'weighted_avg': clear_string(values[14].contents[0]),
                'index': clear_string(values[15].contents[0]),
                'buy_volume': clear_string(values[16].contents[0]),
                'sell_volume': clear_string(values[17].contents[0])}


def clear_string(string):
 
    if sys.version_info[0]<3:
        string = string.encode('utf-8').strip()
    else:
        string = string.strip() 
    string = string.replace(',', '')
    string = string.replace('&amp;', 'and')
    string = string.replace('&nbsp;', '')
    string = string.replace('&#8211;', '-')
    string = string.replace('None', '')
    string = string.replace('–', '')
    string = string
    if string == '':
        string = None
    return string



class DayAheadWebpage(Webpage):

    def __init__(self):
        self.html = None
        self.url = None
        self.date = None
        self.table = None
        self.html_soup = None
        self.time_stamps = None
        self.basepeak_fr = None
        self.basepeak_de = None
        self.basepeak_ch = None
        self.blocks_fr = None
        self.blocks_de = None
        self.blocks_ch = None
        self.hours_fr = None
        self.hours_de = None
        self.hours_ch = None

    def make_url(self):
        url_trunk = 'http://www.epexspot.com/en/market-data/dayaheadauction/auction-table/'
        url_date = str(self.date.date())
        self.url = url_trunk + url_date + '/'

    def parse(self):
        self.html_soup = BeautifulSoup(self.html, "lxml")
        self.extract_timestamps()
        self.extract_tables()

    def extract_timestamps(self):
        self.time_stamps = []
        dates = (self.html_soup.find_all('span', 'date')[0].contents[0].split(' - '))
        date = datetime.datetime.strptime(clear_string(dates[0]), '%d/%m/%Y')
        end_date = datetime.datetime.strptime(clear_string(dates[1]), '%d/%m/%Y')
        while date <= end_date:
            self.time_stamps.append(date)
            date += datetime.timedelta(days=1)

    def extract_tables(self):
        basepeak_fr_table = self.html_soup.find_all('table')[0]
        basepeak_de_table = self.html_soup.find_all('table')[3]
        basepeak_ch_table = self.html_soup.find_all('table')[6]
        self.basepeak_fr = self.extract_basepeak(basepeak_fr_table)
        self.basepeak_de = self.extract_basepeak(basepeak_de_table)
        self.basepeak_ch = self.extract_basepeak(basepeak_ch_table)

        blocks_fr_table = self.html_soup.find_all('table')[1]
        blocks_de_table = self.html_soup.find_all('table')[4]
        blocks_ch_table = self.html_soup.find_all('table')[7]
        self.blocks_fr = self.extract_blocks(blocks_fr_table)
        self.blocks_de = self.extract_blocks(blocks_de_table)
        self.blocks_ch = self.extract_blocks(blocks_ch_table)

        hours_fr_table = self.html_soup.find_all('table')[2]
        hours_de_table = self.html_soup.find_all('table')[5]
        hours_ch_table = self.html_soup.find_all('table')[8]
        self.hours_fr = self.extract_hours(hours_fr_table)
        self.hours_de = self.extract_hours(hours_de_table)
        self.hours_ch = self.extract_hours(hours_ch_table)

    def extract_basepeak(self, table):
        rows = table.find_all('tr')
        price_base = []
        volume_base = []
        price_peak = []
        volume_peak = []
        for col in range(1, 8):
            price_base.append(float(clear_string(rows[1].find_all('td')[col].contents[0])))
            volume_base.append(float(clear_string(rows[2].find_all('td')[col].contents[0])))
            price_peak.append(float(clear_string(rows[4].find_all('td')[col].contents[0])))
            volume_peak.append(float(clear_string(rows[5].find_all('td')[col].contents[0])))
        df = pandas.DataFrame(data={'time_stamp': self.time_stamps,
                                    'price_base': price_base,
                                    'volume_base': volume_base,
                                    'price_peak': price_peak,
                                    'volume_peak': volume_peak})
        return df

    def extract_blocks(self, table):
        rows = table.find_all('tr')
        df_dict = {}
        for row in rows[1:-1]:
            block_name = block_dict[row.find('td', 'title').contents[0].strip()]
            block_values = []
            for col in range(1, 8):
                block_values.append((clear_string(row.find_all('td')[col].contents[0])))
            df_dict[block_name] = block_values
        df_dict['time_stamp'] = self.time_stamps
        df = pandas.DataFrame(df_dict)
        return df

    def extract_hours(self, table):
        rows = table.find_all('tr')
        price = []
        volume = []
        time_stamps = []
        for n_col in range(2, 9):
            date_num = n_col - 2
            date = self.time_stamps[date_num]
            hour = 0
            for n_row in range(1, len(rows), 2):
                time_stamps.append(date + datetime.timedelta(hours=hour))
                price.append((clear_string(rows[n_row].find_all('td')[n_col].contents[0])))
                volume.append((clear_string(rows[n_row+1].find_all('td')[n_col].contents[0])))
                hour += 1
        df = pandas.DataFrame(data={'time_stamp': time_stamps,
                                    'price': price,
                                    'volume': volume})
        return df



block_dict = {}
block_dict['Middle-Night (01-04)'] = 'middle_night'
block_dict['Middle Night (01-04)'] = 'middle_night'
block_dict['Early Morning (05-08)'] = 'early_morning'
block_dict['Late Morning (09-12)'] = 'late_morning'
block_dict['Early Afternoon (13-16)'] = 'early_afternoon'
block_dict['Rush Hour (17-20)'] = 'rush_hour'
block_dict['Off-Peak 2 (21-24)'] = 'off_peak2'
block_dict['Off Peak II (21-24)'] = 'off_peak2'
block_dict['Baseload (01-24)'] = 'baseload'
block_dict['Peakload (09-20)'] = 'peakload'
block_dict['Night (01-06)'] = 'night'
block_dict['Off-Peak 1 (01-08)'] = 'off_peak1'
block_dict['Off Peak I (01-08)'] = 'off_peak1'
block_dict['Business (09-16)'] = 'business'
block_dict['Business Hours (09-16)'] = 'business'
block_dict['Offpeak (01-08 and 21-24)'] = 'off_peak'
block_dict['Offpeak (01-08 & 21-24)'] = 'off_peak'
block_dict['Off-Peak (01-08 and 21-24)'] = 'off_peak'
block_dict['Off-Peak (01-08 & 21-24)'] = 'off_peak'
block_dict['Off Peak (01-08 and 21-24)'] = 'off_peak'
block_dict['Off Peak (01-08 & 21-24)'] = 'off_peak'
block_dict['Morning (07-10)'] = 'morning'
block_dict['High Noon (11-14)'] = 'high_noon'
block_dict['Afternoon (15-18)'] = 'afternoon'
block_dict['Evening (19-24)'] = 'evening'
block_dict['Sun Peak (11-16)'] = 'sun_peak'


def nat2none(value):
    if str(value) == 'NaT':
        value = 0
        return value
    else:
        return value

if __name__ == '__main__':
    price_today=[]
    price_tomorrow=[]
    prize = []
#    date = cet.localize(datetime.datetime(2018, 5, 9))
    date = cet.localize(datetime.datetime.now()+datetime.timedelta(days=1))
#    
#    page = DayAheadWebpage()
#    page.set_date(date)
#    page.download_page()
#    page.parse()
#    for row in  page.basepeak_de.iterrows():
#        if (row[1]['time_stamp'].date() == datetime.datetime.now().date()):
##            print(row[1]['price_base'])
#            bprice_today = float(row[1]['price_base'])
#        if (row[1]['time_stamp'].date() == (datetime.datetime.now()+datetime.timedelta(1)).date()):
#            bprice_tomorrow = row[1]['price_base']
#    
#    for row in page.hours_de.iterrows():
#        if row[1]['time_stamp'].date() == datetime.datetime.now().date():
#            price_today.append(float(row[1]['price']))
#            
#        if row[1]['time_stamp'].date() == (datetime.datetime.now()+datetime.timedelta(1)).date():
#            price_tomorrow.append(float(row[1]['price']))
#    import pylab as pl        
#    cost_buy = pl.append((pl.array(price_today)/1000.)+ bprice_today/1000.,(pl.array(price_tomorrow)/1000.)+ bprice_tomorrow/1000.)        
#    
#    print(cost_buy)
##    print(bprice_today, bprice_tomorrow) 
##    print(price_today, price_tomorrow)
##    print(page.df)
##    print(page.base1)
    
    page2 = IntradayWebpageDE()
    page2.set_date(date)
    page2.download_page()
    page2.parse()
    for row in page2.df.iterrows():
        if row[1]['time_stamp'].date() == date.now().date():
            
#        print(row[1]['time_stamp_end'].minute - row[1]['time_stamp'].minute)
            if (row[1]['time_stamp_end'].minute - row[1]['time_stamp'].minute) == 15 or (row[1]['time_stamp_end'].minute - row[1]['time_stamp'].minute)==-45:
                print(nat2none(row[1]['weighted_avg']))
#                prize.append(float(row[1]['weighted_avg']))
#    print(price, len(prize))
        
            
    






