#!/usr/bin/python3

import pymc3 as pm
import pandas as pd
import numpy as np
import arviz as az
from rt_live_covid_model import covid
from matplotlib import pyplot as plt
from covid.models.generative import GenerativeModel
from covid.data import summarize_inference_data
from covid.data import get_and_process_covidtracking_data, summarize_inference_data
import sys


idx = pd.IndexSlice
region = sys.argv[1]

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
    data = data[["positive", "total"]]
    # Now work with daily counts
    data = data.diff().dropna().clip(0, None).sort_index()
    return data.loc[idx[:, :(run_date - pd.DateOffset(1))], ["positive", "total"]]
    
if (region=='USA'):
    df = get_raw_UScovidtracking_data()
    model_data = processUScovidtracking_data(df,run_date=pd.Timestamp.today()-pd.Timedelta(days=1))
    model_data = model_data.loc[region]
else:
    df = get_and_process_covidtracking_data(run_date=pd.Timestamp.today()-pd.Timedelta(days=1))
    model_data = df.loc[region]

gm = GenerativeModel(region, model_data)
gm.sample()

result = summarize_inference_data(gm.inference_data)


#make cases plot
fig, ax = plt.subplots(figsize=(10,5))
result.test_adjusted_positive.plot(c="g", label="Test-adjusted")
result.test_adjusted_positive_raw.plot(c="g", alpha=.5, label="Test-adjusted (raw)", style="--")
result.infections.plot(c="b", label="Implied Infections")
gm.observed.positive.plot(c='r', alpha=.7, label="Reported Positives")
fig.set_facecolor('w')
ax.legend();
ax.set_title(f"{region} rtLive Inferred Cases and Infections")
plt.savefig(fname=region+"_cases.png")


fig, ax = plt.subplots(figsize=(10,5))

ax.set_title(f"{region} rtLive Algorithm Inferred $R_t$")
samples = gm.trace['r_t']
x=result.index
cmap = plt.get_cmap("Reds")
percs = np.linspace(51, 99, 40)
colors = (percs - np.min(percs)) / (np.max(percs) - np.min(percs))
samples = samples.T

result["median"].plot(c="k", ls='-')

for i, p in enumerate(percs[::-1]):
    upper = np.percentile(samples, p, axis=1)
    lower = np.percentile(samples, 100-p, axis=1)
    color_val = colors[i]
    ax.fill_between(x, upper, lower, color=cmap(color_val), alpha=.8)

ax.axhline(1.0, c="k", lw=1, linestyle="--")
fig.set_facecolor('w')

plt.savefig(fname=region+"_rt.png")



