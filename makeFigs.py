#!/usr/bin/python3

#import pymc3 as pm
import pandas as pd
import numpy as np
#import arviz as az
from matplotlib import pyplot as plt
from matplotlib.ticker import PercentFormatter
#from covid.models.generative import GenerativeModel
#from covid.data import summarize_inference_data

from rt_live_covid_model.covid.data import get_and_process_covidtracking_data 
from rt_live_covid_model.covid.data import summarize_inference_data
from rt_live_covid_model.covid.data_us import get_raw_covidtracking_data
import os
import math
import sys
idx = pd.IndexSlice



arglen=len(sys.argv)

if arglen>1:
    regionOption = sys.argv[1]
else:
    regionOptios == 'ALL'

if arglen>2:
    option = sys.argv[2]
else:
    option = '-limited'

regionOption = regionOption.upper()
print("running with region option "+regionOption)






if option == '-a':
    includeRT=True
    print("including rt runs")
else:
    print("not including rt runs")
    includeRT=False


def get_raw_UScovidtracking_data():
    """ Gets the current daily CSV from COVIDTracking for the US as a whole"""
    url = "https://covidtracking.com/api/v1/us/daily.csv"
    #url = "https://covidtracking.com/api/v1/states/daily.csv"
    data = pd.read_csv(url)
    return data


def processUScovidtracking_data(data: pd.DataFrame, run_date: pd.Timestamp):
    """ Processes raw COVIDTracking data to be in a form for the GenerativeModel.
        In many cases, we need to correct data errors or obvious outliers."""
    data["region"]='USA'
    #data = data.rename(columns={"state": "region"})
    data["date"] = pd.to_datetime(data["date"], format="%Y%m%d")
    data = data.set_index(["region", "date"]).sort_index()
    data = data[["positive", "total","death","deathIncrease"]]
    data = data.rename(columns={"positive": "casesCumulative"})
    data = data.rename(columns={"total": "testsCumulative"})
    data = data.rename(columns={"death": "deathsCumulative"})


    # Now work with daily counts
    #data = data.diff().dropna().clip(0, None).sort_index()
    data["casesDaily"]=data["casesCumulative"].diff().dropna().clip(0,None)
    data["testsDaily"]=data["testsCumulative"].diff().dropna().clip(0,None)
    data = data.rename(columns={"deathIncrease": "deathsDaily"})

    #return data.loc[idx[:, :(run_date - pd.DateOffset(1))], ["positive", "total", "death","deathIncrease"]]
    return data








def process_covidtracking_data(data: pd.DataFrame, run_date: pd.Timestamp):
    """ Processes raw COVIDTracking data to be in a form for the GenerativeModel.
        In many cases, we need to correct data errors or obvious outliers."""
    data = data.rename(columns={"state": "region"})
    data["date"] = pd.to_datetime(data["date"], format="%Y%m%d")
    data = data.set_index(["region", "date"]).sort_index()
    data = data[["positive", "total", "death","deathIncrease"]]
    data = data.rename(columns={"positive": "casesCumulative"})
    data = data.rename(columns={"total": "testsCumulative"})
    data = data.rename(columns={"death": "deathsCumulative"})
    data = data.sort_index()

    # Too little data or unreliable reporting in the data source.
    data = data.drop(["MP", "GU", "AS", "PR", "VI"])

    # On Jun 5 Covidtracking started counting probable cases too
    # which increases the amount by 5014.
    # https://covidtracking.com/screenshots/MI/MI-20200605-184320.png
    data.loc[idx["MI", pd.Timestamp("2020-06-05") :], "casesCumulative"] -= 5014

    # From CT: On June 19th, LDH removed 1666 duplicate and non resident cases
    # after implementing a new de-duplicaton process.
    data.loc[idx["LA", pd.Timestamp("2020-06-19") :], "casesCumulative"] += 1666

    # Now work with daily counts
    data["casesDaily"]=data["casesCumulative"].diff().dropna().clip(0,None)
    data["testsDaily"]=data["testsCumulative"].diff().dropna().clip(0,None)
    data = data.rename(columns={"deathIncrease": "deathsDaily"})




    #data = data.diff().dropna().clip(0, None).sort_index()
    
    # Michigan missed 6/18 totals and lumped them into 6/19 so we've
    # divided the totals in two and equally distributed to both days.
    data.loc[idx["MI", pd.Timestamp("2020-06-18")], "testsDaily"] = 14871
    data.loc[idx["MI", pd.Timestamp("2020-06-19")], "testsDaily"] = 14871
    
    # Two days of no new data then lumped sum on third day with lack of new total tests
    data.loc[idx["OR", pd.Timestamp("2020-06-26") : pd.Timestamp("2020-06-28")], 'casesDaily'] = 174
    data.loc[idx["OR", pd.Timestamp("2020-06-26") : pd.Timestamp("2020-06-28")], 'testsDaily'] = 3296
    
    # At the real time of `run_date`, the data for `run_date` is not yet available!
    # Cutting it away is important for backtesting!
    return data
    #return data.loc[idx[:, :(run_date - pd.DateOffset(1))], ["positive", "total", "death","deathIncrease"]]

