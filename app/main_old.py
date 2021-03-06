import pandas as pd
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import os
from shutil import copyfile
import datetime as dt
import matplotlib.pyplot as plt
from scipy.stats import linregress
import matplotlib.dates as mdates
import matplotlib
import numpy as np
import math
import io

tfr_ak_az = 131.71
tfr_tt_az = 117.21

tfr_ak_rot_az = tfr_ak_az + 90
tfr_tt_rot_az = tfr_tt_az + 90

def rotate_via_numpy(xy, radians):
    """Use numpy to build a rotation matrix and take the dot product."""
    x, y = xy
    c, s = np.cos(radians), np.sin(radians)
    j = np.matrix([[c, s], [-s, c]])
    m = np.dot(j, [x, y])

    return float(m.T[0]), float(m.T[1])

myFmt = mdates.DateFormatter('%Y-%m-%d')
app = FastAPI()
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
    path = ""
except:
    app.mount("/static", StaticFiles(directory="app/static"), name="static")
    path = "app/"

templates = Jinja2Templates(directory= path + "templates")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    make_custom()
    plots = sorted(os.listdir(path + 'static/plots'))
    plots = list(filter(lambda x: "empty" not in x, plots))
    print(plots)
    plots = ['plots/' + file for file in plots]
    # return render_template('report.html', hists = hists)
    return templates.TemplateResponse("index.html", {"request": request, "plots": plots})

def make_custom_plot(dataframe, filename, name):
    x_orig = pd.to_datetime(dataframe['date'])
    x=np.array(pd.to_datetime(dataframe['date']).index.values, dtype=float)
    y_orig = dataframe[name + '_value']
    y_orig = y_orig
    y_mean = np.mean(y_orig)
    y = np.array(y_orig)
    # y = y
    stats = linregress(x, y)
    m = stats.slope
    b = stats.intercept
    regres_y = m * x + b
    result_row = []
    for index, value in enumerate(regres_y):
        res_value = y[index] - value
        result_row.append(res_value)
    min_sigma = 99999999999
    min_value_shift = 0
    sinus_result = []

    for day in range(365):
        sinus_row = []
        
        for index, value in enumerate(result_row):
            sinus = math.sin(2 * math.pi / 365.25 * index + day)
            sinus_row.append(sinus)
        sinus_row = np.array(sinus_row, dtype=float)
        sinus_regr = linregress(sinus_row, result_row)
        sinus_m = sinus_regr.slope
        sinus_b = sinus_regr.intercept
        sinus_regr_result = sinus_m * sinus_row + sinus_b
        sig_sum = 0
        for index, value in enumerate(result_row):
            sig_sum += (sinus_regr_result[index] - result_row[index])**2
        sigma = math.sqrt(sig_sum/len(result_row))
        if (sigma < min_sigma):
            min_sigma = sigma
            min_value_shift = day
            sinus_result = sinus_regr_result
        
    y_sin = np.array(y) - np.array(sinus_result)
    final_regr = linregress(x, y_sin)
    final_m = final_regr.slope
    final_b = final_regr.intercept
    final_stderr = round(final_regr.stderr * 1000 * 365.25, 2)
    final_intercept_stderr = final_regr.intercept_stderr

    speed_mm_per_year = final_m * 1000 * 365.25
    sinus_result = sinus_result + y_mean
    
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.plot(x, sinus_result, color='green')
    ax.plot(x, y)
    ax.plot(x, final_m * x + final_b, color="red")
    ax.get_yaxis().set_major_formatter(
        matplotlib.ticker.FuncFormatter(lambda x, p: format(round(float(x), 4), ',')))
    # ax.xaxis.set_major_formatter(myFmt)
    ax.set(xlabel='day', ylabel='baseline length', title= filename + ' ' + name + ' baseline time series, speed = ' + str(round(speed_mm_per_year, 2)) + ' mm per year, +-stderr = ' + str(final_stderr))
    plt.setp(ax.get_xticklabels(), rotation=45)
    plt.savefig(path + 'static/plots/final_regr' + '_' + filename + '_' + name + ".png")

def make_custom():
    for file in os.listdir(path + 'data/'):
        filename = file[:-4]
        dataframe = pd.read_csv(path + "data/" + file, parse_dates=['date'])
        dataframe.set_index('date')
        make_custom_plot(dataframe, filename, 'east')
        make_custom_plot(dataframe, filename, 'north')
