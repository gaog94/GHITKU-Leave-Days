#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri May  9 23:39:29 2025

@author: galengao
"""

from shiny import App, reactive, render, ui

from urllib.request import urlretrieve

import datetime
from collections import Counter

import pandas as pd

def generate_url(startdate, enddate, passkey):
    # format passkey to account for whitespace
    passkey = passkey.replace(' ', '%20')
    
    '''Download amion datatable of interest'''
    # Use the 625c extension to figure out wtf people are doing
    urlstem = "https://www.amion.com/cgi-bin/ocs?Lo={}&Rpt=625ctabs".format(passkey)
    
    # If Amion urls still work this way as documented, consider future upgrade:
    # Request blocks 2-14 for interns & blocks 1-13 for seniors
    # Example w/academic year 2023 as such:
    # https://www.amion.com/cgi-bin/ocs?Lo=***&Rpt=625c&Blks=1-13&Syr=2023
    
    # parse date information
    y, m, d = startdate.strftime('%y'), startdate.month, startdate.day
    delta = (enddate - startdate).days

    datestring = "&Day={}&Month={}-{}&Days={}".format(d, m, y, delta)

    return urlstem + datestring

def download_df(academicYear, passkey):
    # need to adjust these thresholds for intern vs senior calendars
    # will also try to get rid of hard-coded dates in a later patch
    if academicYear == 'AY22':
        startdate = datetime.datetime(2022, 6, 24) # '2022-06-24'
        enddate = datetime.datetime(2023, 6, 27) # '2023-06-27'
    if academicYear == 'AY23':
        startdate = datetime.datetime(2023, 6, 28) # '2023-06-28'
        enddate = datetime.datetime(2024, 6, 30) # '2024-06-30'
    elif academicYear == 'AY24':
        startdate = datetime.datetime(2024, 7, 1) # '2024-07-01'
        enddate = datetime.datetime(2025, 6, 29) # '2025-06-29'
    elif academicYear == 'AY25':
        startdate = datetime.datetime(2025, 6, 30) # '2025-06-30'
        enddate = datetime.datetime(2026, 6, 29) # '2026-06-29'
    else: # if invalid academic year given, then return ancient year for an error
        startdate = datetime.datetime(1, 1, 1)
        enddate = datetime.datetime(1, 1, 2)
    
    # pull data from amion using given academic year and passkey
    url = generate_url(startdate, enddate, passkey)
    path, headers = urlretrieve(url)

    # attempt to parse results and return accordingly
    try:
        df = pd.read_table(path, skiprows=7, header=None, \
                       usecols=[0,3,6,7,8,9,15,16])
    
    except pd.errors.EmptyDataError:
        return pd.DataFrame([])
    
    else:
        # rename columns
        columns = ['Name', 'Assignment', 'Date', 'Start', 'Stop', 'Role', 'Type', 'Assgn']
        df.columns = columns
    
        # Get rid of role == null columns and role == "Services" (e.g. "H MICU A")
        df = df[~df.Role.isnull()]
        df = df[df.Role != 'Services']
        df = df[df.Role.str[-1] != '*']
    
        # replace instances of "(" and ")" with "'" to encode nicknames the same way
        df['Name'] = df.Name.str.replace('\'', '').str.replace('\"', '')
    
        return df
        

def generate_rezzy_dictionary(df):
    # Sorting code
    listRoles = ['IM R1', 'IM R2', 'IM R3', 'RM R1', 'Psych R1', 'Anes R1', \
                 'FM R1', 'FM R2', 'EM UW', 'EM UW R1', 'EM Madigan R1', 'IM R4']
    roleDict = {x:y for x,y in zip(listRoles, range(len(listRoles)))}
    
    # get only role assignments from the first date in the date range
    # this avoids duplication of 
    df_x = df[df.Date == df.Date.iloc[0]]
    
    # drop duplicates name entries and then sort first by role (e.g. PGY year)
    # and then alphebetically by name
    df_x = df_x[~df_x.Name.duplicated()].sort_values(["Role", "Name"], \
                                                 key=lambda x: x.map(roleDict))
    
    masterDict = {r:{x:x for x in df_x[df_x.Role == r]['Name']} \
                  for r in df_x.Role.unique()}
    
    return masterDict

def check_delinquency(df, rezzy):
    '''Note, this script assumes all weekend dates denoted "Vac" are denoted in
    error, as the working assumption is that we get 20 vacation days to use on
    weekdays each academic year. Thus, if you use a vacation day during a 
    weekend on an admitting block, then this app will undercount your vacation
    days'''
    # List of days that will get penalized
    # Note rezzies are NOT penalized for conferences, interviews, retreats/RATL, etc
    penalties = ['Vac', 'Sick', 'LWOP', 'Jury Duty', 'Bereavement', 'Personal Holiday']
    penalties += [x+'*' for x in penalties] # account for Vac*, Sick*, and Bereavement*

    df_x = df[df.Name == rezzy]
    # df_x = df_x.dropna()
    df_x = df_x[df_x.Assgn.isin(penalties)]

    # Strip asterisks for any labels that contain asterisks
    df_x.Assignment = [x.strip('*') for x in df_x.Assignment]

    # Drop any potential duplicate dates (e.g. in case AM & PM are labeled in independent rows)
    df_x = df_x[~df_x.Date.duplicated(keep='first')]

    # Mask Sick & Bereavement under same label to attempt to protect privacy
    df_x.Assignment = ['Sick/Bereavement' if x in  ['Bereavement', 'Sick'] else x for x in df_x.Assignment]

    # Drop vacation days used used on weekend days:
    
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
    df_out = pd.concat([df_nonvac, df_vac], axis=0)[['Assignment', 'Date']]

    # Sort Dates by chronological order
    df_out['Year'] = df_out.Date.str.split('-').str[2].astype(int)
    df_out['Month'] = df_out.Date.str.split('-').str[0].astype(int)
    df_out['Day'] = df_out.Date.str.split('-').str[1].astype(int)
    df_out = df_out.sort_values(['Year', 'Month', 'Day'])
    
    # drop 'Year', 'Month', 'Day', and 'Date' columns for sleek presentation
    df_out = df_out[['Assignment']]

    # reset index to be numerical for styles
    df_out = df_out.reset_index()
    df_out.columns = ['Date', 'Assignment']

    # Create coloring guide for output dataframe
    classes = ['Vac', 'Personal Holiday', 'Sick/Bereavement', 'LWOP', 'Jury Duty']
    colors = ['#1b9e77', '#d95f02', '#7570b3', '#e7298a', '#66a61e']
    styles = [{"class": "text-center", "color": "white"}]
    for absentType, color in zip(classes, colors):
        rowIndices = list(df_out[df_out['Assignment'] == absentType].index)
        styles.append({
            "rows": rowIndices,
            "cols": [1],
            "style": {"background-color": color}
        })
        
    return df_out, styles

def summarize_delinquency(df_out, academicYear):
    classes = ['Vacation', 'Personal', 'Sick/Bereavement', 'Leave W/O Pay', 'Jury Duty']
    mapping = {'Vac': 'Vacation', 'LWOP': 'Leave W/O Pay', 'Personal Holiday': 'Personal'}
    counts = Counter(df_out['Assignment'].replace(mapping))
    df_s = pd.DataFrame(counts, index=[academicYear])
    for c in classes:
        if c not in df_s.columns:
            df_s[c] = 0
            
    return df_s

app_ui = ui.page_fluid(
    ui.row(
        ui.column(4, 
                  ui.h4("Check your ABIM leave days:"),
                  
                  # Amion password
                  ui.input_password("password", "Amion Access Code:", ""),  
              
                  # Date range
                  ui.input_select(
                      "academicYear",
                      "Choose an academic year:",
                      {"AY22": "2022 - 2023", \
                       "AY23": "2023 - 2024" , \
                       "AY24": "2024 - 2025", \
                       "AY25": "2025 - 2026"},
                      selected = "AY24"
                  ),

                  # Submit button to populate list of residents
                  ui.input_action_button("submit_AY", "Submit Year"),  
              
                  ui.HTML("<br><br><br>"),  
              
                  ui.input_select(  
                      "rezzies",  
                      'How many leave days will ___ have used?',  
                      [],
                      multiple=False,
                      width="100%",
                      size=12,
                  ),  
              
                  ui.input_action_button("submit_resident", "Check Leave"),  
                  
                  ui.HTML("<br><br><br>"),  
                  
                  ui.input_text("alert", label=""),

              
        ),
    
        ui.column(8,
                  ui.h2("Summary of Days of Leave"),
                  ui.output_data_frame("DQ_aggregate"), # change this to summary
                  ui.output_text_verbatim("summary", placeholder=False),
                  ui.output_text("asteriskOne"),
                  ui.output_text("asteriskTwo"),
                  
                  ui.HTML("<br> <br>"),
                  ui.output_data_frame("DQ_individual"), # change this to individual dates
        ),

    ),
    
)

def server(input, output, session):
    
    # implement storage of data, so you only have to pull data once
    amionData = reactive.value(pd.DataFrame({" ": [], "  ": []}))
    
    @reactive.effect()
    @reactive.event(input.submit_AY)
    def _():
        df = download_df(input.academicYear(), input.password())
        amionData.set(df)


    @reactive.effect()
    @reactive.event(input.submit_AY)
    def update_select_rezzies():
        df = amionData.get()
        if len(df) == 0:
            ui.update_text('alert', value='Error: check password!')
        else:
            masterDict = generate_rezzy_dictionary(df)
            ui.update_select("rezzies", choices=masterDict)
        
    @reactive.Calc
    @reactive.event(input.submit_resident)
    def data():
        try:
            df_out, styles = check_delinquency(amionData.get(), input.rezzies())
        except AttributeError:
            df_out = pd.DataFrame({" ": [], "  ": []})
            styles = {}
        
        return df_out, styles

    @render.data_frame
    def DQ_individual():
        df_out, styles = data()
        if len(df_out) == 0:
            ui.update_text('alert', value='Error: Not all inputs provided!')
        else:
            return render.DataGrid(
                df_out,
                filters=False,
                summary=False,
                width="100%",
                styles=styles,
            )

    # @output
    @render.data_frame
    def DQ_aggregate():
        df = data()[0]
        if len(df) == 0:
            ui.update_text('alert', value='Error: Not all inputs provided!')
        else:
            columns = ['Vacation', 'Personal', 'Sick/Bereavement', 'Leave W/O Pay', 'Jury Duty']
            legend = pd.DataFrame([20, '1*', '17/3-5**', 'NA', 'NA'], columns=['Max Per Year'], \
                          index = columns).T
                
            df_s = summarize_delinquency(data()[0], input.academicYear())
            df_s = pd.concat([legend, df_s]).reset_index()
            df_s.columns = [' '] + columns
            
            colors = ['#1b9e77', '#d95f02', '#7570b3', '#e7298a', '#66a61e']
    
            return render.DataGrid(
                df_s,
                styles=[
                    {
                        'rows': [1],
                        'cols': [i+1],
                        'style': {'background-color': color},
                    } for i, color in enumerate(colors)]
                    
            )

    @render.text
    @reactive.event(input.submit_resident)
    def summary():
        df = data()[0]
        if len(df) == 0:
            ui.update_text('alert', value='Error: Not all inputs provided!')
        else:
            df = summarize_delinquency(df, input.academicYear()).T
            s = sum(df[input.academicYear()])
            return "%s has used %d days of leave out of 35 advised (per annum)" \
                % (input.rezzies(), s)
    
    @render.text
    @reactive.event(input.submit_resident)
    def asteriskOne():
        if len(data()[0]) == 0:
            ui.update_text('alert', value='Error: Not all inputs provided!')
        else:
            return "*1 personal day is allowed per calendar year (NOT academic year)"

    @render.text
    @reactive.event(input.submit_resident)
    def asteriskTwo():
        if len(data()[0]) == 0:
            ui.update_text('alert', value='Error: Not all inputs provided!')
        else:
            return "**RFPU grants 17 days of sick time per academic year. RFPU \
                also grants 5 days of bereavement leave a year (or 3 if no \
                significant travel is required)"
    
app = App(app_ui, server)