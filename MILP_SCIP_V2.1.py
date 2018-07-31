
# -*- coding: utf-8 -*-

"""
Created on Thu May 31st 2018

@author: Oscar VM
"""

#%% Check if code is running in real environment or simulation. Also Check if EPEX Values are read or Excel
#"""xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"""
#""" ---------- Real or simulation ----------"""
real = False            # False - Simulation 
#real = True            # True - Real World
#""" ---------- Weather Forecast ----------"""
f_cast = False
#""" ------------ EPEX reading --------------"""
#epexread = True             # True - Read EPEX Data
epexread = False          # False - Read Excel Data

#"""xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"""
#"""-----------------------------------------"""

#%%
#"""----------------------------------------Library import definition----------------------------------------"""
#"""---------------------------------------------------------------------------------------------------------"""
import pandas
import pylab as pl
from pyscipopt import quicksum, Model
from datetime import datetime, timedelta
from darksky import forecast
from Libraries.microkwkkcom import microKWKKcom
import time
import Libraries.webpage as web
try:
    from Libraries.MQTT_KWKK import mqtt_kwkk
except:
    pass

import pytz
cet = pytz.timezone('Europe/Amsterdam')
pl.close("all")

global elapsed_time
elapsed_time = 0
roll_times = 0

#%%
#"""-------------------------------------------Function Definition-------------------------------------------"""
#"""---------------------------------------------------------------------------------------------------------"""
def WriteExcel(filename,Step_Pgrid_B,Step_Pgrid_S,Step_CHP_bin,Step_HP_bin,Step_COIL_bin,Step_T_HTES, Step_T_CTES, Step_CCM_bin, Step_AdCM_bin, T_amb, T_amb_real, Heat_Load, Cool_Load, epex_buy, epex_sell):
    df = pandas.DataFrame({'Pgrid_Buy':Step_Pgrid_B,'Pgrid_Sell':Step_Pgrid_S,'CHP_Switch': Step_CHP_bin,'HP_Switch': Step_HP_bin,'COIL_Switch': Step_COIL_bin, 'CCM_Switch': Step_CCM_bin, 'AdCM_Switch': Step_AdCM_bin, 'T_HTES': Step_T_HTES, 'T_CTES': Step_T_CTES, 'T_Amb':T_amb, 'T_Amb_R':T_amb_real, 'Heat_Load':Heat_Load, 'Cool_Load':Cool_Load, 'EPEX_buy':epex_buy, 'EPEX_sell':epex_sell})
    writer = pandas.ExcelWriter(filename, engine = 'xlsxwriter')
    df.to_excel(writer, sheet_name='Sheet1', startcol = 0)
    writer.save()   

def epexdata(dt,n,date):
    
    if epexread == False:
        raise ValueError('epex reading disabled')
    
    price_today=[]
    price_tomorrow=[]
    intprice_15m = []
    bsell = 0.151
    bbuy = 0.297
    date_plus = date + timedelta(days=1)

    ## ---retrieve the day ahead information by scrapping the DA webpage...
    da_page = web.DayAheadWebpage()
    da_page.set_date(cet.localize(date_plus))
    da_page.download_page()
    da_page.parse()
    ##--Filter the info to a list of both
    # Base Price
#    for row in  da_page.basepeak_de.iterrows():
#        if (row[1]['time_stamp'].date() == date.date()):
#            bprice_today = float(web.nat2none(row[1]['price_base']))
#        if (row[1]['time_stamp'].date() == date_plus.date()):
#            bprice_tomorrow = float(web.nat2none(row[1]['price_base']))
    # Day Ahead for Today and Tomorrow
    for row in da_page.hours_de.iterrows():
        if row[1]['time_stamp'].date() == date.date():
            price_today.append(float(web.nat2none(row[1]['price'])))
            
        if row[1]['time_stamp'].date() == (date_plus.date()):
            price_tomorrow.append(float(web.nat2none(row[1]['price'])))
     
  
    epexdt = date.time().hour*dt + int(date.time().minute/(60/dt)) #to decide where to start in the list of 192 values depending on current time

    
     ## ---retrieve the intraday information by scrapping the Intradaycontiniuos webpage...
    int_page = web.IntradayWebpageDE()
    int_page.set_date(cet.localize(date))
    int_page.download_page()
    int_page.parse()
    
#    print (int_page.df)
    for row in int_page.df.iterrows():
        if row[1]['time_stamp'].date() == date.date():
            if (row[1]['time_stamp_end'].minute - row[1]['time_stamp'].minute) == 15 or (row[1]['time_stamp_end'].minute - row[1]['time_stamp'].minute)==-45:
                intprice_15m.append(float(web.nat2none(row[1]['weighted_avg'])))
     
    
#    print(intprice_15m)
        
    ##-------------- condense the data to a (n-1 length list )
    
      #-- transform pricetomorrow to 15 min
    
    if len(price_tomorrow)<(24):
        price_tomorrow = intprice_15m
    else:
        price_tomorrow = repeat(dt,pl.array(price_tomorrow))
        
#    print(price_tomorrow)    
    cost_buy =  pl.append((pl.array(intprice_15m)/1000.)+ bbuy ,(pl.array(price_tomorrow)/1000.)+ bbuy) 
    cost_sell = pl.append((pl.array(intprice_15m)/1000.)+ bsell,(pl.array(price_tomorrow)/1000.)+ bsell) 
    
    da_buy15 = cost_buy[epexdt:(n-1)+epexdt]
    da_sell15 = cost_sell[epexdt:(n-1)+epexdt]
    
    return da_buy15, da_sell15

        
def T_amb_forecast(f_hours,i,Total_F_T,sizeb,t_amb_m): 
     ##---- Call a forecast for the next "f_hours" (max168) if one key doesnt work call it with another key, if not then use the last forecast data as the next one.
     ## -  "i" iterate on the loop the required value is i
     ## -  Total_F_T is the actual list with the forecasted values 
     ## -  sizeb recieves the maximum size of the total forecast horizon (m value ) as for comparing with sizea (size of actual forecasted temp list) if there is enough forecasted data for continuing in case of an api retrieve failure.
#    sizea = len(Total_F_T)                    
    Og_coord = 48.491445, 7.952259#
    if f_cast == True:
        key1='8273ad8cd9c3979df031488e4a1e4509'
        key2='ee1ae28de91506ee5679851fa8a84a0b'
    else:
         key1 = 0
         key2 = 0
    queries = {'extend': 'hourly', 'units': 'si'}
    meas_temp = t_amb_m
    
    try:
        offenburg =  forecast(key1, *Og_coord,time= None,timeout=None,**queries)
        T_Amb_Fore_C = pl.array([hour.temperature for hour in offenburg.hourly[:f_hours]])

        roll_times = 0
    except:
        try:
            offenburg =  forecast(key2, *Og_coord,time= None,timeout=None,**queries)
            T_Amb_Fore_C = pl.array([hour.temperature for hour in offenburg.hourly[:f_hours]])
         
            roll_times = 0
        except:
            try:
               if roll_times < 96:
                   T_Amb_Fore_C= pl.roll(Total_F_T[i:],-1) # If no internet connection use the same data and roll it each 25 min
                   
                   roll_times = roll_times + 1
            except:
                
                print("Forecast data not accesible, using values from the excel File")
                T_Amb_Fore_C = T_Amb[i:]
           
    T_Amb_Forec_real = pl.array(T_Amb_Fore_C)
    
    if meas_temp==None:
        pass
    else:

        T_Amb_Fore_C[0]= float(meas_temp)
        T_Amb_Fore_C[1]= float(meas_temp)
        
    return  T_Amb_Fore_C,  T_Amb_Forec_real

   
def interpolate(dt, Input_list ):   #interpolate the values in dt steps to transform from 1 hour to 15 min
    sz=int(Input_list.size)-1         #dt = 4 for 15 min
    Split_list = []
    for i in range(sz):
        Split_list =  pl.append(Split_list[:i*(dt)],pl.linspace(Input_list[i],Input_list[i+1],dt+1))
    return Split_list    

def repeat(dt, Input_list ): #Don´t interpolate values but repeat the same value i+(dt-1) times e.g  1,2,3,4 = 1,1,1,1,2,2,2,2,3,3,3.....
    sz=int(Input_list.size)          #dt = 4 for 15 min
    Split_list = []
    for i in range(sz):
        Split_list =  pl.append(Split_list,pl.ones(dt)*Input_list[i])
    return Split_list   

def time_to_15min(dt, Input_list):   #change the time vector from its original value to a list from 0 to the total forecast horizon in hours *dt
    sz=int(Input_list.size)*dt       #dt = 4 for changing to 15 min
#    Split_list = []
    Split_list = pl.array(range(sz))
    return Split_list
        
def binarytransform(comparison_value, input_list):     #Transforms a list into a binary integer one given a specified condition input_list <= comparison_value
    input_list = (input_list <= comparison_value)*1
    return input_list

