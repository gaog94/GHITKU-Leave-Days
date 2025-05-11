#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri May  9 22:11:19 2025

@author: galengao
"""
import pandas as pd
import numpy as np

import datetime

df = pd.read_csv('~/Downloads/Amion_Report_625_1-1-24_to_12-30-24.csv', \
                   skiprows=7, header=None, usecols=[0,3,6,7,8,9,15,16])
columns = ['Name', 'Assignment', 'Date', 'Start', 'Stop', 'Role', 'Type', 'Assgn']
df.columns = columns

# Get names of all IM residents
df_x = df[df.Role.isin(['IM R1', 'IM R2', 'IM R3'])]
rezzies = np.sort(df_x.Name.unique())

# dive into 1 rezzy's clinic numbers
x = 'Zhang, Michelle'

# List of days that will get penalized
# Note rezzies are NOT penalized for conferences, interviews, retreats/RATL, etc
penalties = ['Vac', 'Sick', 'LWOP', 'Jury Duty', 'Bereavement', 'Personal Holiday']
penalties += [x+'*' for x in penalties] # account for Vac*, Sick*, and Bereavement*

df_x = df[df.Name == x]
df_x = df_x.dropna()
df_x = df_x[df_x.Assgn.isin(penalties)]

# Strip asterisks for any labels that contain asterisks
df_x.Assignment = [x.strip('*') for x in df_x.Assignment]

# Drop any potential duplicate dates (e.g. in case AM & PM are labeled in independent rows)
df_x = df_x[~df_x.Date.duplicated(keep='first')]

# Hide Sick/Bereavement
df_x.Assignment = ['Sick/Bereavement' if x in  ['Bereavement', 'Sick'] else x for x in df_x.Assignment]

# Check Vacations are not used on weekend days
# Note, if you somehow game the system and used a vacation day on an admitting block
# then you will be falsely granted a vacation date (i.e. this script assumes all
# weekend dates designated as "Vac" are designated in error, as we get 20 vacation
# days to use on weekdays throughout the year)

# Convert index dates to [DOW Month DD, YYYY] format & add DOW column
df_out = df_x[['Assignment', 'Date', 'Assgn']]
dates, dsow = [], []
for d in df_out.Date:
    if type(d) is str:
        date = datetime.datetime.strptime(d, '%m-%d-%y') # -> datetime obj
        textdate = date.strftime("%A %b %d, %Y") # -> new string
        dates.append(textdate)
        dsow.append(date.strftime("%A"))
    else:
        dates.append('')
        dsow.append('')
df_out.index = dates
df_out['DOW'] = dsow

# Split df_out into vacation and non-vacation days, remove Sat/Sun from vacation
# days, then re-combine into df_out
df_nonvac = df_out[df_out.Assignment != 'Vac']
df_vac = df_out[df_out.Assignment == 'Vac']
df_vac = df_vac[~df_vac.DOW.isin(['Saturday', 'Sunday'])]
df_out = pd.concat([df_nonvac, df_vac], axis=0)[['Assignment']]

# Create coloring guide for output dataframe
classes = ['Vac', 'Personal Holiday', 'Sick/Bereavement', 'LWOP', 'Jury Duty']
colors = ['#1b9e77', '#d95f02', '#7570b3', '#e7298a', '#66a61e']
styles = [{"class": "text-center", "color": "white"}]
for absentType, color in zip(classes, colors):
    rowIndices = list(df_out[df_out['Assignment'] == absentType].index)
    styles.append({
        "rows": rowIndices,
        "cols": [0],
        "style": {"background-color": color}
    })



# Craft Output Summary Dataframe
legend = pd.DataFrame([20, '1*', 20, 'NA', 'NA'], columns=['Max Per Year'], \
                      index = ['Vacation', 'Personal', 'Sick/Bereavement', \
                       'Leave W/O Pay', 'Jury Duty']).T
    
# df_s = legend.T
# len(df_x.Assignment)
# df_s[x] = []

# Craft Output List of Penalized Dates