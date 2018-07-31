# -*- coding: utf-8 -*-
"""
Created on Thu Jun  7 14:47:32 2018

@author: INES
"""

import pandas
import pylab as pl
from datetime import datetime, timedelta
import time
from Libraries.microkwkkcom import microKWKKcom

def T_sps_Celsius(beckhoff_var):     
    ##--- Retrieves the temperature of a given variable in the sps ----
    ## - beckhof var takes the name of the beckhoff variable to retrieve the vaalue. A list of the selected values are: 
    ## - T of a layer in HTES --> "HTES_H_W_T_M_IT_"+str(layer)+"_" <---
    ## - T_amb in sensor      --> "AUX_HC_A_T_M___" <---
    try:
        mc = microKWKKcom(server_address = "141.79.92.19", server_port = "4840")
        kwkk_meas = mc.get_all_values()
        T_meas = round(float(kwkk_meas[str(beckhoff_var)]),1)
        return T_meas
    except:
        T_meas = None
        print('Connection to sps failed, please check the variable name or connection to the network')
        return T_meas

def optmode(HP_Switch, CHP_Switch): 
    ## ---- Select an optimal mode depending on the optimized values  ----
     if (round(CHP_Switch) == 1) and (round(HP_Switch) ==0):
         optimal_mode = float(1)
         print('CHP_ON, HP_OFF. Optimal_Mode:', str(optimal_mode))
     elif (round(CHP_Switch) == 0) and (round(HP_Switch) ==1):
         optimal_mode = float(4)
         print('CHP_OFF, HP_ON. Optimal_Mode:', str(optimal_mode))
     elif (round(CHP_Switch) == 0) and (round(HP_Switch) ==0):
         optimal_mode = float(0)
         print('CHP_OFF, HP_OFF. Using Tank Energy, Optimal_Mode:', str(optimal_mode))       
     else: 
         optimal_mode = float(0)
         print('Unrecognized Mode. Optimal_Mode:', str(optimal_mode))
     return optimal_mode

def setspsvals(opt_mode, COIL_Switch): 
    ## ----- Set an optimal mode into the sps server, also set the coil switch value -------
   
    if round(COIL_Switch) == 1:
        coil_value = True
    else: 
        coil_value = False
    try:    
        mc = microKWKKcom(server_address = "141.79.92.19", server_port = "4840")
        mc.set_value("COIL_H_W_B_O_IT__", value = coil_value)
        print(mc.get_value (device = "COIL_H_W_B_O_IT__"))
        mc.set_value(device = "Optimal_Mode", value = opt_mode)
        print(mc.get_value (device = "Optimal_Mode"))
    except:
        print('Connection to SPS unsuccesful, please retry and check connection to the SPS server.')

def read_excel(filename):
    
    #df = pandas.read_excel('Winter_24_Hrs_EPEX.xlsx')
    #df = pandas.read_excel('Winter_Campus_EPEX.xlsx')
    #df = pandas.read_excel('Winter_Campus_Ewerk.xlsx')
    #df = pandas.read_excel('Transition_Dairy_EPEX.xlsx')
    #df = pandas.read_excel('Transition_Home_EPEX.xlsx')
    #df = pandas.read_excel('Transition_Home_Ewerk.xlsx')
    #df = pandas.read_excel('Winter_2days_EPEX.xlsx')
    #df = pandas.read_excel('Winter_2days_Ewerk.xlsx')
    #df = pandas.read_excel('Summer_2days_EPEX.xlsx')
    #df = pandas.read_excel('Summer_2days_Ewerk.xlsx')
    #df = pandas.read_excel('Winter_2_Weeks.xlsx')
    #df = pandas.read_excel('NR_Winter_2_Weeks_EPEX_29.03.2018.xlsx')
    #df = pandas.read_excel('Winter_2_Weeks_EPEX.xlsx')
    df = pandas.read_excel(filename)#'NR_Winter_2_Weeks_EPEX_16.04.2018.xlsx')
    
       ##---Retrieve all the data from the file as variables---
       ##-------#get the values for a given column
    Pth_Load_Heat = df['Pth_Load_Heat'].values
    Time = df['Time'].values
    Pel_Load = df['Pel'].values
    epex_price_buy = df['Elect_Price_Buy'].values
    epex_price_sell = df['Elect_Price_Sell'].values
    T_Amb = df['T_Amb'].values
    
    return Pth_Load_Heat,Time,Pel_Load,epex_price_buy, epex_price_sell,T_Amb

def start_time(dt,date):
    

    st = date.time().hour*dt + int(date.time().minute/(60/dt))
    
    return st

def time_delta(date):
    
    date_actual = datetime.now()
    
    time_delta = date_actual.replace(minute=0,second = 0, microsecond = 0) - date.replace(minute=0,second = 0, microsecond = 0)
    
    delta = int((time_delta.days)*24.0 + (time_delta.seconds)/3600.0)
    
    
#    hour_delta = date_actual.time().hour - date.time().hour
#    
#    day_delta = date_actual.date().day - date.date().day
#    day_delta = day_delta * 24
#    

    return delta

def bivalent_selection_hp(power):
    layer_6 = T_sps_Celsius("HTES_H_W_T_M_IT_"+str(6)+"_")
    layer_1= T_sps_Celsius("HTES_H_W_T_M_IT_"+str(1)+"_")
    
    if power > 0.0 and power <= 10.0:
        if layer_6 < 70.0: 
            optimal_mode = float(1)
            coil = 0
        elif layer_1 > 70.0:
            optimal_mode = float(0)
            coil = 0
#        else:
#            optimal_mode = float(0)
            
    elif power > 10.0 and power <= 17.0:
        if layer_6 < 50.0:
            optimal_mode = float(4)
            coil = 0
        elif layer_1 > 42.0:
            optimal_mode = float(0)
            coil = 0 
#        else:
#            optimal_mode = float(0)
    
    elif power > 17.0:
        if layer_6 < 50.0:
            optimal_mode = float(4)
            coil = 1
        elif layer_1 > 42.0:
            optimal_mode = float(0)
            coil = 0
#        else:
#            optimal_mode = float(0)
    else:
        optimal_mode = float(0) 
        coil = 0
        
    return optimal_mode, coil
            
def bivalent_selection_adcm(power): 

    if power > 0.0 and power <= 12.0:
        optimal_mode = float(2)
    elif power > 12.0:
        optimal_mode = float(3)
    else:
        optimal_mode = float(0)      
    return optimal_mode



i = 0 
iplus = 0
date = datetime.now()
while i <= 100:
    
    
    filename = 'NR_Winter_2_Weeks_EPEX_16.04.2018.xlsx'
    Pth_Load_Heat,Time,Pel_Load,epex_price_buy, epex_price_sell,T_Amb = read_excel(filename)
    st = start_time(1,date)
    delta = time_delta(date)
    power = Pth_Load_Heat[st + delta]
    optimal_mode, coil = bivalent_selection_hp(power)
    print(optimal_mode)
#    setspsvals(optimal_mode, coil)
    
    
    time.sleep(1)
    i = i + 1
    
    
    




    