def ReadSPS(beckhoff_var):     
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
    
    
def optmode(HP_Switch, CHP_Switch, CCM_Switch, AdCM_Switch): 
    ## ---- Select an optimal mode depending on the optimized values  ----
    if (round(CHP_Switch) == 1) and (round(HP_Switch) ==0) and (round(CCM_Switch) ==0) and (round(AdCM_Switch) ==0):
         optimal_mode = float(1)
         print('CHP_ON, HP_OFF. Optimal_Mode:', str(optimal_mode))
    elif (round(CHP_Switch) == 0) and (round(HP_Switch) ==1):
         optimal_mode = float(4)
         print('CHP_OFF, HP_ON. Optimal_Mode:', str(optimal_mode))
    elif (round(CHP_Switch) == 0) and (round(CCM_Switch) ==1):
         optimal_mode = float(3)
         print('CHP_OFF, CCM_ON. Optimal_Mode:', str(optimal_mode))  
    elif (round(CHP_Switch) == 0) and (round(AdCM_Switch) ==1):
         optimal_mode = float(5)
         print('CHP_OFF, AdCM_ON. Optimal_Mode:', str(optimal_mode))
    elif (round(CHP_Switch) == 1) and (round(CCM_Switch) ==1):
         optimal_mode = float(6)
         print('CHP_ON, CCM_ON. Optimal_Mode:', str(optimal_mode))
    elif (round(CHP_Switch) == 1) and (round(AdCM_Switch) ==1):
         optimal_mode = float(2)
         print('CHP_ON, AdCM_ON. Optimal_Mode:', str(optimal_mode))
    elif (round(CHP_Switch) == 0) and (round(HP_Switch) ==0) and (round(CCM_Switch) == 0) and (round(AdCM_Switch) ==0) :
         optimal_mode = float(0)
         print('CHP_OFF, HP_OFF. Using Tank Energies, Optimal_Mode:', str(optimal_mode))       
    else: 
         optimal_mode = float(0)
         print('Unrecognized Mode. Optimal_Mode:', str(optimal_mode))
    return optimal_mode
 
def WriteSPS(opt_mode, COIL_Switch): 
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

#%% Formulate the MILP Problem as a Function
#    """-----------------------------------------------"""
#    """----- Define the MILP model as a function -----"""
#    """-----------------------------------------------"""

    ## - n receives the number of time steps to solve per iteration
    ## - dt is the amount of steps to discretizice the model eg. dt =  4 is every 15 min = 1hr /  4 for every hour dt = 1.
    ## - Par* = the parameters that aresolved every iteration as the Cost of electricity per time window.
    ## - n_switching is the allowed number of switching times per iteration in the n horizon.
def kwkk_opt(n, dt, n_switching_CHP, n_switching_HP, min_runtime, Par_C_El_B, Par_C_El_S, Par_T_Amb_bin, Par_Load_El, Par_Load_Th, Par_Load_C, T_HP_max, T_HP_min, T_AdCM_min, LS_CHP_S, LS_HP_S, LS_CCM_S, LS_AdCM_S):
    
   ## ---Naming the model ( any name can be given ) ----
    model = Model("kwkk_milp")

   ## ----- Declare the variables of the model -----
    Pel_CHP =  {}
    Pgrid_B =  {}
    Pgrid_S =  {}
    Pth_COIL = {}
    Pth_HP =   {}
    Pth_CHP =  {}
    Pth_AdCM_HT = {}
    Pth_AdCM_LT = {}
    Pel_CCM    =  {}
    Pel_AdCM = {}
    Pel_AUX =  {}
    Pth_CCM  = {}
    Pel_OC  =  {}
    V_FUEL =   {}
    CHP_bin =  {}
    COIL_bin = {}
    HP_bin =   {}
    CCM_bin =  {}
    AdCM_bin = {}
    T_HTES =   {}
    T_CTES =   {}
    HP_S_bin = {}
    CHP_S_bin =  {}
    CCM_S_bin =  {}
    AdCM_S_bin = {}
    Surplus_Tadcm = {}
    
    # Different Binaries for ON/OFF of components to formulate maximum switching contraint
#    HP_ON_bin =  {}
#    CHP_ON_bin = {}
#    HP_OFF_bin = {}
#    CHP_OFF_bin ={}
    
  ## ------ Define the variables of ther model -----  
    for j in range((n-1)+min_runtime):
    
        Pel_CHP[j] =  model.addVar(vtype = "C", \
                        name = "Pel_CHP_{0}".format(j), \
                        lb = 0.0, ub = Pmax_CHP_El)
        
        Pgrid_B[j] =  model.addVar(vtype = "C", \
                        name = "Pgrid_B_{0}".format(j), \
                        lb = 0.0)
        
        Pgrid_S[j] =  model.addVar(vtype = "C", \
                        name = "Pgrid_S_{0}".format(j), \
                        lb = 0.0)
        
        Pth_COIL[j] =   model.addVar(vtype = "C", \
                        name = "Pth_COIL_{0}".format(j), \
                        lb = 0.0, ub = Pmax_COIL_Th)
        
        Pth_HP[j] =     model.addVar(vtype = "C", \
                        name = "Pth_HP_{0}".format(j), \
                        lb = 0.0, ub = Pmax_HP_Th)
        
        Pth_CHP[j] =    model.addVar(vtype = "C", \
                        name = "Pth_CHP_{0}".format(j), \
                        lb = 0.0, ub = Pmax_CHP_Th)
        
        Pth_AdCM_HT[j] =   model.addVar(vtype = "C", \
                        name = "Pth_AdCM_HT_{0}".format(j), \
                        lb = 0.0, ub = Pmax_AdCM_HT_Th)
        
        Pth_AdCM_LT[j] =   model.addVar(vtype = "C", \
                        name = "Pth_AdCM_LT_{0}".format(j), \
                        lb = 0.0, ub = Pmax_AdCM_LT_Th)
        
        Pel_AdCM[j] =   model.addVar(vtype = "C", \
                        name = "Pel_AdCM_{0}".format(j), \
                        lb = 0.0, ub = Pmax_AdCM_El)
        
        Pel_CCM[j] =   model.addVar(vtype = "C", \
                        name = "Pel_CCM_{0}".format(j), \
                        lb = 0.0, ub = Pmax_CCM_El)
        
        
        Pel_AUX[j] =    model.addVar(vtype = "C", \
                        name = "Pel_AUX_{0}".format(j), \
                        lb = 0.0)
        
        Pth_CCM[j]  =   model.addVar(vtype = "C", \
                        name = "Pth_CCM_{0}".format(j), \
                        lb = 0.0, ub = Pmax_CCM_Th)
       
        Pel_OC[j]  =    model.addVar(vtype = "C", \
                        name = "Pel_OC_{0}".format(j), \
                        lb = 0.0) 
        
        
        V_FUEL[j] =     model.addVar(vtype = "C", \
                        name = "V_FUEL_{0}".format(j), \
                        lb = 0.0, ub = vdot_fuel) 
        
        T_HTES[j] =     model.addVar(vtype = "C", \
                        name = "T_HTES_{0}".format(j), \
                        lb = HTES_Cold, ub = HTES_Warm)
        
        T_CTES[j] =     model.addVar(vtype = "C", \
                        name = "T_CTES_{0}".format(j), \
                        lb = CTES_Cold, ub = CTES_Warm)
        
        CHP_bin[j] =  model.addVar(vtype = "B", \
                        name = "CHP_bin_{0}".format(j))
        COIL_bin[j] = model.addVar(vtype = "B", \
                        name = "COIL_bin_{0}".format(j))
        HP_bin[j] =   model.addVar(vtype = "B", \
                        name = "HP_bin_{0}".format(j))
        
        CCM_bin[j] =    model.addVar(vtype = "B", \
                        name = "CCM_bin_{0}".format(j))
        
        AdCM_bin[j] =   model.addVar(vtype = "B", \
                        name = "AdCM_bin_{0}".format(j))

        HP_S_bin[j] =   model.addVar(vtype = "B", \
                        name = "HP_S_bin_{0}".format(j))
        CHP_S_bin[j] =  model.addVar(vtype = "B", \
                        name = "CHP_S_bin_{0}".format(j))
        
        CCM_S_bin[j] =    model.addVar(vtype = "B", \
                        name = "CCM_S_bin_{0}".format(j))
        
        AdCM_S_bin[j] =   model.addVar(vtype = "B", \
                        name = "AdCM_S_bin_{0}".format(j))
        
        
        

        Surplus_Tadcm[j] = model.addVar(vtype = "C", \
                        name = "Surplus_Tadcm_{0}".format(j), \
                        lb = 0)
