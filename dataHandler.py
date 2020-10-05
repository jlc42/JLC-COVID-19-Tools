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
    data['total'] = data['positive']+data['negative']
    data = data.set_index(["region", "date"]).sort_index()
    data['total']=data['positive']+data['negative']
    data = data[["positive", "total","death","deathIncrease"]]
    data = data.rename(columns={"positive": "cumulativeCases"})
    data = data.rename(columns={"total": "testsCumulative"})
    data = data.rename(columns={"death": "deathsCumulative"})


    # Now work with daily counts
    #data = data.diff().dropna().clip(0, None).sort_index()
    data["casesDaily"]=data["cumulativeCases"].diff().dropna().clip(0,None)
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
    data = data.rename(columns={"positive": "cumulativeCases"})
    data = data.rename(columns={"total": "testsCumulative"})
    data = data.rename(columns={"death": "deathsCumulative"})
    data = data.sort_index()

    # Too little data or unreliable reporting in the data source.
    data = data.drop(["MP", "GU", "AS", "PR", "VI"])

    # On Jun 5 Covidtracking started counting probable cases too
    # which increases the amount by 5014.
    # https://covidtracking.com/screenshots/MI/MI-20200605-184320.png
    data.loc[idx["MI", pd.Timestamp("2020-06-05") :], "cumulativeCases"] -= 5014

    # From CT: On June 19th, LDH removed 1666 duplicate and non resident cases
    # after implementing a new de-duplicaton process.
    data.loc[idx["LA", pd.Timestamp("2020-06-19") :], "cumulativeCases"] += 1666

    # Now work with daily counts
    data["casesDaily"]=data["cumulativeCases"].diff().dropna().clip(0,None)
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



def getMasterCovidDataFromOnlineSources():
    run_date=pd.Timestamp.today()-pd.Timedelta(days=1)
    #df = get_and_process_covidtracking_data(run_date=pd.Timestamp.today()-pd.Timedelta(days=1))
    print("getting data")
    rawStateData=get_raw_covidtracking_data()
    dataState = process_covidtracking_data(rawStateData,run_date)
    rawUSData = get_raw_UScovidtracking_data()
    dataUS = processUScovidtracking_data(rawUSData,run_date=pd.Timestamp.today()-pd.Timedelta(days=1))
    data=dataUS.append(dataState)

    dataRegionList=data.index.get_level_values(0).drop_duplicates()
    
    #Add Population Data to the Master Data Frame:
    popDf=pd.read_csv('COVID_Data/regionPopulation.csv',index_col='region')
    for region in dataRegionList:
        data.loc[region,"population"]=int(popDf.loc[region,"population"].replace(',',''))

    #Calculate Other Parameters of Interest
    for regionName in dataRegionList:
        #dailyCases
        data.loc[idx[regionName, :], 'dailyNewCases-7DayAvg'] = data.loc[idx[regionName, :], "casesDaily"].rolling(window=7).mean()
        #dailyTests
        data.loc[idx[regionName, :], 'dailyNewTests-7DayAvg'] = data.loc[idx[regionName, :],"testsDaily"].rolling(window=7).mean()
        #percent of Daily Tests Positive
        data.loc[idx[regionName, :], 'percentVTPositive'] = data.loc[idx[regionName, :],'dailyNewCases-7DayAvg']/data.loc[idx[regionName, :], 'dailyNewTests-7DayAvg']
        #daily Deaths
        data.loc[idx[regionName, :], 'dailyDeaths-7DayAvg'] = data.loc[idx[regionName, :], 'deathsDaily'].rolling(window=7).mean()
        #daily Infections
        data.loc[idx[regionName, :], 'infFromCasesYYGEst'] = data.loc[idx[regionName, :], 'dailyNewCases-7DayAvg']*(16*(pow(data.loc[idx[regionName,:], 'percentVTPositive'],0.5))+2.5)
        #cumulative Cases
        """Already exists in data.loc[idx[regionName, :], "cumulativeCases"]"""
        data.loc[idx[regionName, :], 'cumulativeCasesPercent'] = data.loc[idx[regionName, :], 'cumulativeCases'] / data.loc[idx[regionName, :], 'population']
        #cumulative Infections
        data.loc[idx[regionName, :], 'cumulativeInfectionsFromCasesYYG'] = data.loc[idx[regionName, :], 'infFromCasesYYGEst'].cumsum()
        data.loc[idx[regionName, :], 'cumulativeInfectedPercent'] = data.loc[idx[regionName, :], 'cumulativeInfectionsFromCasesYYG'] / data.loc[idx[regionName, :], 'population']

        #recoveredInfections
        data14Shift=data.loc[idx[regionName, :], 'cumulativeInfectionsFromCasesYYG'].shift(14)
        data32Shift=data.loc[idx[regionName, :], 'cumulativeInfectionsFromCasesYYG'].shift(32)
        data.loc[idx[regionName, :], 'cumulativeRecoveredInfections']=(.2*data32Shift+.8*data14Shift).fillna(0)
        data.loc[idx[regionName, :], 'cumulativeRecoveredInfectionsPercent'] = data.loc[idx[regionName, :], 'cumulativeRecoveredInfections']/data.loc[idx[regionName, :], 'population']
        #Recovered Cases:
        data14Shift=data.loc[idx[regionName, :], 'cumulativeCases'].shift(14)
        data32Shift=data.loc[idx[regionName, :], 'cumulativeCases'].shift(32)
        data.loc[idx[regionName, :], 'recoveredCasesCumulative']=(.2*data32Shift+.8*data14Shift).fillna(0)
        #active
        data.loc[idx[regionName, :], 'activeCases']=data.loc[idx[regionName, :], 'cumulativeCases']-data.loc[idx[regionName, :], 'recoveredCasesCumulative']
        data.loc[idx[regionName, :], 'activeCasesPercent']=data.loc[idx[regionName, :], 'activeCases']/data.loc[idx[regionName, :], 'population']
        data.loc[idx[regionName, :], 'activeInfections']=data.loc[idx[regionName, :], 'cumulativeInfectionsFromCasesYYG']-data.loc[idx[regionName, :], 'cumulativeRecoveredInfections']
        data.loc[idx[regionName, :], 'activeInfectionsPercent']=data.loc[idx[regionName, :], 'activeInfections']/data.loc[idx[regionName, :], 'population']
    return data




