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


idx = pd.IndexSlice

def process_covidtracking_data(data: pd.DataFrame, run_date: pd.Timestamp):
    """ Processes raw COVIDTracking data to be in a form for the GenerativeModel.
        In many cases, we need to correct data errors or obvious outliers."""
    data = data.rename(columns={"state": "region"})
    data["date"] = pd.to_datetime(data["date"], format="%Y%m%d")
    data = data.set_index(["region", "date"]).sort_index()
    data = data[["positive", "total", "death","deathIncrease"]]
    
    # Too little data or unreliable reporting in the data source.
    data = data.drop(["MP", "GU", "AS", "PR", "VI"])
    
    # On Jun 5 Covidtracking started counting probable cases too
    # which increases the amount by 5014.
    # https://covidtracking.com/screenshots/MI/MI-20200605-184320.png
    data.loc[idx["MI", pd.Timestamp("2020-06-05") :], "positive"] -= 5014
    
    # From CT: On June 19th, LDH removed 1666 duplicate and non resident cases
    # after implementing a new de-duplicaton process.
    data.loc[idx["LA", pd.Timestamp("2020-06-19") :], :] += 1666
    
    # Now work with daily counts
    data = data.diff().dropna().clip(0, None).sort_index()
    
    # Michigan missed 6/18 totals and lumped them into 6/19 so we've
    # divided the totals in two and equally distributed to both days.
    data.loc[idx["MI", pd.Timestamp("2020-06-18")], "total"] = 14871
    data.loc[idx["MI", pd.Timestamp("2020-06-19")], "total"] = 14871
    
    # Note that when we set total to zero, the model ignores that date. See
    # the likelihood function in GenerativeModel.build
    
    # Huge outlier in NJ causing sampling issues.
    data.loc[idx["NJ", pd.Timestamp("2020-05-11")], :] = 0
    # Same tests and positives, nulling out
    data.loc[idx["NJ", pd.Timestamp("2020-07-25")], :] = 0
    
    # Huge outlier in CA causing sampling issues.
    data.loc[idx["CA", pd.Timestamp("2020-04-22")], :] = 0
    
    # Huge outlier in CA causing sampling issues.
    # TODO: generally should handle when # tests == # positives and that
    # is not an indication of positive rate.
    data.loc[idx["SC", pd.Timestamp("2020-06-26")], :] = 0
    
    # Two days of no new data then lumped sum on third day with lack of new total tests
    data.loc[idx["OR", pd.Timestamp("2020-06-26") : pd.Timestamp("2020-06-28")], 'positive'] = 174
    data.loc[idx["OR", pd.Timestamp("2020-06-26") : pd.Timestamp("2020-06-28")], 'total'] = 3296
    
    #https://twitter.com/OHdeptofhealth/status/1278768987292209154
    data.loc[idx["OH", pd.Timestamp("2020-07-01")], :] = 0
    data.loc[idx["OH", pd.Timestamp("2020-07-09")], :] = 0
    
    # Nevada didn't report total tests this day
    data.loc[idx["NV", pd.Timestamp("2020-07-02")], :] = 0
    
    # A bunch of incorrect values for WA data so nulling them out.
    data.loc[idx["WA", pd.Timestamp("2020-06-05") : pd.Timestamp("2020-06-07")], :] = 0
    data.loc[idx["WA", pd.Timestamp("2020-06-20") : pd.Timestamp("2020-06-21")], :] = 0
    
    # AL reported tests == positives
    data.loc[idx["AL", pd.Timestamp("2020-07-09")], :] = 0
    
    # Low reported tests
    data.loc[idx["AR", pd.Timestamp("2020-07-10")], :] = 0
    
    # Positives == tests
    data.loc[idx["MS", pd.Timestamp("2020-07-12")], :] = 0
    
    # Positive == Tests; lumpy reporting for CT
    data.loc[idx["CT", pd.Timestamp("2020-07-17")], :] = 0
    data.loc[idx["CT", pd.Timestamp("2020-07-21")], :] = 0
    
    data.loc[idx["DC", pd.Timestamp("2020-08-04")], :] = 0
    
    # Outlier dates in PA
    data.loc[
        idx[
            "PA",
            [
                pd.Timestamp("2020-06-03"),
                pd.Timestamp("2020-04-21"),
                pd.Timestamp("2020-05-20"),
            ],
        ],
        :,
    ] = 0
    
    data.loc[idx["HI", pd.Timestamp("2020-08-07")], :] = 0
    data.loc[idx["TX", pd.Timestamp("2020-08-08")], :] = 0
    data.loc[idx["TX", pd.Timestamp("2020-08-11")], :] = 0
    
    data.loc[idx["DE", pd.Timestamp("2020-08-14")], :] = 0
    
    # Zero out any rows where positive tests equal or exceed total reported tests
    # Do not act on Wyoming as they report positive==total most days
    filtering_date = pd.Timestamp('2020-07-27')
    zero_filter = (data.positive >= data.total) & \
        (data.index.get_level_values('date') >= filtering_date) & \
        (~data.index.get_level_values('region').isin(['WY']))
    data.loc[zero_filter, :] = 0
    
    # At the real time of `run_date`, the data for `run_date` is not yet available!
    # Cutting it away is important for backtesting!
    return data.loc[idx[:, :(run_date - pd.DateOffset(1))], ["positive", "total", "death","deathIncrease"]]