def roundup(x):
    return int(math.ceil(x /100.0)) * 100

run_date=pd.Timestamp.today()-pd.Timedelta(days=1)

#df = get_and_process_covidtracking_data(run_date=pd.Timestamp.today()-pd.Timedelta(days=1))
print("getting data")
rawStateData=get_raw_covidtracking_data()
dataState = process_covidtracking_data(rawStateData,run_date)
rawUSData = get_raw_UScovidtracking_data()
dataUS = processUScovidtracking_data(rawUSData,run_date=pd.Timestamp.today()-pd.Timedelta(days=1))
data=dataUS.append(dataState)



dataRegionList=data.index.get_level_values(0).drop_duplicates()
#Add Population Data to the Data Frame Data. 
popDf=pd.read_csv('COVID_Data/regionPopulation.csv',index_col='region')
for region in dataRegionList:
    data.loc[region,"population"]=popDf.loc[region,"population"]




#Calculate Other Parameters of Interest
for regionName in dataRegionList:
    #region['dailyNewCases-7DayAvg'] = region["casesDaily"].rolling(window=7).mean()
    data.loc[idx[regionName, :], 'dailyNewCases-7DayAvg'] = data.loc[idx[regionName, :], "casesDaily"].rolling(window=7).mean()
    #region['dailyNewTests-7DayAvg'] = region["testsDaily"].rolling(window=7).mean()
    data.loc[idx[regionName, :], 'dailyNewTests-7DayAvg'] = data.loc[idx[regionName, :],"testsDaily"].rolling(window=7).mean()
    #region['percentVTPositive'] = region['dailyNewCases-7DayAvg']/region['dailyNewTests-7DayAvg']
    data.loc[idx[regionName, :], 'percentVTPositive'] = data.loc[idx[regionName, :],'dailyNewCases-7DayAvg']/data.loc[idx[regionName, :], 'dailyNewTests-7DayAvg']
    #region['dailyDeaths-7DayAvg'] = region['deathsDaily'].rolling(window=7).mean()
    data.loc[idx[regionName, :], 'dailyDeaths-7DayAvg'] = data.loc[idx[regionName, :], 'deathsDaily'].rolling(window=7).mean()
    #region['infFromCasesYYGEst'] = region['dailyNewCases-7DayAvg']*(16*(pow(region['percentVTPositive'],0.5))+2.5)
    data.loc[idx[regionName, :], 'infFromCasesYYGEst'] = data.loc[idx[regionName, :], 'dailyNewCases-7DayAvg']*(16*(pow(data.loc[idx[regionName,:], 'percentVTPositive'],0.5))+2.5)