#        HP_ON_bin[j] =   model.addVar(vtype = "B", \
#                        name = "HP_ON_bin_{0}".format(j))
#        CHP_ON_bin[j] =  model.addVar(vtype = "B", \
#                        name = "CHP_ON_bin_{0}".format(j))
#        HP_OFF_bin[j] =  model.addVar(vtype = "B", \
#                        name = "HP_OFF_bin_{0}".format(j))
#        CHP_OFF_bin[j] = model.addVar(vtype = "B", \
#                        name = "CHP_OFF_bin_{0}".format(j))
#    
    T_HTES[(n-1)+min_runtime] = model.addVar(vtype = "C", \
                    name = "T_HTES_{0}".format((n-1)+min_runtime), \
                    lb = HTES_Cold, ub = HTES_Warm)
    
    T_HTES[0+min_runtime] =     model.addVar(vtype = "C", \
                    name = "T_HTES_{0}".format(0+min_runtime), \
                    lb = T_HTES_init_0, ub = T_HTES_init_0)
    
    T_CTES[(n-1)+min_runtime] = model.addVar(vtype = "C", \
                    name = "T_CTES_{0}".format((n-1)+min_runtime), \
                    lb = CTES_Cold, ub = CTES_Warm)
    
    T_CTES[0+min_runtime] =     model.addVar(vtype = "C", \
                    name = "T_CTES_{0}".format(0+min_runtime), \
                    lb = T_CTES_init_0, ub = T_CTES_init_0)
    
    for j in range(0,min_runtime):
    
        HP_bin[j] =  model.addVar(vtype = "I", \
                        name = "HP_bin_{0}".format(j), \
                        lb = int(LS_HP_S[j]), ub = int(LS_HP_S[j]))
    
        CHP_bin[j] = model.addVar(vtype = "I", \
                        name = "CHP_bin_{0}".format(j), \
                        lb = int(LS_CHP_S[j]), ub = int(LS_CHP_S[j]))
        
        CCM_bin[j] =  model.addVar(vtype = "I", \
                        name = "CCM_bin_{0}".format(j), \
                        lb = int(LS_CCM_S[j]), ub = int(LS_CCM_S[j]))
    
        AdCM_bin[j] = model.addVar(vtype = "I", \
                        name = "AdCM_bin_{0}".format(j), \
                        lb = int(LS_AdCM_S[j]), ub = int(LS_AdCM_S[j]))

    ##------ Define the constraints -------
    
    for t in range(min_runtime,(n-1)+min_runtime):
    
#        model.addCons(0 == (Pth_HP[t]*(1./COP_HP))+(Pth_COIL[t]*(1./Pth_eff_COIL))+(Par_Load_El[t-min_runtime]*(1./dt))-(Pel_CHP[t])-Pgrid_B[t]+Pgrid_S[t])
        model.addCons(0 == (Pel_AUX[t])+(Pel_OC[t])+(Pel_CCM[t])+(Pel_AdCM[t])+(Pth_HP[t]*(1./COP_HP))+(Pth_COIL[t]*(1./Pth_eff_COIL))+(Par_Load_El[t-min_runtime]*(1./dt))-(Pel_CHP[t])-Pgrid_B[t]+Pgrid_S[t])
    
#        model.addCons(0 == (((T_HTES[t+1]-T_HTES[t])* (1./3600))*(HTES_Cap*rho_w*cp_w))-(((Pth_HP[t]+Pth_COIL[t]+(Pth_CHP[t])))-Par_Load_Th[t-min_runtime]*(1./dt)))
        model.addCons(0 == (((T_HTES[t+1]-T_HTES[t])* (1./3600))*(HTES_Cap*rho_w*cp_w))-((Pth_HP[t]+Pth_COIL[t]+Pth_CHP[t])-Pth_AdCM_HT[t]-Par_Load_Th[t-min_runtime]*(1./dt)))

        model.addCons(0 == (((T_CTES[t+1]-T_CTES[t])* (1./3600))*(CTES_Cap*rho_w*cp_w))+((Pth_CCM[t]+Pth_AdCM_LT[t])-Par_Load_C[t-min_runtime]*(1./dt)))
    
        model.addCons(0 == (Pel_CHP[t]*dt) - (Pmax_CHP_El * CHP_bin[t]))
        
        model.addCons(0 == (Pel_AdCM[t]*dt) - (Pmax_AdCM_El * AdCM_bin[t]))
        
        model.addCons(0 == (Pel_CCM[t]*dt) - (Pmax_CCM_El * CCM_bin[t]))
        
        model.addCons(0 == (Pel_AUX[t]*dt) - ((0.7 * HP_bin[t])+(0.3 *AdCM_bin[t])+(0.3* CCM_bin[t])+(0.1)))

        model.addCons(0 == (Pel_OC[t]*dt) - ((1.4 * HP_bin[t])+(1.4 *AdCM_bin[t])+(1.4* CCM_bin[t])))

        model.addCons(0 == (Pth_HP[t]*dt) - (Pmax_HP_Th * HP_bin[t]))
        
        model.addCons(0 == (Pth_COIL[t]*dt) - (Pmax_COIL_Th * COIL_bin[t]))
       
        model.addCons(0 == (Pth_CHP[t]*dt) - (Pmax_CHP_Th * CHP_bin[t]))
        
        model.addCons(0 == (Pth_AdCM_HT[t]*dt) - (Pmax_AdCM_HT_Th * AdCM_bin[t]))
        
        model.addCons(0 == (Pth_AdCM_LT[t]*dt) - (Pmax_AdCM_LT_Th * AdCM_bin[t]))
        
        model.addCons(0 == (Pth_CCM[t]*dt) - (Pmax_CCM_Th * CCM_bin[t]))
    
        model.addCons(0 == (V_FUEL[t]*dt) - (vdot_fuel * CHP_bin[t]))
        
  
      ##------System  constraints in terms of binaries-------
        
        model.addCons(0 <= (CHP_bin[t]+HP_bin[t] <= 1)) #HP and CHP cannot work at the same time
        model.addCons(0 <= (Par_T_Amb_bin[t-min_runtime]+HP_bin[t] <= 1)) #HP should not work if Tamb is less than a certain level. ParT_amb_bin is obtained via binary function.
        
        model.addCons(0 <= (CCM_bin[t]+HP_bin[t]+AdCM_bin[t] <= 1)) #HP and CCM 

      
        ##------ System  constraints big M ------- 
        
        model.addCons( (T_HTES[t] - 500*(1-HP_bin[t]))<= T_HP_max) # --- if THTES > T_HP_max(in K) it it not possible to turn ON the Heat Pump.
#        model.addCons( ((T_HTES[t]-T_HP_max) * HP_bin[t]) <= 0) 
        
#        model.addCons( (T_HTES[t] + 500*(1-AdCM_bin[t]) - Surplus_Tadcm[j]) == T_AdCM_min)
        model.addCons( (T_HTES[t] + 500*(1-AdCM_bin[t])) >= T_AdCM_min)
#        model.addCons( ((T_AdCM_min-T_HTES[t]) - 500*(1-AdCM_bin[t])) <= 0)

        ##------ System  constraints vanishing variables-------
        
##        -T_HTES[t] <= T_AdCM_min + 500 * AdCM_bin[t]
#        model.addCons( (((T_AdCM_min - T_HTES[t])*AdCM_bin[t])<=0))
        
        
#       model.addCons(0 >= HP_bin[t] *(T_HTES[t]-T_HP_max))     # --- if THTES > THP max(in k) it it not possible
###     model.addCons(0 >= HP_bin[t] *((T_HP_min+273.15)-T_Amb[t]))     # in dev..-----if Tamb < Thp min x it it not possible 
        
    
    ## ---- System maximum switching constraints ----   Divided in 2 parts as it showed better calculation of the flank than doing everything together. (flank can be 0 or 1 if both switches are 0)
    for k in range(1,min_runtime+1):
        
        model.addCons((CHP_bin[k-1]-CHP_bin[k]-CHP_S_bin[k] <= 0))        #)  This part is to calculate the flanks of the past times. Depending on the previous Switch and the actual.
        model.addCons((-CHP_bin[k-1]+CHP_bin[k]-CHP_S_bin[k] <= 0))       #)  It is done from 1 to min_runtime + 1 This means the flank between the first opt. switch the - 1 switch of the opt is calculated.
        model.addCons((HP_bin[k-1]-HP_bin[k]-HP_S_bin[k] <= 0))           #)  Past switches -> [s0 s1 s2 s3 ] [s4] <- Present switch (first opt switch)  The flanks start s1-s0 = f0 ... s4-s3 = f3
        model.addCons((-HP_bin[k-1]+HP_bin[k]-HP_S_bin[k] <= 0))          #)  past flanks   -> [ - f0 f1 f1 ] [f3]  <-Present Flanks ()          
        model.addCons((CCM_bin[k-1]-CCM_bin[k]-CCM_S_bin[k] <= 0))           
        model.addCons((-CCM_bin[k-1]+CCM_bin[k]-CCM_S_bin[k] <= 0))
        model.addCons((AdCM_bin[k-1]-AdCM_bin[k]-AdCM_S_bin[k] <= 0))           
        model.addCons((-AdCM_bin[k-1]+AdCM_bin[k]-AdCM_S_bin[k] <= 0))        
        
            
    for k in range(1+min_runtime,(n-1)+min_runtime):   
       
        model.addCons((CHP_bin[k-1]-CHP_bin[k]-CHP_S_bin[k] <= 0))       #) this part calculates flanks from the present. it is done from the min runtime +1 to n-1 - runtime.
        model.addCons((-CHP_bin[k-1]+CHP_bin[k]-CHP_S_bin[k] <= 0))      #) Present switches -> [s4 s5 s6 s7........]                                                                   
        model.addCons((HP_bin[k-1]-HP_bin[k]-HP_S_bin[k] <= 0))          #) present flanks ->   [-  f4 f5 f6 f7 ....]  --!! f3 is calculated in the previous part.
        model.addCons((-HP_bin[k-1]+HP_bin[k]-HP_S_bin[k] <= 0))
        model.addCons((CCM_bin[k-1]-CCM_bin[k]-CCM_S_bin[k] <= 0))           
        model.addCons((-CCM_bin[k-1]+CCM_bin[k]-CCM_S_bin[k] <= 0))
        model.addCons((AdCM_bin[k-1]-AdCM_bin[k]-AdCM_S_bin[k] <= 0))           
        model.addCons((-AdCM_bin[k-1]+AdCM_bin[k]-AdCM_S_bin[k] <= 0))        
     
  