def roundup(x):
    return int(math.ceil(x /100.0)) * 100

run_date=pd.Timestamp.today()-pd.Timedelta(days=1)

#df = get_and_process_covidtracking_data(run_date=pd.Timestamp.today()-pd.Timedelta(days=1))
rawData=get_raw_covidtracking_data()

data = process_covidtracking_data(rawData,run_date)

FIGUREPATH="../jlc42.github.io/figs/"

os.system('mkdir '+FIGUREPATH+'casesNTests')
os.system('mkdir '+FIGUREPATH+'percentViralTestsPositive')
os.system('mkdir '+FIGUREPATH+'dailyDeaths')
os.system('mkdir '+FIGUREPATH+'estimatedInfections')

###Generate figures for each State: 
regionList=data.index.get_level_values(0).drop_duplicates()
for stateName in regionList:
    print("Generating Figures for "+stateName)
    state=data.loc[stateName]
    
    #Calculate Values of Use for later:
    state['dailyNewCases-7DayAvg'] = state["positive"].rolling(window=7).mean()
    state['dailyNewTests-7DayAvg'] = state["total"].rolling(window=7).mean()
    state['percentVTPositive'] = state['dailyNewCases-7DayAvg']/state['dailyNewTests-7DayAvg']
    state['dailyDeaths-7DayAvg'] = state['deathIncrease'].rolling(window=7).mean()
    state['infFromCasesYYGEst'] = state['dailyNewCases-7DayAvg']*(16*(pow(state['percentVTPositive'],0.5))+2.5)

    
    #CasesAndTests
    maxCases=state['dailyNewCases-7DayAvg'].max()*10
    maxTests=state['dailyNewTests-7DayAvg'].max()
    axis2Max=roundup(max(maxCases,maxTests))
    axis1Max=axis2Max/10

    fig, ax1 = plt.subplots()
    color = 'tab:orange'
    plt.title(stateName+': Daily Cases and Tests')
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Daily Cases', color=color)
    ax1.plot(state['dailyNewCases-7DayAvg'], color=color)
    ax1.tick_params(axis='y', labelcolor=color)
    ax1.set_ylim(0,axis1Max)
    ax1.grid(True)
    plt.scatter(state.index,state['positive'], color=color, s=1, alpha=0.5)

    ax2 = ax1.twinx()  # instantiate a second axes that shares the same x-axis
    color = 'tab:blue'
    ax2.set_ylabel('Daily Tests', color=color)  # we already handled the x-label with ax1
    ax2.plot(state['dailyNewTests-7DayAvg'], color=color)
    ax2.tick_params(axis='y', labelcolor=color)
    ax2.set_ylim(0,axis2Max)

    fig.tight_layout(pad=2)  # otherwise the right y-label is slightly clipped
    plt.scatter(state.index,state['total'], color=color, s=1, alpha=0.5)
    
    plt.savefig(FIGUREPATH + 'casesNTests/' + stateName +'-DailyCasesAndTests')
    plt.close('all')

    #%Positive
    color = 'tab:blue'
    ax = state['percentVTPositive'].plot(color=color)
    ax.yaxis.set_major_formatter(PercentFormatter(xmax=1,decimals=0))
    ax.grid(True)

    plt.title(stateName+': Percent Viral Tests Positive')
    plt.xlabel('Date')
    plt.ylabel('% of Tests Positive', color=color)
    plt.ylim(0,.3)
    plt.tight_layout(pad=2)

    plt.savefig(FIGUREPATH + 'percentViralTestsPositive/' + stateName +'-PercentViralTestsPositive')
    plt.close('all')

    #Daily Deaths
    color = 'tab:red'
    yAxisMax=state['dailyDeaths-7DayAvg'].max()
    yAxisMax=math.ceil(yAxisMax*1.3)



    ax = state['dailyDeaths-7DayAvg'].plot(color=color)
    plt.scatter(state.index,state['deathIncrease'], color=color, s=1, alpha=0.5)
    ax.grid(True)
    ax.set_ylim(0,yAxisMax)
    
    plt.title(stateName+': Daily Deaths')
    plt.xlabel('Date')
    plt.ylabel('Daily Deaths', color=color)
    plt.tight_layout(pad=2)
    
    plt.savefig(FIGUREPATH + 'dailyDeaths/' + stateName +'-DailyDeaths')
    plt.close('all')


    #Infections Estimates:
    casesColor = 'tab:blue'
    yygColor = 'tab:green'
    plt.title(stateName+': Estimated Infections')
    plt.xlabel('Date')
    plt.ylabel('Daily Cases')
    plt.scatter(state.index,state['positive'], color=casesColor, s=1, alpha=0.5)
    plt.plot(state.index,state['dailyNewCases-7DayAvg'], color=casesColor, label = 'confirmed cases')
    #plt.scatter(state.index,state['dailyNewCases-7DayAvg'], color=casesColor)
    plt.plot(state.index,state['infFromCasesYYGEst'], color=yygColor, label = 'estimated infections (from cases)')
    plt.grid(True)
    plt.legend()
    fileName=FIGUREPATH + 'estimatedInfections/' + stateName +'-EstimatedInfections'
    plt.savefig(fileName)
    plt.close('all')
    f=open(fileName+'.txt', "w")
    description = """The true number of infections is far larger than the number of officially reported cases. One way to estimate the true number of infections from reported cases and the percent of tests that are positive was proposed by Youyang Gu: true-new-daily-infections = daily-confirmed-cases * (16 * (positivity-rate)^(0.5) + 2.5). (see: https://covid19-projections.com/estimating-true-infections/)"""
    f.write(description)
    f.close()
    plt.close('all')