if __name__=="__main__":
    casesColor = 'tab:orange'
    yygColor = 'tab:purple'
    deathsColor = 'tab:red'
    testsColor = 'tab:blue'
    recoveredColor = 'tab:green'
    masterData=getMasterCovidDataFromOnlineSources()
    ######################################################
    #to test this, let's plot the cumulative data for USA:
    ######################################################
    regionName='USA'
    plt.title(regionName+': TestPlot')
    plt.xlabel('Date')
    plt.ylabel('CumulativeData')
    #plt.plot(masterData.loc[regionName]['recoveredCasesCumulative'], color=recoveredColor,label='Recovered')
    #plt.plot(masterData.loc[regionName]['cumulativeCases'], color=casesColor, label = 'CumulativeCases')
    plt.plot(masterData.loc[regionName]['activeCases'], color=casesColor, label = 'Active Cases')
    plt.plot(masterData.loc[regionName]['activeInfections'], color=yygColor, label = 'Active Infections')
    #plt.plot(masterData.loc[regionName]['cumulativeInfectionsFromCasesYYG'], color=yygColor, label = 'Estimated Actual Cumulative Infections')
    #plt.plot(masterData.loc[regionName]['testsCumulative'], color=testsColor, label = 'Cumulative Tests')
    #plt.scatter(state.index,state['dailyNewCases-7DayAvg'], color=casesColor)
    plt.grid(True)
    plt.legend()
    plt.show()
    plt.close('all')


    regionName='USA'
    

    fig, ax1 = plt.subplots()
    plt.title(regionName+': TestPlotPercent')
    ax1.set_xlabel('Date')
    ax1.set_ylabel('CumulativeData')
    #plt.plot(masterData.loc[regionName]['recoveredCasesCumulative'], color=recoveredColor,label='Recovered')
    #plt.plot(masterData.loc[regionName]['cumulativeCases'], color=casesColor, label = 'CumulativeCases')
    ax1.plot(masterData.loc[regionName]['activeCasesPercent'], color=casesColor, label = 'Active Cases')
    ax1.plot(masterData.loc[regionName]['activeInfectionsPercent'], color=yygColor, label = 'Active Infections')
    #plt.plot(masterData.loc[regionName]['cumulativeInfectionsFromCasesYYG'], color=yygColor, label = 'Estimated Actual Cumulative Infections')
    #plt.plot(masterData.loc[regionName]['testsCumulative'], color=testsColor, label = 'Cumulative Tests')
    #plt.scatter(state.index,state['dailyNewCases-7DayAvg'], color=casesColor)
    ax1.yaxis.set_major_formatter(PercentFormatter(1))
    ax1.set_ylim(bottom=0)
    plt.grid(True)
    plt.legend()
    plt.show()
    plt.close('all')