#    model.addCons(0<=(quicksum(CHP_S_bin[k] for k in range( min_runtime,(n-1)+min_runtime)) <= n_switching_CHP))   #) this part takes the values of the max switching-
#    model.addCons(0<=(quicksum( HP_S_bin[k] for k in range( min_runtime,(n-1)+min_runtime)) <= n_switching_HP))    #) this is the sum of all the flanks since min_runtime until the end 
#    model.addCons(0<=(quicksum( CCM_S_bin[k] for k in range( min_runtime,(n-1)+min_runtime)) <= n_switching_CCM))    #) this is the sum of all the flanks since min_runtime until the end 
#    model.addCons(0<=(quicksum( AdCM_S_bin[k] for k in range( min_runtime,(n-1)+min_runtime)) <= n_switching_AdCM))    #) this is the sum of all the flanks since min_runtime until the end 
##                                                                                                                    ##) [f3 + f4 + f5 + f6 + ....fn-1+min_runtime] <= n_switching

    for k in range((min_runtime-1),(n-1)+min_runtime): 
            
        model.addCons((quicksum(CHP_S_bin[k-j]  for j in range(min_runtime)) <= 1))                                #)this part adds the min runtime from as the starting point - 3 steps behind until the end of the horizon
        model.addCons((quicksum( HP_S_bin[k-j]  for j in range(min_runtime)) <= 1))   
        
    for k in range((min_runtime-1-2),(n-1)+min_runtime):    
                                                                 #) [ -   f0   f1    f2 ] [f3]
        model.addCons((quicksum(CCM_S_bin[k-j]  for j in range(min_runtime-2)) <= 1))                                #)this part adds the min runtime from as the starting point - 3 steps behind until the end of the horizon
        model.addCons((quicksum( AdCM_S_bin[k-j]  for j in range(min_runtime-2)) <= 1))                                                                                                                   #)      <= + =  +  =  + =Xmrt  <=1   ...                                                                                                              
     ##  ---- ---- Add objective term. ------------
     
    model.setObjective(quicksum((Par_C_El_B[t-min_runtime]*Pgrid_B[t]) + (C_FUEL*V_FUEL[t]) - (Par_C_El_S[t-min_runtime]*Pgrid_S[t]) for t in range(min_runtime,(n-1)+min_runtime)))
    
     ## ---- Add the variables to the data set, for later retrieval ----
     
    model.data = Pel_CHP, Pgrid_B, Pgrid_S, Pth_COIL, Pth_HP, Pth_CHP, V_FUEL, CHP_bin, COIL_bin, HP_bin, CCM_bin, AdCM_bin, T_HTES, CHP_S_bin, HP_S_bin, CCM_S_bin, AdCM_S_bin, Pel_CCM, Pel_AdCM, Pel_AUX, Pel_OC, Pth_CCM, Pth_AdCM_HT, Pth_AdCM_LT, T_CTES
    return model

#    """-----------------------------------------------"""
#    """------- Function for plotting the data --------"""
#    """-----------------------------------------------"""

def plotall(Time,i,dt, Pth_Load_Heat,Pth_CHP_opt,Pth_HP_opt,Pth_COIL_opt,C_El_B,C_El_S,E_El_HP_opt,E_El_COIL_opt,Pel_Load,Pgrid_B_opt,Pgrid_S_opt,P_El_CHP_opt,T_HTES_opt,T_Amb_f,T_HP_min,COIL_bin_opt,CHP_bin_opt,HP_bin_opt,T_Amb_Forec_real,Pth_Load_Heat_File, Pth_Load_Cool, Pel_AUX_opt, Pel_CCM_opt, Pel_AdCM_opt, Pth_AdCM_HT_opt, Pth_AdCM_LT_opt, Pel_OC_opt, Pth_CCM_opt, CCM_bin_opt, AdCM_bin_opt):
    import matplotlib.ticker as ticker
    Q_HTES_opt=pl.zeros(T_HTES_opt.shape)
    Q_CTES_opt=pl.zeros(T_CTES_opt.shape)
    
    
    for t in range ((n-1)+(i-1)):
        Q_HTES_opt[0] = Q_HTES_init   
        Q_CTES_opt[0] = Q_CTES_init  
        Q_HTES_opt[t+1] = ((((T_HTES_opt[t+1]-T_HTES_opt[t])/3600.)*(HTES_Cap*rho_w*cp_w)))+Q_HTES_opt[t]
        Q_CTES_opt[t+1] = ((((T_CTES_opt[t+1]-T_CTES_opt[t])/3600.)*(CTES_Cap*rho_w*cp_w)))+Q_CTES_opt[t]

        
    Q_HTES_shift = pl.zeros(T_HTES_opt.shape)
    Q_HTES_delta = pl.zeros(T_HTES_opt.shape)
    Q_CTES_shift = pl.zeros(T_CTES_opt.shape)
    Q_CTES_delta = pl.zeros(T_CTES_opt.shape)
    
    for k in range ((n-1)+(i-1)):    
        Q_HTES_shift[k] = Q_HTES_opt[k+1]
        Q_HTES_delta[k] = (-Q_HTES_shift[k]+Q_HTES_opt[k])*dt
        Q_CTES_shift[k] = Q_CTES_opt[k+1]
        Q_CTES_delta[k] = (-Q_CTES_shift[k]+Q_CTES_opt[k])*dt
    

    tgrid = pl.array(Time[0:(n-1)+(i-1)])


    fig1 = pl.figure(1)
    ax1 = fig1.add_subplot(211)
    ax1.plot(tgrid,Pth_Load_Heat[0:(n-1)+(i-1)]+Pth_AdCM_HT_opt, '-',color = 'green')
    ax1.plot(tgrid,Pth_Load_Heat[0:(n-1)+(i-1)], '-')
    ax1.bar(pl.append(tgrid,tgrid[-1]+1),Q_HTES_delta)
    ax1.bar(tgrid,Pth_CHP_opt,bottom = Q_HTES_delta[0:(n-1)+(i-1)])
    ax1.bar(tgrid,Pth_HP_opt ,bottom = Q_HTES_delta[0:(n-1)+(i-1)]+Pth_CHP_opt)
    ax1.bar(tgrid,pl.absolute(Pth_COIL_opt) ,bottom =Q_HTES_delta[0:(n-1)+(i-1)]+Pth_CHP_opt+Pth_HP_opt)
    ax1.yaxis.set_major_locator(ticker.MultipleLocator(4))
    ax1.yaxis.set_minor_locator(ticker.MultipleLocator(2))
    pl.xlabel('Time [h]')
    pl.ylabel('Power [kWth]')
    pl.legend(['Pth_AdCM','Pth_LOAD','Q_HTES','Pth_CHP','Pth_HP','Pth_COIL'], loc = 'lower right', prop={'size':8})
    ax2 = fig1.add_subplot(211, sharex=ax1, frameon=False)
    ax2.plot(tgrid,C_El_B[0:(n-1)+(i-1)], '--',color='r') 
    ax2.yaxis.tick_right()
    ax2.yaxis.set_label_position("right")
    pl.ylabel("Price [Euro/kWhel]")
    pl.legend(['El_Price'],prop={'size':8},loc='upper right')
    pl.grid(True)  
    
    fig8 = pl.figure(8)
    ax1 = fig8.add_subplot(211)
    ax1.plot(tgrid,Pth_Load_Cool[0:(n-1)+(i-1)], '-')
    ax1.bar(pl.append(tgrid,tgrid[-1]+1),-Q_CTES_delta)
    ax1.bar(tgrid,Pth_CCM_opt,bottom = Q_CTES_delta[0:(n-1)+(i-1)])
    ax1.bar(tgrid,Pth_AdCM_LT_opt ,bottom = Q_CTES_delta[0:(n-1)+(i-1)]+Pth_CCM_opt)
    ax1.yaxis.set_major_locator(ticker.MultipleLocator(4))
    ax1.yaxis.set_minor_locator(ticker.MultipleLocator(2))
    pl.xlabel('Time [h]')
    pl.ylabel('Power [kWth]')
    pl.legend(['Pth_LOAD_Cool','Q_CTES','Pth_CCM','Pth_AdCM'], loc = 'lower right', prop={'size':8})
    ax2 = fig8.add_subplot(211, sharex=ax1, frameon=False)
    ax2.plot(tgrid,C_El_B[0:(n-1)+(i-1)], '--',color='r') 
    ax2.yaxis.tick_right()
    ax2.yaxis.set_label_position("right")
    pl.ylabel("Price [Euro/kWhel]")
    pl.legend(['El_Price'],loc='upper right',prop={'size':8} )
    pl.grid(True)  
    
    fig2 = pl.figure(2)    
    pl.clf()    
    ax1 = fig2.add_subplot(211)
    ax1.plot(tgrid,(E_El_HP_opt)+(E_El_COIL_opt)+Pel_AdCM_opt+Pel_CCM_opt+Pel_AUX_opt+Pel_OC_opt+Pel_Load[0:(n-1)+(i-1)], '-')
    ax1.bar(tgrid,Pgrid_B_opt)
    ax1.bar(tgrid,P_El_CHP_opt, bottom = pl.absolute(Pgrid_B_opt+Pgrid_S_opt))
    ax1.bar(tgrid,-Pgrid_S_opt)
    ax1.yaxis.set_major_locator(ticker.MultipleLocator(2))
    ax1.yaxis.set_minor_locator(ticker.MultipleLocator(1))
    pl.xlabel('Time [h]')
    pl.ylabel('Power [kWel]')
    pl.legend(['LOAD','Pgrid_buy','Pel_CHP','Pgrid-sell'],loc = 'lower right', prop={'size':8})
    ax2 = fig2.add_subplot(211, sharex=ax1, frameon=False)
    ax2.plot(tgrid,C_El_B[0:(n-1)+(i-1)], '--',color='r') 
    ax2.yaxis.tick_right()
    ax2.yaxis.set_label_position("right")
    pl.ylabel("Price [Euro/kWhel]")
    pl.legend(['El_Price'], loc = 'upper right',prop={'size':8})
    pl.grid(True)
    pl.close
    
    
    fig3 = pl.figure(3)
    pl.clf()
    ax1 = fig3.add_subplot(211)
    ax1.plot(tgrid,Pth_Load_Heat_File[0:(n-1)+(i-1)], '-*',color = 'red')
    ax1.plot(tgrid,Pth_Load_Heat[0:(n-1)+(i-1)], '-*',color = 'blue')
    ax1.bar(pl.append(tgrid,tgrid[-1]+1),Q_HTES_opt, color = 'orange')
    ax1.yaxis.set_major_locator(ticker.MultipleLocator(10))
    ax1.yaxis.set_minor_locator(ticker.MultipleLocator(5))
    pl.xlabel('Time [h]')
    pl.ylabel('Power [kWth]')
    pl.legend(['Heat_LOAD','Heat_LOAD_Ajusted','Q_HTES'],loc='best',prop={'size':9})
    ax2 = fig3.add_subplot(211, sharex=ax1, frameon = False)
    ax2.plot(pl.append(tgrid,tgrid[-1]+1),pl.array(T_HTES_opt)-pl.ones(T_HTES_opt.shape)*273.15, color = 'red')
    ax2.yaxis.tick_right()
    ax2.yaxis.set_label_position("right")
    pl.ylabel('Temp [C]')
    pl.legend(['T_HTES'], loc = 4)
    pl.grid(True)
    pl.close
    
    fig4 = pl.figure(4)
    pl.clf()
    ax1 = fig4.add_subplot(211)
