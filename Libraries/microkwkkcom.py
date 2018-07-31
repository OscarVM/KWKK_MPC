# -*- coding: utf-8 -*-
"""
Created on Fri Mar  3 14:56:08 2017

@author: PXI-PC
"""


from opcua import Client # import opcua library
from opcua import ua


class microKWKKcom(object): 
    
    variables_location = ["0:Objects", "4:PLC1", "4:GVL_OPC_Variablen"]
    
    devices = {
        "CHP_H_W_Q_M___": "4:QthChp",
        "CHP_H_W_PT_M___": "4:PthChp",
        "CHP_H_W_VF_M___": "4:VdotChp",
        "CHP_H_W_T_M__FL_": "4:TflChp",
        "CHP_H_W_T_M__RL_": "4:TrlChp",
        "CHP_H_W_dT_M___": "4:VHmChp",
        "CHP_H_E_PE_M___": "4:PelChp",
        "CHP_H_F_VF_M___": "4:VdotFuel",
        "CHP_H_F_IMP_M___": "4:VdotFuelImp",
        "CHP_H_W_B_O___": "4:OnChp",
        "CHP_H_E_B_O___": "4:OnVoltageChp",
        "CHP_H_E_Q_M__FL_": "4:QelChpIn",
        "CHP_H_E_Q_M__RL_": "4:QelChpOut",
        "ADCM_C_W_Q_M_LT__": "4:QthAdcmLt",
        "ADCM_C_W_PT_M_LT__": "4:PthAdcmLt",
        "ADCM_C_W_VF_M_LT__": "4:VdotAdcmLt",
        "ADCM_C_W_T_M_LT_FL_": "4:TflAdcmLt",
        "ADCM_C_W_T_M_LT_RL_": "4:TrlAdcmLt",
        "ADCM_C_W_dT_M_LT__": "4:VHmAdcmLt",
        "ADCM_C_W_Q_M_MT__": "4:QthAdcmMt",
        "ADCM_C_W_PT_M_MT__": "4:PthAdcmMt",
        "ADCM_C_W_VF_M_MT__": "4:VdotAdcmMt",
        "ADCM_C_W_T_M_MT_FL_": "4:TflAdcmMt",
        "ADCM_C_W_T_M_MT_RL_": "4:TrlAdcmMt",
        "ADCM_C_W_dT_M_MT__": "4:VHmAdcmMt",
        "ADCM_C_W_Q_M_HT__": "4:QthAdcmHt",
        "ADCM_C_W_PT_M_HT__": "4:PthAdcmHt",
        "ADCM_C_W_VF_M_HT__": "4:VdotAdcmHt",
        "ADCM_C_W_T_M_HT_FL_": "4:TflAdcmHt",
        "ADCM_C_W_T_M_HT_RL_": "4:TrlAdcmHt",
        "ADCM_C_W_dT_M_HT__": "4:VHmAdcmHt",
        "ADCM_C_E_PE_M___": "4:PelAdcm",
        "ADCM_C_W_B_O___": "4:OnAdcm",
        "ADCM_C_W_TSET_O_LT__": "4:TsetAdcm",
        "ADCM_C_W_VSET_M_MT__": "4:VAdcmCt",
        "RevHP_HC_W_Q_M_LT__": "4:QthCcmLt",
        "RevHP_HC_W_PT_M_LT__": "4:PthCcmLt",
        "RevHP_HC_W_VF_M_LT__": "4:VdotCcmLt",
        "RevHP_HC_W_T_M_LT_FL_": "4:TflCcmLt",
        "RevHP_HC_W_T_M_LT_RL_": "4:TrlCcmLt",
        "RevHP_HC_W_dT_M_LT__": "4:VHmCcmLt",
        "RevHP_HC_W_Q_M_MT__": "4:QthCcmCkd",
        "RevHP_HC_W_PT_M_MT__": "4:PthCcmCkd",
        "RevHP_HC_W_VF_M_MT__": "4:VdotCcmCkd",
        "RevHP_HC_W_T_M_MT_FL_": "4:TflCcmCkd",
        "RevHP_HC_W_T_M_MT_RL_": "4:TrlCcmCkd",
        "RevHP_HC_W_dT_M_MT__": "4:VHmCcmCkd",
        "RevHP_HC_E_PE_M___": "4:PelCcm",
        "RevHP_HC_W_B_O___": "4:OnCcm",
        "RevHP_C_W_B_O___": "4:CoolingCcm",
        "OC_HC_B_Q_M___": "4:QthCt",
        "OC_HC_B_PT_M___": "4:PthCt",
        "OC_HC_B_VF_M___": "4:VdotCt",
        "OC_HC_B_T_M__FL_": "4:TrlCt",
        "OC_HC_B_T_M__RL_": "4:TflCt",
        "OC_HC_B_dT_M___": "4:VHmCt",
        "OC_HC_E_PE_M___": "4:PelCt",
        "OC_HC_B_B_O___": "4:OnCt",
        "OC_HC_B_PSET_O___": "4:VsetCt",
        "OC_HC_E_B_O___": "4:ModeCt",
        "LOAD_HC_W_Q_M___": "4:QthLoad",
        "LOAD_HC_W_PT_M___": "4:PthLoad",
        "LOAD_HC_W_VF_M___": "4:VdotLoad",
        "LOAD_HC_W_T_M__FL_": "4:TflLoad",
        "LOAD_HC_W_T_M__RL_": "4:TrlLoad",
        "LOAD_HC_W_dT_M___": "4:VHmLoad",
        "PU_HC_B_B_O_MT__": "4:OnP5AdcmMt",
        "PU_HC_W_B_O_LT_RevHp_": "4:OnP6CcmLt",
        "PU_HC_W_B_O_MT_RevHp_": "4:OnP7CcmMt",
        "PU_H_W_B_O__MX_": "4:OnP8HtesCtes",
        "PU_H_W_B_O_MT_HTES_": "4:OnP11Htes",
        "PU_H_W_B_O_IT_HTES_": "4:OnP12Htes",
        "PU_H_W_B_O_HT_RevHP_": "4:OnP13RevHpW2",
        "HTES_H_W_T_M_IT_1_": "4:HT01",
        "HTES_H_W_T_M_IT_2_": "4:HT02",
        "HTES_H_W_T_M_IT_3_": "4:HT03",
        "HTES_H_W_T_M_IT_4_": "4:HT04",
        "HTES_H_W_T_M_IT_5_": "4:HT05",
        "HTES_H_W_T_M_IT_6_": "4:HT06",
        "HTES_H_W_T_M_IT_7_": "4:HT07",
        "HTES_H_W_T_M_IT_8_": "4:HT08",
        "HTES_H_W_T_M_IT_9_": "4:HT09",
        "CTES_C_W_T_M_IT_1_": "4:CT01",
        "CTES_C_W_T_M_IT_2_": "4:CT02",
        "CTES_C_W_T_M_IT_3_": "4:CT03",
        "CTES_C_W_T_M_IT_4_": "4:CT04",
        "COIL_H_W_B_O_IT__": "4:OnCoil",
        "COIL_H_E_PE_M___": "4:PelCoil",
        "ASL_H_W_B_O_IT_FL_": "4:LeftAsl",
        "ASL_H_W_B_O_IT_RL_": "4:RightAsl",
        "ASL_H_W_T_M_IT_FL_": "4:AslTcl",
        "SV_HC_W_B_O__FL_": "4:OpenSo1",
        "SV_HC_W_B_O__RL_": "4:OpenSo2",
        "MV_HC_W_B_O_FL_1_": "4:OpenMv1",
        "MV_HC_W_B_O_FL_2_": "4:OpenMv2",
        "MV_HC_W_B_O_RL_1_": "4:CloseMv1",
        "MV_HC_W_B_O_RL_2_": "4:CloseMv2",
        "AUX_HC_E_PE_M___": "4:PelAux",
        "AUX_HC_A_T_M___": "4:Tamb",
        "KWKK_SPStime": "4:SPSzeit",
        "KWKK_SPSrun": "4:SPSrun",
        "KWKK_CtrlMode": "4:OpModeAuto",
        "NotAusAktiv": "4:NotAusAktiv",
        "Optimal_Mode": "4:Optimal_Mode"

            }
    
    def __init__(self, server_address = None, server_port = None):
        
        self.server_address = server_address
        self.server_port = server_port
        
        self.client = Client("opc.tcp://" +str(self.server_address) + ":" + \
                             str(self.server_port))
        self.client.connect()
        
        self.root = self.client.get_root_node()
        
    def __del__(self):
        
        self.client.disconnect()
        
        
    def set_value(self, device = "",  value = ""):
        
        """
        Assign a value to the specified device listed on the dictionary (use labview name)
        These values have to match the data type set on the PLC (SPS). eg. float, UInt16, etc.
        The SPS can recieve either a variant or a datavalue variable, but it seems to accept 
        more the Datavalue as in Set_Value, therefore its better to send it this way.
        Refer to uatypes.py for more information regarding variant types. 
        the Timestamp also on uatypes.py has to be set to 0 or none.
        https://github.com/FreeOpcUa/python-opcua/issues/9
              
        """
        
        child = self.root.get_child(self.variables_location + \
                                    [self.devices[str(device)]])
        
        if isinstance(value, float):
        
            dv = ua.DataValue(ua.Variant(float(value), ua.VariantType.Float))
        elif isinstance(value, bool):
            dv = ua.DataValue(ua.Variant(bool(value), ua.VariantType.Boolean))
        else: print('At the moment Bool and Float variant types are accepted, for adding'
                    'an extra type please refer to microkwkkcom.py document')
        
        child.set_value(dv)
        

        value = child.get_value()
        
        return {device: value}
        

    def get_value(self, device = ""):
        
        """
        Retrieve the value from the listed device contained on the dictionary
              
        """
        
        child = self.root.get_child(self.variables_location + \
                                    [self.devices[str(device)]])
        value = child.get_value()
        
        return {device: value}
    

    def get_all_values(self):
        
        """
        Retrieve the value from the listed device contained on the dictionary
              
        """
        
        values = {}
        
        for device in self.devices:
            
            values.update(self.get_value(device = device))
            
        return values
