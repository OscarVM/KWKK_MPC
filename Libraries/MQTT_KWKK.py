# -*- coding: utf-8 -*-
"""
Created on Tue Jun 26 10:49:22 2018

@author: Oscar VM
"""
import paho.mqtt.client as mqtt #import the client1
import json
import pylab as pl

class mqtt_kwkk:
    
    def mqttsend(Par_Load_Th,Pth_CHP_opt,Pth_HP_opt,Pth_COIL_opt, Par_C_El_B,T_HTES_opt,T_Amb_f_15,COIL_bin_opt,CHP_bin_opt,HP_bin_opt,Step_T_HTES, Stepplus_T_HTES):
    
            Load_Actual = "LOAD"
            Load_graph =  "LOAD/graph"
            Elec_cost =   "ELECT/graph"
            CHP       =   "CHP/status"
            CHP_graph =   "CHP/graph"
            HP        =   "HP/status"
            HP_graph  =   "HP/graph"
            COIL      =   "COIL/status"
            COIL_graph =  "COIL/graph"
            T_amb      =   "TEMP/TAMB/graph"
            T_init      =  "TEMP/TANK/init"
            T_OPT       =  "TEMP/TANK/graph"
            T_Real      =  "TEMP/TANK/real"
            T_Predicted =  "TEMP/TANK/predict"
            CHP_load    =  "CHP/load"
            HP_load     =  "HP/load"
            COIL_load   =  "COIL/load"
            
            LOAD_ACTUAL= str(Par_Load_Th[0])
            LOAD_GRAPH = json.dumps(pl.flip(Par_Load_Th,0).tolist())
            ELEC_COST = json.dumps(pl.flip(Par_C_El_B,0).tolist())
            CHP_STATUS = int(CHP_bin_opt[0])
            CHP_GRAPH = json.dumps(pl.flip(CHP_bin_opt,0).tolist())
            HP_STATUS = int(HP_bin_opt[0])
            HP_GRAPH = json.dumps(pl.flip(HP_bin_opt,0).tolist())
            COIL_STATUS = int(COIL_bin_opt[0])
            COIL_GRAPH = json.dumps(pl.flip(COIL_bin_opt,0).tolist())
            T_AMB = json.dumps(pl.flip(T_Amb_f_15,0).tolist())
            T_INIT = str(T_HTES_opt[0]-273.15)
            T_GRAH = json.dumps(pl.flip((T_HTES_opt-273.15),0).tolist())
            T_REAL = json.dumps(pl.flip(Step_T_HTES,0).tolist())
            T_PRED = json.dumps(pl.flip(Stepplus_T_HTES,0).tolist())
            CHP_LOAD = json.dumps(pl.flip(Pth_CHP_opt,0).tolist())
            HP_LOAD  = json.dumps(pl.flip(Pth_HP_opt,0).tolist())
            COIL_LOAD = json.dumps(pl.flip(Pth_COIL_opt,0).tolist())
               
            
        
            #broker_address="192.168.1.184" 
            broker_address="broker.shiftr.io"
            user = "Oscar_VM_access"
            passw = "2dcd155aa662458f"
    #            print("creating new instance")
            client = mqtt.Client("Status") #create new instance
    #            print("connecting to broker")
            client.username_pw_set(user,passw)
            client.connect(broker_address) #connect to broker
       
            client.publish(Load_Actual,LOAD_ACTUAL,retain = True) 
            client.publish(Load_graph,LOAD_GRAPH,retain = True) 
            client.publish(Elec_cost,ELEC_COST,retain = True)
            client.publish(CHP,CHP_STATUS,retain = True) 
            client.publish(CHP_graph,CHP_GRAPH,retain = True) 
            client.publish(HP,HP_STATUS,retain = True) 
            client.publish(HP_graph,HP_GRAPH,retain = True)
            client.publish(COIL,COIL_STATUS,retain = True) 
            client.publish(COIL_graph,COIL_GRAPH,retain = True)
            client.publish(T_amb,T_AMB,retain = True)
            client.publish(T_init,T_INIT,retain = True) 
            client.publish(T_OPT,T_GRAH,retain = True) 
            client.publish(T_Real,T_REAL,retain = True) 
            client.publish(T_Predicted,T_PRED,retain = True)
            client.publish(CHP_load,CHP_LOAD,retain = True)
            client.publish(HP_load,HP_LOAD,retain = True)
            client.publish(COIL_load,COIL_LOAD,retain = True)
            client.publish(COIL_load,COIL_LOAD,retain = True)
            client.disconnect()
    
    
    def mqtterror(solv_error):
        
            Error       =  "ERROR"
        
            ERROR = str(solv_error)    
        
            broker_address="broker.shiftr.io"
            user = "Oscar_VM_access"
            passw = "2dcd155aa662458f"
            client = mqtt.Client("Status") #create new instance
            client.username_pw_set(user,passw)
            client.connect(broker_address) #connect to broker

            if solv_error == None:
                pass
            else:    
                client.publish(Error,ERROR,retain = True)
        
            client.disconnect()