#    ax1.plot(tgrid,Pth_Load_Heat_File[0:(n-1)+(i-1)], '-*',color = 'red')
    ax1.plot(tgrid,Pth_Load_Cool[0:(n-1)+(i-1)], '-*',color = 'blue')
    ax1.bar(pl.append(tgrid,tgrid[-1]+1),Q_CTES_opt)
    ax1.yaxis.set_major_locator(ticker.MultipleLocator(10))
    ax1.yaxis.set_minor_locator(ticker.MultipleLocator(5))
    pl.xlabel('Time [h]')
    pl.ylabel('Power [kWth]')
#    pl.legend(['Cool_LOAD','Cool_LOAD_Ajusted','Q_HTES'],loc=4)
    pl.legend(['Cool_LOAD','Q_CTES'],loc='best',prop={'size':9})
    ax2 = fig4.add_subplot(211, sharex=ax1, frameon = False)
    ax2.plot(pl.append(tgrid,tgrid[-1]+1),pl.array(T_CTES_opt)-pl.ones(T_CTES_opt.shape)*273.15, color = 'red')
    ax2.yaxis.tick_right()
    ax2.yaxis.set_label_position("right")
    pl.ylabel('Temp [C]')
    pl.legend(['T_CTES'], loc = 4)
    pl.grid(True)
    pl.close


    fig5 = pl.figure(5)
    pl.clf()  
    ax =pl.subplot(211)
    ax.plot(tgrid, T_Amb_Forec_real[0:(n-1)+(i-1)], color = 'blue')
    ax.plot(tgrid, T_Amb_f[0:(n-1)+(i-1)], color = 'red')
    ax.plot(tgrid, pl.ones(tgrid.size)*T_HP_min,'*' ,color = 'orange')
    ax.yaxis.set_major_locator(ticker.MultipleLocator(5))
    ax.yaxis.set_major_locator(ticker.MultipleLocator(5))
    pl.xlabel('Time [h]')
    pl.ylabel('Temp [C]')
    pl.legend(['T_Amb_Fore','T_Amb_F_Adjusted','T_HP_min'])
    pl.grid(True)
    pl.close
    
    fig6 = pl.figure(6)
    pl.subplot(311)
    pl.step(tgrid,COIL_bin_opt)
    pl.legend(['COIL'],loc='best')
    pl.subplot(312)
    pl.step(tgrid,CHP_bin_opt)
    pl.legend(['CHP'],loc='best')        
    pl.subplot(313)
    pl.step(tgrid,HP_bin_opt)
    pl.legend(['HP'],loc='best')
    pl.close
    
    fig7 = pl.figure(7)
    pl.subplot(311)
    pl.step(tgrid,CCM_bin_opt)
    pl.legend(['CCM'],loc='best')
    pl.subplot(312)
    pl.step(tgrid,AdCM_bin_opt)
    pl.legend(['AdCM'],loc='best')
    pl.close
    
#    with PdfPages('test1.pdf') as pdf:
#        pdf.savefig(fig1)
#        pdf.savefig(fig2)
#        pdf.savefig(fig3)
#        pdf.savefig(fig4)
#        pdf.savefig(fig5)
    
    pl.show()  

# Plot to show deviation in real and simulated tank temperature    
def plotTdev(T_HTES_actual, T_HTES_opt,i,plotart):
    pl.figure(1)
    pl.clf()    
    xgrid = pl.array(range(len(T_HTES_opt[i:-1])))
    pl.plot(xgrid, pl.array(T_HTES_actual[i:])-273.15,plotart, color = 'red')

    
    pl.plot(xgrid, (pl.array(T_HTES_opt[i:-1])-273.15),plotart,color = 'orange')
    pl.xlabel('Iteration [h]')
    pl.ylabel('Temp [C]')
    pl.legend(['T_HTES_actual','T_HTES_predicted'])
    pl.grid(True)
    pl.show()

#    """-----------------------------------------------"""
#    """---------- Retrieve data from excel -----------"""
#    """-----------------------------------------------"""

def read_excel(filename):
    
    df = pandas.read_excel(filename)#'NR_Winter_2_Weeks_EPEX_16.04.2018.xlsx')
    
       ##---Retrieve all the data from the file as variables---
       ##-------#get the values for a given column
    Pth_Load_Heat = df['Pth_Load_Heat'].values
    Time = df['Time'].values
    Pel_Load = df['Pel'].values
    epex_price_buy = df['Elect_Price_Buy'].values
    epex_price_sell = df['Elect_Price_Sell'].values
    T_Amb = df['T_Amb'].values
    Pth_Load_Cool = df['Pth_Load_Cool'].values
    
    return Pth_Load_Heat,Pth_Load_Cool,Time,Pel_Load,epex_price_buy, epex_price_sell,T_Amb

# to increase accuracy the measured load is used as forecast for next hour and rest 23 hours are from forecast file       
def correction_load(i,st,Pth_Load_Heat_File,Pth_Load_Heat,Pth_Load_Cool_File,Pth_Load_Cool,real_load):#ReadSPS("LOAD_HC_W_PT_M___")
    
    if i== 0:
       Pth_Load_Heat= pl.append(pl.array(Pth_Load_Heat),Pth_Load_Heat_File)
       Pth_Load_Cool= pl.append(pl.array(Pth_Load_Cool),Pth_Load_Cool_File)
    else: 
       Pth_Load_Heat = pl.append(Pth_Load_Heat[:i+st],Pth_Load_Heat_File[i+st:])
       Pth_Load_Cool = pl.append(Pth_Load_Cool[:i+st],Pth_Load_Cool_File[i+st:])
       
    meas_load = real_load
    if meas_load==None:
        pass
    elif meas_load < 0:
        Pth_Load_Cool[i+st]= float(meas_load/-1000.)
        Pth_Load_Cool[i+st+1]= float(meas_load/-1000.)
        Pth_Load_Cool[i+st+2]= float(meas_load/-1000.)
        Pth_Load_Cool[i+st+3]= float(meas_load/-1000.)
        
    else:  
        Pth_Load_Heat[i+st]= float(meas_load/1000.)
        Pth_Load_Heat[i+st+1]= float(meas_load/1000.)
        Pth_Load_Heat[i+st+2]= float(meas_load/1000.)
        Pth_Load_Heat[i+st+3]= float(meas_load/1000.)
    return Pth_Load_Heat, Pth_Load_Cool

    

