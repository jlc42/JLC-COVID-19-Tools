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
import dataHandler as dh
idx = pd.IndexSlice


FIGUREPATH="../jlc42.github.io/figs/"



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



def roundup(x):
    return int(math.ceil(x /100.0)) * 100

run_date=pd.Timestamp.today()-pd.Timedelta(days=1)

#df = get_and_process_covidtracking_data(run_date=pd.Timestamp.today()-pd.Timedelta(days=1))
#print("getting data")
data=dh.getMasterCovidDataFromOnlineSources()

dataRegionList=data.index.get_level_values(0).drop_duplicates()


os.system('mkdir '+FIGUREPATH+'casesNTests')
os.system('mkdir '+FIGUREPATH+'percentViralTestsPositive')
os.system('mkdir '+FIGUREPATH+'dailyDeaths')
os.system('mkdir '+FIGUREPATH+'estimatedInfections')
os.system('mkdir '+FIGUREPATH+'PercentActive')
os.system('mkdir '+FIGUREPATH+'PercentInfected')

###Generate figures for each State:
casesColor = 'tab:orange'
yygColor = 'xkcd:aqua green'
deathsColor = 'tab:red'
testsColor = 'tab:blue'
recoveredColor = 'tab:green'



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
    #state['dailyNewCases-7DayAvg'] = state["casesDaily"].rolling(window=7).mean()
    #state['dailyNewTests-7DayAvg'] = state["testsDaily"].rolling(window=7).mean()
    #state['percentVTPositive'] = state['dailyNewCases-7DayAvg']/state['dailyNewTests-7DayAvg']
    #state['dailyDeaths-7DayAvg'] = state['deathsDaily'].rolling(window=7).mean()
    #state['infFromCasesYYGEst'] = state['dailyNewCases-7DayAvg']*(16*(pow(state['percentVTPositive'],0.5))+2.5)

    
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
    plt.ylabel('Daily Cases or Infections')
    plt.scatter(state.index,state['casesDaily'], color=casesColor, s=1, alpha=0.5)
    plt.plot(state.index,state['dailyNewCases-7DayAvg'], color=casesColor, label = 'Reported Daily Confirmed Cases')
    #plt.scatter(state.index,state['dailyNewCases-7DayAvg'], color=casesColor)
    plt.plot(state.index,state['infFromCasesYYGEst'], color=yygColor, label = 'Estimated Actual Daily Infections')
    plt.grid(True)
    plt.legend()
    fileName=FIGUREPATH + 'estimatedInfections/' + regionName +'-EstimatedInfections'
    plt.savefig(fileName)
    plt.close('all')
    f=open(fileName+'.txt', "w")
    description = """The true number of infections is far larger than the number of officially reported cases. One way to estimate the true number of infections from reported cases and the percent of tests that are positive was proposed by Youyang Gu: true-new-daily-infections = daily-confirmed-cases * (16 * (positivity-rate)^(0.5) + 2.5). (see: https://covid19-projections.com/estimating-true-infections/)"""
    f.write(description)
    f.close()

    #####################################
    #ACTIVE CASES AND INFECTION ESTIMATES
    #####################################
    FIGURETYPENAME='PercentActive'
    fileName=FIGUREPATH + FIGURETYPENAME + '/' + regionName +'-'+FIGURETYPENAME
    fig, ax1 = plt.subplots()
    plt.title(regionName+': Percent Active')
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Percent Active')
    ax1.plot(data.loc[regionName]['activeCasesPercent'], color=casesColor, label = 'Active Reported Cases')
    ax1.plot(data.loc[regionName]['activeInfectionsPercent'], color=yygColor, label = 'Active Actual Infections (Estimated)')
    #plt.plot(masterData.loc[regionName]['cumulativeInfectionsFromCasesYYG'], color=yygColor, label = 'Estimated Actual Cumulative Infections')
    #plt.plot(masterData.loc[regionName]['testsCumulative'], color=testsColor, label = 'Cumulative Tests')
    #plt.scatter(state.index,state['dailyNewCases-7DayAvg'], color=casesColor)
    ax1.yaxis.set_major_formatter(PercentFormatter(1))
    ax1.set_ylim(bottom=0)
    plt.grid(True)
    plt.legend()
    
    plt.savefig(fileName)
    plt.close('all')
    f=open(fileName+'.txt', "w")
    description = """The true number of infections is far larger than the number of officially reported cases. Using the population size, estimated recoveries, and estimated infections it's possible to compute an estimate of the population that are actively infected in a given location. This is a useful estimate of individual risk, because it gives you an idea of how likely it is that you will interact with a person who is actively contagious. If 2% of the population in your region are actively infected, then in a randomly chosen group of 100 people, on average, 2 of them will be contageous."""
    f.write(description)
    f.close()
    
    #Make CSV for color coding map
    f=open(fileName+'.csv', "w")
    percentInfectedToday=data.loc[regionName]['activeInfectionsPercent'].loc[run_date.strftime("%Y-%m-%d")]
    f.write(str(percentInfectedToday))
    f.close()
    


    #####################################
    #Cumulative Percent Cases and INFECTION ESTIMATES
    #####################################
    FIGURETYPENAME='PercentInfected'
    fileName=FIGUREPATH + FIGURETYPENAME + '/' + regionName +'-'+FIGURETYPENAME
    fig, ax1 = plt.subplots()
    plt.title(regionName+': Cumulative Percent of the Population')
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Percent of the Population')
    ax1.plot(data.loc[regionName]['cumulativeCasesPercent'], color=casesColor, label = 'Percent Reported Confirmed Cases')
    ax1.plot(data.loc[regionName]['cumulativeInfectedPercent'], color=yygColor, label = 'Percent Actually Infected (Estimated)')
    ax1.plot(data.loc[regionName]['cumulativeRecoveredInfectionsPercent'], color=recoveredColor, label = 'Percent Actually Recovered (Estimated)') 
    ax1.yaxis.set_major_formatter(PercentFormatter(1))
    ax1.set_ylim(bottom=0)
    plt.grid(True)
    plt.legend()
    
    plt.savefig(fileName)
    plt.close('all')
    f=open(fileName+'.txt', "w")
    description = """The true number of infections is far larger than the number of officially reported cases. One way to estimate the true number of infections from reported cases and the percent of tests that are positive was proposed by Youyang Gu: true-new-daily-infections = daily-confirmed-cases * (16 * (positivity-rate)^(0.5) + 2.5). (see: https://covid19-projections.com/estimating-true-infections/). The cumulative percent of the population that has been infected so far is an important first step towards extimating the fraction of the population that will be immune in a given location.""" 
    f.write(description)
    f.close()
 






    #RT.LIVE code...
    if includeRT:
        RTPATH=FIGUREPATH+'rt_live_code_figs/'
        print("running rt.live code on region "+regionName+" and path "+RTPATH)

        os.system('./runRTLive.py '+regionName+' '+ RTPATH) 



#Now I need to gather all the rt csv files into a single file:
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

#Now I need to gather all the percent Infected csv files into a single file:
masterPercentInfected=pd.DataFrame(columns=['Mean'])
activePath=FIGUREPATH+'PercentActive'
for fileName in os.listdir(path=activePath):
    if (fileName != 'masterPercentInfected.csv') and ('.csv' in fileName):
        new=pd.read_csv(activePath + '/' + fileName, header=None)
        new=new.rename(columns={0:'Mean'})
        newName=fileName.split('_')[0]
        new=new.rename(index={0:newName})
        masterPercentInfected=masterPercentInfected.append(new)

masterPercentInfected=masterPercentInfected.sort_index()
masterPercentInfected.to_csv(activePath + '/masterPercentInfected.csv')


#matplotlib filling and shading regions https://matplotlib.org/3.1.1/gallery/lines_bars_and_markers/fill_between_demo.html