FIGUREPATH="../jlc42.github.io/figs/"

os.system('mkdir '+FIGUREPATH+'casesNTests')
os.system('mkdir '+FIGUREPATH+'percentViralTestsPositive')
os.system('mkdir '+FIGUREPATH+'dailyDeaths')
os.system('mkdir '+FIGUREPATH+'estimatedInfections')

###Generate figures for each State:
casesColor = 'tab:orange'
yygColor = 'tab:green'
deathsColor = 'tab:red'
testsColor = 'tab:blue'



if regionOption=='ALL':
    regionList=dataRegionList
elif regionOption == 'ALLUS':
    regionList=['USA', 'AK', 'AL', 'AR', 'AZ', 'CA', 'CO', 'CT', 'DC', 'DE', 'FL', 'GA',
       'HI', 'IA', 'ID', 'IL', 'IN', 'KS', 'KY', 'LA', 'MA', 'MD', 'ME', 'MI',
       'MN', 'MO', 'MS', 'MT', 'NC', 'ND', 'NE', 'NH', 'NJ', 'NM', 'NV', 'NY',
       'OH', 'OK', 'OR', 'PA', 'RI', 'SC', 'SD', 'TN', 'TX', 'UT', 'VA', 'VT',
       'WA', 'WI', 'WV', 'WY']
else: 
    regionList=[regionOption]



