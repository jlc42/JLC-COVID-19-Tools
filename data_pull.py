#!/usr/bin/env python3

import os
from datetime import date


today = date.today()
d1 = today.strftime("%Y-%m-%d")
print('getting source data for %s'%today)

os.system('mkdir '+d1)

print('Getting WHO Data')
os.system('wget -P'+d1+' -p --convert-links https://covid19.who.int/WHO-COVID-19-global-data.csv')

print('Getting JHU Data')
if(os.path.exists('../JHUCovid')):
    print('pulling ../JHUCovid')
    os.system('git -C ../JHUCovid pull') 
else:
    print('../JHUCovid does not exist... cloning repo')
    os.system('git clone https://github.com/CSSEGISandData/COVID-19.git ../JHUCovid')

print('Getting Covid-Tracking Data:')
os.system('wget -P'+d1+' -p --convert-links https://covidtracking.com/api/v1/us/daily.csv')
os.system('wget -P'+d1+' -p --convert-links https://covidtracking.com/api/v1/states/daily.csv')

print('Getting rt.live results:')
os.system('wget -P'+d1+' -p --convert-links https://d14wlfuexuxgcm.cloudfront.net/covid/rt.csv')


print('Getting Georgia Data:')
os.system('mkdir '+d1+'/GA')
os.system('wget -P'+d1+'/GA/ -p --convert-links https://ga-covid19.ondemand.sas.com/')

print('Getting Texas Data:')
os.system('wget -P'+d1+' -p --convert-links https://dshs.texas.gov/coronavirus/TexasCOVID19CaseCountData.xlsx')
#Need to compile this daily to make sure I get the positive antigen and serology for that day. 
#There is more data we coud get from Texas, go here to look and see if there is anything interesting: https://txdshs.maps.arcgis.com/apps/opsdashboard/index.html#/ed483ecd702b4298ab01e8b9cafc8b83

print('Getting WorldOMeter Data:')
os.system('wget -P'+d1+' -p --convert-links https://www.worldometers.info/coronavirus/')

#TODO Get "Our World in Data" information as well. Ideas to do this, https://srome.github.io/Parsing-HTML-Tables-in-Python-with-BeautifulSoup-and-pandas/
#TOSO parse georgia, and worldometer into csv files somehow. 