def interpolate_values(dt,Pth_Load_Heat,Pth_Load_Cool,Pel_Load,T_Amb,Time,epex_price_buy,epex_price_sell,Fuel):
        
   ##---Repeat the data not interpolate---
    Pth_Load_Heat = repeat(dt, Pth_Load_Heat)
    Pth_Load_Cool = repeat(dt, Pth_Load_Cool)
    Pel_Load = repeat(dt,  Pel_Load)
#    T_Amb = repeat(dt, T_Amb)
    T_Amb = T_Amb
    
    Time = time_to_15min(dt, Time)
    
    ##---Electricity costs to dt data---
    C_El_B= repeat(dt,epex_price_buy)
    C_El_S= repeat(dt,epex_price_sell)
    
    ##-----------------redefine the fuel variables------------------------
    C_FUEL = Fuel
    
    ##--- set the whole time horizon available from the given file and discreetization
    m= int(Pth_Load_Heat.size)# + 1
    
    return Pth_Load_Heat,Pth_Load_Cool,Pel_Load,T_Amb,Time,C_El_B,C_El_S,C_FUEL,m


#%%

#"""---------------------------------------------------------------------------------------------------------"""
#""" ----------------------------- Define The problem and the required variables ----------------------------"""
#"""---------------------------------------------------------------------------------------------------------"""
#"""_________________________________________________________________________________________________________"""

    
"""Variable definition""" 

    ##---- for storing the data of all the optimizations----
    
Step_Pel_CHP =  []
Step_Pel_AdCM = []
Step_Pel_AUX =  []
Step_Pel_OC  =  []
Step_Pgrid_B =  []
Step_Pgrid_S =  []
Step_Pth_COIL = []
Step_Pth_HP =   []
Step_Pth_CHP =  []
Step_Pth_CCM =  []
Step_Pth_AdCM = []
Step_V_FUEL =   []
Step_CHP_bin =  []
Step_COIL_bin = []
Step_HP_bin =   []
Step_AdCM_bin = []
Step_CCM_bin =  []
Step_T_HTES =   []
Step_T_CTES =   []
Stepplus_T_HTES=[]
Stepplus_T_CTES=[]

EPEX_buy_list = []
EPEX_sell_list = []

T_Amb_f_15 = []
T_Amb_Forec_real_15 = []
T_Amb_Meas = []

Pth_Load_Heat = []
Pth_Load_Cool = []

#%%
"""-------------- Component Specifications ---------------"""
"""-------------------------------------------------------"""
# Main User Input for component Parameters
     ##-------  Powers  ------- 
Pmin_CHP_Th    = 0                 #kW_Th
Pmax_CHP_Th    = 10 
Pmin_CHP_El    = 0
Pmax_CHP_El    = 5                 #kW_El
Pmin_COIL_Th   = 0
Pmax_COIL_Th   = 5               #kW_Th       ##5.8
Pmin_HP_Th     = 0
Pmax_HP_Th     = 16           #kW_Th       ##16
Pmin_AdCM_Th   = 0
Pmax_AdCM_HT_Th   = 10
Pmax_AdCM_LT_Th   = 6.5
Pmin_AdCM_El   = 0
Pmax_AdCM_El   = 0.23
Pmin_CCM_Th    = 0
Pmax_CCM_Th    = 13
Pmin_CCM_El    = 0
Pmax_CCM_El    = 3.2

     ##------ Efficiencies --------
Pel_eff_CHP = 0.3
Pth_eff_CHP = 0.59
COP_HP = 4.45
Pth_eff_COIL = 0.95
EER_CCM = 3.44
COP_AdCM = 0.65
    #---- Storage Tank ----
HTES_Cap = 1.5                  # m3 -- Assuming no loss in the tank. 
CTES_Cap = 1.5
    ##---Thermodynamical properties----
LHV_FUEL = 42600                #Kj/kg , lower heating value
rho_FUEL = 853.5                #kg/m³
rho_w    = 977.8                #kg/m³
cp_w     = 4.180                #kJ/kg.K
 
    ##---Volume flow of Fuel for CHP----
vdot_fuel = 1.8/1000            #m³/h

    ##---Fuel Costs---
Fuel= 510                       #eur/m³

""" Problem Initial Values"""

HTES_Warm = 72 + 273.15         #K Highest possible temperature in tank 
HTES_Cold = 35 + 273.15
CTES_Warm = 15 + 273.15
CTES_Cold = 8 + 273.15
         #K
T_HP_min   = 12                   #Temperature min of ambient to operate the HP.
T_HP_max   = 40 + 273.15   
T_AdCM_min = 55 + 273.15       #Max T_HTES_temperature to operate the HP.

if real:
    T_HTES_init_0 =ReadSPS("HTES_H_W_T_M_IT_"+str(1)+"_") + 273.15              # layer from the tank to retrieve
    T_CTES_init_0 =ReadSPS("CTES_H_W_T_M_IT_"+str(1)+"_") + 273.15
else:
    T_HTES_init_0 = 60 +273.15
    T_CTES_init_0 = 14 +273.15                                                        #Initial temperature in the Tank

Q_HTES_init = ((((T_HTES_init_0-HTES_Cold)/3600.)*(HTES_Cap*rho_w*cp_w)))#77.5        #kW Initial Power in Tank
Q_CTES_init = ((((T_CTES_init_0-CTES_Cold)/3600.)*(CTES_Cap*rho_w*cp_w)))

LS_CHP_S =  pl.array([0,0,0,0])
LS_HP_S =   pl.array([0,0,0,0])
LS_CCM_S =  pl.array([0,0,0,0])
LS_AdCM_S = pl.array([0,0,0,0])

"""-----------Formulation of the MILP problem-------------"""
"""-------------------------------------------------------"""
   ##--- time formulation parameters-----
   
dt = 4                         # hour splitting factor
hours = 24          # hours to solve each iteration
n= hours * dt + 1              # window time horizon
sampling_time = 15             # in min  --- Time to wait between iterations              
forecast_horizon = hours + 1   # 168hours in total can be set. this means weather will be forecasted for the next forecast_horizon hours. 25 is the min required as it is forecasting for the 24 h + 15 min next hours
sub_cost = 0
n_flanks_HP = 600
n_flanks_CHP = 400
n_flanks_CCM = 400
n_flanks_AdCM = 400
min_runtime = 4
#filename = 'HO_Summer_2_Weeks_EPEX_2018.06.28.xlsx'
filename ='HO_Summer_2_Weeks_EPEX_2018.06.28.xlsx'
   ## ---------------start the load depending on the hour----------
#st = datetime.now().time().hour*dt + int(datetime.now().time().minute/(60/dt))
st=0


#%%  Define number of iterations to solve  

#""" --------------------------------------Start the solving iteration loop------------------------------------------------"""
#"""-----------------------------------------------------------------------------------------------------------------------"""


    ##---------------variable declaration of the looping-------------------
i=0
steps = 24*7


#while True:                   # Solve for an undefined time.
while i != steps:              # To solve for the amount of time steps defined
#while i != ((m-st)-n):        #To solve for the whole forecast horizon      ##---- This means to solve for n horizon (24 hrs[96- 15mins], 48 hrs, etc.) within a m total horizon (1 week, 2 weeks... etc) a total of m-n times in a loop    
#%%       
    ##----------------Define the incomming variables------------------
        
    start_time = time.time()
    date = datetime.now()
    solv_error = None
    
    print('CPU_Clock_Time',date.time())
    
    
    """------ Retrieve data from excel ----"""
    Pth_Load_Heat_File,Pth_Load_Cool_File,Time,Pel_Load,epex_price_buy,epex_price_sell,T_Amb = read_excel(filename)      #Read excel file
    Pth_Load_Heat_File,Pth_Load_Cool_File,Pel_Load,T_Amb,Time,C_El_B,C_El_S,C_FUEL,m = interpolate_values(dt,Pth_Load_Heat_File,Pth_Load_Cool_File,Pel_Load,T_Amb,Time,epex_price_buy,epex_price_sell,Fuel)     #interpolate the values and give them back
   
    """------ Retrieve load data from sps + correction ----"""
    if real:
        real_load = ReadSPS("LOAD_HC_W_PT_M___")
    else:
        real_load = None
        

    Pth_Load_Heat, Pth_Load_Cool = correction_load(i,st,Pth_Load_Heat_File,Pth_Load_Heat,Pth_Load_Cool_File,Pth_Load_Cool,real_load)
     
    
    """------ Reset flanks ----"""
    
    if i%n == 0:                                      # Each 96 iterations reset flanks to defined values
        n_switching_CHP = n_flanks_CHP        
        n_switching_HP = n_flanks_HP
        n_switching_CCM = n_flanks_CCM        
        n_switching_AdCM = n_flanks_AdCM
        
    if real:                                          # If running real mode, read from sps the initial value
        T_HTES_init_0 =ReadSPS("HTES_H_W_T_M_IT_"+str(1)+"_") + 273.15
        T_CTES_init_0 =ReadSPS("CTES_H_W_T_M_IT_"+str(1)+"_") + 273.15
    """------ Electricity Forecast ----""" 
    try:
        
        da_buy15, da_sell15 = epexdata(dt,n,date)
        Par_C_El_B = da_buy15                            # updating the parameter acccording to where we want to start
        Par_C_El_S = da_sell15
        print('epex read')
    except:
        solv_error = 'EPEX_not_available'
        Par_C_El_B = C_El_B[0+i+st:(n-1)+i+st]            # updating the parameter acccording to where we want to start
        Par_C_El_S = C_El_S[0+i+st:(n-1)+i+st]