for regionName in regionList:
    #print("should I run for "+region)
    print("Generating Figures for "+regionName)
    if not (regionName in dataRegionList):
        print("don't have data for region "+regionName)
        continue

    state=data.loc[regionName].copy(deep=True)
    
    #Calculate Values of Use for later:
    state['dailyNewCases-7DayAvg'] = state["casesDaily"].rolling(window=7).mean()
    state['dailyNewTests-7DayAvg'] = state["testsDaily"].rolling(window=7).mean()
    state['percentVTPositive'] = state['dailyNewCases-7DayAvg']/state['dailyNewTests-7DayAvg']
    state['dailyDeaths-7DayAvg'] = state['deathsDaily'].rolling(window=7).mean()
    state['infFromCasesYYGEst'] = state['dailyNewCases-7DayAvg']*(16*(pow(state['percentVTPositive'],0.5))+2.5)

    
    #CasesAndTests
    maxCases=state['dailyNewCases-7DayAvg'].max()*10
    maxTests=state['dailyNewTests-7DayAvg'].max()
    axis2Max=roundup(max(maxCases,maxTests))
    axis1Max=axis2Max/10

    fig, ax1 = plt.subplots()
    plt.title(regionName+': Daily Cases and Tests')
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Daily Cases', color=casesColor)
    ax1.plot(state['dailyNewCases-7DayAvg'], color=casesColor)
    ax1.tick_params(axis='y', labelcolor=casesColor)
    ax1.set_ylim(0,axis1Max)
    ax1.grid(True)
    plt.scatter(state.index,state['casesDaily'], color=casesColor, s=1, alpha=0.5)

    ax2 = ax1.twinx()  # instantiate a second axes that shares the same x-axis
    color = testsColor
    ax2.set_ylabel('Daily Tests', color=color)  # we already handled the x-label with ax1
    ax2.plot(state['dailyNewTests-7DayAvg'], color=color)
    ax2.tick_params(axis='y', labelcolor=color)
    ax2.set_ylim(0,axis2Max)

    fig.tight_layout(pad=2)  # otherwise the right y-label is slightly clipped
    plt.scatter(state.index,state['testsDaily'], color=color, s=1, alpha=0.5)
    
    plt.savefig(FIGUREPATH + 'casesNTests/' + regionName +'-DailyCasesAndTests')
    plt.close('all')

    #%Positive
    color = 'tab:blue'
    ax = state['percentVTPositive'].plot(color=color)
    ax.yaxis.set_major_formatter(PercentFormatter(xmax=1,decimals=0))
    ax.grid(True)

    plt.title(regionName+': Percent Viral Tests Positive')
    plt.xlabel('Date')
    plt.ylabel('% of Tests Positive', color=color)
    plt.ylim(0,.3)
    plt.tight_layout(pad=2)

    plt.savefig(FIGUREPATH + 'percentViralTestsPositive/' + regionName +'-PercentViralTestsPositive')
    plt.close('all')


    #################################
    #Daily Deaths
    #################################
    fileName=FIGUREPATH+'dailyDeaths/' + regionName +'-DailyDeaths'
    color = 'tab:red'
    yAxisMax=state['dailyDeaths-7DayAvg'].max()
    yAxisMax=math.ceil(yAxisMax*1.3)
    

    ax = state['dailyDeaths-7DayAvg'].plot(color=color)
    plt.scatter(state.index,state['deathsDaily'], color=color, s=1, alpha=0.5)
    ax.grid(True)
    ax.set_ylim(0,yAxisMax)
    
    plt.title(regionName+': Daily Deaths')
    plt.xlabel('Date')
    plt.ylabel('Daily Deaths', color=color)
    plt.tight_layout(pad=2)
    
    plt.savefig(fileName)
    f=open(fileName+'.txt', "w")
    description = "The number of daily deaths in "+regionName+"."
    f.write(description)
    f.close()

    plt.close('all')


    #################################
    #Infections Estimates:
    #################################
    plt.title(regionName+': Estimated Infections')
    plt.xlabel('Date')
    plt.ylabel('Daily Cases')
    plt.scatter(state.index,state['casesDaily'], color=casesColor, s=1, alpha=0.5)
    plt.plot(state.index,state['dailyNewCases-7DayAvg'], color=casesColor, label = 'confirmed cases')
    #plt.scatter(state.index,state['dailyNewCases-7DayAvg'], color=casesColor)
    plt.plot(state.index,state['infFromCasesYYGEst'], color=yygColor, label = 'estimated infections (from cases)')
    plt.grid(True)
    plt.legend()
    fileName=FIGUREPATH + 'estimatedInfections/' + regionName +'-EstimatedInfections'
    plt.savefig(fileName)
    plt.close('all')
    f=open(fileName+'.txt', "w")
    description = """The true number of infections is far larger than the number of officially reported cases. One way to estimate the true number of infections from reported cases and the percent of tests that are positive was proposed by Youyang Gu: true-new-daily-infections = daily-confirmed-cases * (16 * (positivity-rate)^(0.5) + 2.5). (see: https://covid19-projections.com/estimating-true-infections/)"""
    f.write(description)
    f.close()
    plt.close('all')


    #RT.LIVE code...
    if includeRT:
        RTPATH=FIGUREPATH+'rt_live_code_figs/'
        print("running rt.live code on region "+regionName+" and path "+RTPATH)

        os.system('./runRTLive.py '+regionName+' '+ RTPATH) 



#Now I need to gather all the csv into a single file:
masterRt=pd.DataFrame(columns=['Lower 80','Mean','Upper 80'])
for fileName in os.listdir(path='../jlc42.github.io/figs/rt_live_code_figs/'):
    if (fileName != 'masterRt.csv') and ('.csv' in fileName):
        new=pd.read_csv('../jlc42.github.io/figs/rt_live_code_figs/'+fileName, header=None)
        new=new.rename(columns={0:'Lower 80',1:'Mean',2:'Upper 80'})
        newName=fileName.split('_')[0]
        new=new.rename(index={0:newName})
        masterRt=masterRt.append(new)

masterRt=masterRt.sort_index()
masterRt.to_csv('../jlc42.github.io/figs/rt_live_code_figs/masterRt.csv')



#matplotlib filling and shading regions https://matplotlib.org/3.1.1/gallery/lines_bars_and_markers/fill_between_demo.html











