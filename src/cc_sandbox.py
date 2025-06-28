#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jun 20 03:36:04 2025

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

# Use Michelle as testing example, as she multiple different types of leave
x = 'Zhang, Michelle'

# Collect only the clinic shfit entries
df_x = df_x[df_x['Type'] == 'c']

# Pull continuity clinic half-day assignments
# Continuity clinics:
# Belltown, Hobson, International, Madison, Roos, Roos Women, VA, H-AMC
# Note from AY23-24 to AY24-25, Kelli changed the name of VA clinic from "GIM VAMC"
# to "Primary Care V"
# 'GIM VAMC' -> 'Primary Care V'
# 'GIM ROOS'
# 'GIM PMC'
# 'GIM H-AMC'
# 'GIM AMC'
# 'GIM Mad'
# 'GIM Women'

df_x = df_x.dropna(subset=['Assignment'])
df_c = df_x[(df_x.Assignment.str[:3] =='GIM') | (df_x.Assignment.str[:7] == 'Primary')]

# Pull panel management half-day assignments
df_p = df_x[df_x.Assignment.str.contains('Panel')]