#        mqtt_kwkk.mqtterror(solv_error)
    
    EPEX_buy_list.append(Par_C_El_B[0])
    EPEX_sell_list.append(Par_C_El_S[0])
    
    
    """------ Temperature forecast ----""" 
     ##------ call the forecast up to "forecast_horizon" times, transform it to 15 min intevals and append each one to the last forecast ´+ 1 step. Also first hour is same as real Aux_Tamb value
    if real:
        sps_temp = ReadSPS("AUX_HC_A_T_M___")
    else:
        sps_temp = None
    T_Amb_Fore_C, T_Amb_Forec_real = T_amb_forecast(forecast_horizon,i,T_Amb_f_15,m,sps_temp)
    T_Amb_f_15 = pl.append(T_Amb_f_15[:i],interpolate(dt,T_Amb_Fore_C))
    T_Amb_Forec_real_15 = pl.append(T_Amb_Forec_real_15[:i],interpolate(dt,T_Amb_Forec_real))

    """------ Parameters ----"""
      #------ define the parameter values that will change trhougth time---
    Par_T_Amb_bin = binarytransform(T_HP_min, T_Amb_f_15[0+i:(n-1)+i])
    Par_Load_El = Pel_Load[0+i+st:(n-1)+i+st]
    Par_Load_Th = Pth_Load_Heat[0+i+st:(n-1)+i+st] 
    Par_Load_Th_File =Pth_Load_Heat_File[0+i+st:(n-1)+i+st] 
    Par_Load_C = Pth_Load_Cool[0+i+st:(n-1)+i+st]

     
    """------ Create the optimization model from function ----"""
    try:    
        model = kwkk_opt(n, dt, n_switching_CHP, n_switching_HP, min_runtime, Par_C_El_B, Par_C_El_S, Par_T_Amb_bin, Par_Load_El, Par_Load_Th, Par_Load_C, T_HP_max, T_HP_min, T_AdCM_min, LS_CHP_S, LS_HP_S, LS_CCM_S, LS_AdCM_S)
        print("Initial Temp = ",T_HTES_init_0-273.15)
        print("iteration No.= ",i) 
        print("N_Switch_CHP.= ",n_switching_CHP)
        print("N_Switch_HP.= ",n_switching_HP)
    
        
        """---------------- Optimize the model ------------------"""
           
        model.setRealParam('limits/time',30)               # for limiting to n sec sec the solving time
        model.optimize()                                   # optimize the model
    except:
        solv_error = 'Solving_error'
#        mqtt_kwkk.mqtterror(solv_error)
#        break
        
    
       ##----extract the variables from the model
    
    Pel_CHP, Pgrid_B, Pgrid_S, Pth_COIL, Pth_HP, Pth_CHP, V_FUEL, CHP_bin, COIL_bin, HP_bin, CCM_bin, AdCM_bin, T_HTES, CHP_S_bin, HP_S_bin, CCM_S_bin, AdCM_S_bin, Pel_CCM, Pel_AdCM, Pel_AUX, Pel_OC, Pth_CCM, Pth_AdCM_HT, Pth_AdCM_LT, T_CTES = model.data
        
#    Pel_CHP, Pgrid_B, Pgrid_S, Pth_COIL, Pth_HP, Pth_CHP, V_FUEL, CHP_bin, COIL_bin, HP_bin, T_HTES, CHP_S_bin, HP_S_bin = model.data
     
    """------ Optimal variables ----"""
       ##---Retrieve the  values of each optimization and append them as the optimal values----.
   
    P_El_CHP_opt = pl.array([model.getVal(Pel_CHP[j]) for j in range(min_runtime,(n-1)+min_runtime)])*dt    
    P_El_CCM_opt = pl.array([model.getVal(Pel_CCM[j]) for j in range(min_runtime,(n-1)+min_runtime)])*dt
    P_El_AdCM_opt = pl.array([model.getVal(Pel_AdCM[j]) for j in range(min_runtime,(n-1)+min_runtime)])*dt
    P_El_AUX_opt = pl.array([model.getVal(Pel_AUX[j]) for j in range(min_runtime,(n-1)+min_runtime)])*dt
    P_El_OC_opt = pl.array([model.getVal(Pel_OC[j]) for j in range(min_runtime,(n-1)+min_runtime)])*dt  
    Pgrid_B_opt = pl.array([model.getVal(Pgrid_B[j]) for j in range(min_runtime,(n-1)+min_runtime)])*dt
    Pgrid_S_opt = pl.array([model.getVal(Pgrid_S[j]) for j in range(min_runtime,(n-1)+min_runtime)])*dt
    Pth_COIL_opt = pl.array([model.getVal(Pth_COIL[j]) for j in range(min_runtime,(n-1)+min_runtime)])*dt
    Pth_HP_opt = pl.array([model.getVal(Pth_HP[j]) for j in range(min_runtime,(n-1)+min_runtime)])*dt
    Pth_CHP_opt = pl.array([model.getVal(Pth_CHP[j]) for j in range(min_runtime,(n-1)+min_runtime)])*dt
    Pth_AdCM_HT_opt = pl.array([model.getVal(Pth_AdCM_HT[j]) for j in range(min_runtime,(n-1)+min_runtime)])*dt
    Pth_AdCM_LT_opt = pl.array([model.getVal(Pth_AdCM_LT[j]) for j in range(min_runtime,(n-1)+min_runtime)])*dt
    Pth_CCM_opt = pl.array([model.getVal(Pth_CCM[j]) for j in range(min_runtime,(n-1)+min_runtime)])*dt
    V_FUEL_opt = pl.array([model.getVal(V_FUEL[j]) for j in range(min_runtime,(n-1)+min_runtime)])
    
    CHP_bin_opt = pl.array([model.getVal(CHP_bin[j]) for j in range(min_runtime,(n-1)+min_runtime)])
    COIL_bin_opt = pl.array([model.getVal(COIL_bin[j]) for j in range(min_runtime,(n-1)+min_runtime)])
    HP_bin_opt = pl.array([model.getVal(HP_bin[j]) for j in range(min_runtime,(n-1)+min_runtime)])
    CCM_bin_opt = pl.array([model.getVal(CCM_bin[j]) for j in range(min_runtime,(n-1)+min_runtime)])
    AdCM_bin_opt = pl.array([model.getVal(AdCM_bin[j]) for j in range(min_runtime,(n-1)+min_runtime)])
    
    T_HTES_opt = pl.array([model.getVal(T_HTES[j]) for j in range(min_runtime,(n)+min_runtime)])
    T_CTES_opt = pl.array([model.getVal(T_CTES[j]) for j in range(min_runtime,(n)+min_runtime)])
    
    
    E_El_HP_opt = Pth_HP_opt*(1./COP_HP)
    E_El_COIL_opt = Pth_COIL_opt*(1./Pth_eff_COIL)

       ##-----Save the first optimal actions from each optimal solution for printing the whole optimal actions in time.----
        
#    Step_Pel_CHP.append(P_El_CHP_opt[0])
    Step_Pgrid_B.append(Pgrid_B_opt[0])
    Step_Pgrid_S.append(Pgrid_S_opt[0])