#matplotlib filling and shading regions https://matplotlib.org/3.1.1/gallery/lines_bars_and_markers/fill_between_demo.html












"""

nm=data.loc['NM']
nm['DailyNewCases-7DayAvg'] = nm.iloc[:,0].rolling(window=7).mean()
nm['DailyNewTests-7DayAvg'] = nm.iloc[:,1].rolling(window=7).mean()
fig, ax1 = plt.subplots()
color = 'tab:orange'
ax1.set_xlabel('Date')
ax1.set_ylabel('Daily Cases', color=color)
ax1.plot(nm['DailyNewCases-7DayAvg'], color=color)
ax1.tick_params(axis='y', labelcolor=color)
ax1.set_ylim(0,1200)
plt.scatter(nm.index,nm['positive'], color=color, s=1, alpha=0.5)


ax2 = ax1.twinx()  # instantiate a second axes that shares the same x-axis

color = 'tab:blue'
ax2.set_ylabel('Daily Tests', color=color)  # we already handled the x-label with ax1
ax2.plot(nm['DailyNewTests-7DayAvg'], color=color)
ax2.tick_params(axis='y', labelcolor=color)
ax2.set_ylim(0,12000)

fig.tight_layout(pad=1.5)  # otherwise the right y-label is slightly clipped
plt.title('NM: Daily Cases and Tests')
plt.scatter(nm.index,nm['total'], color=color, s=1, alpha=0.5)
plt.savefig('NM: Daily Cases and Tests')
plt.show()

"""