#    Step_Pth_COIL.append(Pth_COIL_opt[0])
#    Step_Pth_HP.append(Pth_HP_opt[0])
#    Step_Pth_CHP.append(Pth_CHP_opt[0])
#    Step_V_FUEL.append(V_FUEL_opt[0])
    Step_CHP_bin.append(CHP_bin_opt[0])
    Step_COIL_bin.append(COIL_bin_opt[0])
    Step_HP_bin.append(HP_bin_opt[0])
    Step_AdCM_bin.append(AdCM_bin_opt[0])
    Step_CCM_bin.append(CCM_bin_opt[0])
    Step_T_HTES.append(T_HTES_opt[0])
    Step_T_CTES.append(T_CTES_opt[0])

    
    if i == 0:
         Stepplus_T_HTES.append(T_HTES_opt[0])
         Stepplus_T_CTES.append(T_CTES_opt[0])
    Stepplus_T_HTES.append(T_HTES_opt[1])
    Stepplus_T_CTES.append(T_CTES_opt[1])

    
    
    LS_CHP_S = pl.delete(pl.append(LS_CHP_S,pl.array([model.getVal(CHP_bin[0+min_runtime])])),0)       # part to append optimal control value to past four and delete first value of the past four. Acts like shifing mechanism
    LS_HP_S  = pl.delete(pl.append(LS_HP_S ,pl.array([model.getVal( HP_bin[0+min_runtime])])),0)
    LS_CCM_S = pl.delete(pl.append(LS_CCM_S,pl.array([model.getVal(CCM_bin[0+min_runtime])])),0)       # part to append optimal control value to past four and delete first value of the past four. Acts like shifing mechanism
    LS_AdCM_S = pl.delete(pl.append(LS_AdCM_S,pl.array([model.getVal(AdCM_bin[0+min_runtime])])),0)       # part to append optimal control value to past four and delete first value of the past four. Acts like shifing mechanism

#    LS_CHP_ON_S = pl.array([model.getVal(CHP_ON_bin[0+min_runtime])])
#    LS_HP_ON_S  = pl.array([model.getVal( HP_ON_bin[0+min_runtime])])
#    HP_S_opt = pl.array([model.getVal(HP_S_bin[j]) for j in range(min_runtime,(n-1)+min_runtime)])
#    CHP_S_opt = pl.array([model.getVal(CHP_S_bin[j]) for j in range(min_runtime,(n-1)+min_runtime)])

            
    if n_switching_CHP == 0:
        pass
    else:
        if model.getVal(CHP_S_bin[0+min_runtime]) == 1:
            n_switching_CHP = n_switching_CHP - 1

    if n_switching_HP == 0:
        pass
    else:
        if model.getVal(HP_S_bin[0+min_runtime]) == 1:
            n_switching_HP = n_switching_HP - 1
 
        ##---Get the cost of the model each time at k = 0 and add it to the sub_total. Sub_total means from 0 to (m-n)
        
    step_cost = (Par_C_El_B[0]*Pgrid_B_opt[0]) + (C_FUEL*V_FUEL_opt[0]) - (Par_C_El_S[0]*Pgrid_S_opt[0])
    sub_cost = sub_cost + step_cost
   
        ##---Retrieve the optimal mode... then send it to the SPS by the WriteSPS(opt_mode, COIL_Switch) function.
        
    optimal_mode = optmode(HP_bin_opt[0],CHP_bin_opt[0], CCM_bin_opt[0], AdCM_bin_opt[0])
    
    print('Solv Time=',str(model.getSolvingTime()))
    print('Total Time=',str(model.getTotalTime()))
   
    if real:
        pass
#        WriteSPS(optimal_mode, COIL_bin_opt[0]) #-->activate to set the optimal mode and coil switch on the sps 
    WriteExcel('SIMULATION_OPT_17_07_iter_HO_summ_2.xlsx',Step_Pgrid_B,Step_Pgrid_S,Step_CHP_bin,Step_HP_bin,Step_COIL_bin,Step_T_HTES, Step_T_CTES, Step_CCM_bin, Step_AdCM_bin, T_Amb_f_15[:i+1], T_Amb_Forec_real_15[:i+1], Pth_Load_Heat[:i+1], Pth_Load_Cool[:i+1], EPEX_buy_list, EPEX_sell_list)
#    plotall(Time[0+i+st:(n-1)+i+st], 1 ,dt,Par_Load_Th,Pth_CHP_opt,Pth_HP_opt,Pth_COIL_opt, Par_C_El_B,Par_C_El_S,E_El_HP_opt,E_El_COIL_opt,Par_Load_El,Pgrid_B_opt,Pgrid_S_opt,P_El_CHP_opt,T_HTES_opt,T_Amb_f_15[0+i:(n-1)+i],T_HP_min,COIL_bin_opt,CHP_bin_opt,HP_bin_opt,T_Amb_Forec_real_15[0+i:(n-1)+i],Par_Load_Th_File,Par_Load_C, P_El_AUX_opt, P_El_CCM_opt, P_El_AdCM_opt, Pth_AdCM_HT_opt, Pth_AdCM_LT_opt, P_El_OC_opt, Pth_CCM_opt, CCM_bin_opt, AdCM_bin_opt)
#    plotTdev(Step_T_HTES, Stepplus_T_HTES,0,'*')
#    mqtt_kwkk.mqttsend(Par_Load_Th,Pth_CHP_opt,Pth_HP_opt,Pth_COIL_opt, Par_C_El_B,T_HTES_opt,T_Amb_f_15[0+i:(n-1)+i],COIL_bin_opt,CHP_bin_opt,HP_bin_opt,Step_T_HTES[0:], Stepplus_T_HTES[0:-1])

        ##---iterate waiting timepause miniutes----
        
    end_time =time.time()
    solv_time = (end_time-start_time)
       


    time_correction = ((sampling_time - (((int(datetime.now().time().minute/(60/dt))+1)*(60/dt))-(datetime.now().time().minute)))*60)+datetime.now().second
    solv_time = 0 

#    time.sleep((sampling_time*60)-solv_time-time_correction)

    
           ##---Set the new value of the initial temperature. This is done for test purposes on the optimized value.
    if real:
        pass
    else:
        T_HTES_init_0 = model.getVal(T_HTES[1+min_runtime])
        T_CTES_init_0 = model.getVal(T_CTES[1+min_runtime])
    
    
    print(model.getObjVal())
    i =i+1
        
""" ------------------------------------- End of the loop, rest of calculations ------------------------------------------"""
"""-----------------------------------------------------------------------------------------------------------------------"""

#    ##---Calculate the total costs
#
#cost = model.getObjVal()
#Total_cost = cost + sub_cost - step_cost  # total cost = cost each 0 step, + cost of the last iteration. Because the last 0step ist summed in the last vector, it is then substracted.
#
#    ##----add the previous step optimal values to the last ones and make a list for printing the whole time horizon.   
#
#P_El_CHP_opt = pl.append(Step_Pel_CHP[0:(i-1)], P_El_CHP_opt)
#Pth_HP_opt = pl.append(Step_Pth_HP[0:(i-1)], Pth_HP_opt)
#E_El_HP_opt = Pth_HP_opt*(1./COP_HP)
#Pth_COIL_opt= pl.append(Step_Pth_COIL[0:(i-1)], Pth_COIL_opt)
#E_El_COIL_opt = Pth_COIL_opt*(1./Pth_eff_COIL)
#Pth_CHP_opt =  pl.append(Step_Pth_CHP[0:(i-1)], Pth_CHP_opt)
#HP_bin_opt =  pl.append(Step_HP_bin[0:(i-1)], HP_bin_opt)
#COIL_bin_opt =  pl.append(Step_COIL_bin[0:(i-1)], COIL_bin_opt)
#CHP_bin_opt =  pl.append(Step_CHP_bin[0:(i-1)], CHP_bin_opt)
#Pgrid_B_opt = pl.append(Step_Pgrid_B[0:(i-1)],Pgrid_B_opt)
#Pgrid_S_opt = pl.append(Step_Pgrid_S[0:(i-1)],Pgrid_S_opt)
#T_HTES_opt = pl.append(Step_T_HTES[0:(i-1)],T_HTES_opt)
#
#     ##----apply the last n-2 hours for the last optimization in fixed time hoizon applications.   
#     
##for lastv in range(n-1):
##    optimal_mode = optmode(HP_bin_opt[i+lastv],CHP_bin_opt[i+lastv])
##    #WriteSPS(optimal_mode, COIL_bin_opt[i]) #-->activate to set the optimal mode and coil switch on the sps 
##    time.sleep((sampling_time*60)-solv_time-time_correction)
#
#
#
#print('--------------------------- Total time plot -------------------------')
#print('---------------------------------------------------------------------')
#
#plotall(Time[0+st:], i,dt,Pth_Load_Heat[0+st:],Pth_CHP_opt,Pth_HP_opt,Pth_COIL_opt,C_El_B[0+st:],C_El_S[0+st:],E_El_HP_opt,E_El_COIL_opt,Pel_Load[0+st:],Pgrid_B_opt,Pgrid_S_opt,P_El_CHP_opt,T_HTES_opt,T_Amb_f_15,T_HP_min,COIL_bin_opt,CHP_bin_opt,HP_bin_opt,T_Amb_Forec_real_15,Pth_Load_Heat_File[0+st:])
#plotTdev(Step_T_HTES, Stepplus_T_HTES,0,'-')
#
#print('Total_Obj=',Total_cost)
#print('Solv Time=',str(model.getSolvingTime()))
#print('Total Time=',str(model.getTotalTime()))
#print('Nodes=',str(model.getNNodes()))


