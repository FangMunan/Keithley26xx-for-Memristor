#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
srdp_tester.py

Spike-Rate-Dependent Plasticity test.
Saves output under: .../YYYYMMDD/srdp_tester/<timestamp_salt_conc_dev_params>/
English UI with Chinese comments, auto-increment filenames, etc.
"""

import os
import time
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

from core import MemristorTester

class SrdpTester(MemristorTester):
    def __init__(self, keithley):
        super().__init__(keithley)
        self.off_time=0.0001
        self.nplc=1
        self.pulse_width=0.2
        self.pulse_num=10
        self.V_read=0.1
        self.V_write=1.0
        self.space_arrays=[
            [20,2,0.2,2],
            [20,5,0.2,5],
            [20,1,0.2,1],
            [20,2,0.1,2],
        ]
        self.current_space_array_index=0
        self.off_time_array=[0.0001,0.01,0.1,1]
        self.pulse_width_array=[0.1,0.2,0.5]
        self.ltm_read_time_before=60
        self.ltm_pulse_count=50
        self.ltm_read_time_after=600

        self.time_values=[]
        self.voltage_values=[]
        self.current_values=[]
        self.conductance_values=[]

    def setup_test_parameters(self):
        self.setup_device_info()
        print("\nCurrent test parameters:")
        print(f"off_time={self.off_time}, nplc={self.nplc}, pulse_width={self.pulse_width}, pulse_num={self.pulse_num}")
        print(f"V_read={self.V_read}, V_write={self.V_write}")
        if self.space_arrays:
            print(f"Current space array: {self.space_arrays[self.current_space_array_index]}")
        ans=input("Modify default? (y/n): ").strip().lower()
        if ans=='y':
            try:
                self.off_time=float(input(f"Off time (default {self.off_time}): ").strip() or self.off_time)
                self.nplc=float(input(f"NPLC (default {self.nplc}): ").strip() or self.nplc)
                self.pulse_width=float(input(f"Pulse width (default {self.pulse_width}): ").strip() or self.pulse_width)
                self.pulse_num=int(input(f"Pulse number (default {self.pulse_num}): ").strip() or self.pulse_num)
                self.V_read=float(input(f"Read voltage (default {self.V_read}): ").strip() or self.V_read)
                self.V_write=float(input(f"Write voltage (default {self.V_write}): ").strip() or self.V_write)
            except ValueError:
                print("[Warning] invalid input")

    def _reset_and_setup_keithley(self):
        self.keithley.reset_device()
        self.keithley.default_setup()
        self.keithley.source_function='voltage'
        self.keithley.level_i=0
        self.keithley.limit_i=1e-7
        self.keithley.nplc=self.nplc
        self.keithley.output=True

    def run_srdp_test(self, space_array):
        self._reset_and_setup_keithley()
        data=[]
        start_time=time.time()

        for idx,space_val in enumerate(space_array):
            print(f"[Info] Using space={space_val}s, pulses={self.pulse_num}")
            for p_idx in range(self.pulse_num):
                # read
                self.keithley.level_v=self.V_read
                time.sleep(self.pulse_width)
                i_read,v_read=self.keithley.measure_iv()
                t_read=time.time()-start_time
                data.append([t_read,v_read,i_read,f"read_{idx+1}-{p_idx+1}"])

                self.keithley.output=False
                time.sleep(self.off_time)
                self.keithley.output=True

                # write
                self.keithley.level_v=self.V_write
                time.sleep(self.pulse_width)
                i_write,v_write=self.keithley.measure_iv()
                t_write=time.time()-start_time
                data.append([t_write,v_write,i_write,f"write_{idx+1}-{p_idx+1}"])

                if p_idx<self.pulse_num-1:
                    self.keithley.output=False
                    time.sleep(self.off_time)
                    self.keithley.output=True
                    time.sleep(space_val)

        self.keithley.output=False

        if data:
            t0=data[0][0]
            for row in data:
                row[0]-=t0
        return np.array(data,dtype=object)

    def run_ltm_test(self, space_values):
        self._reset_and_setup_keithley()
        data=[]
        start_time=time.time()

        # simple example only
        for idx,space_val in enumerate(space_values):
            print(f"[Info] LTM space={space_val}, pulses={self.ltm_pulse_count}")
            for p_idx in range(self.ltm_pulse_count):
                self.keithley.level_v=self.V_write
                time.sleep(self.pulse_width)
                i_write,v_write=self.keithley.measure_iv()
                t_now=time.time()-start_time
                data.append([t_now,v_write,i_write,f"ltm_write_{idx+1}-{p_idx+1}"])

                self.keithley.output=False
                time.sleep(self.off_time)
                self.keithley.output=True

                if p_idx<self.ltm_pulse_count-1:
                    time.sleep(space_val)

        self.keithley.output=False

        if data:
            t0=data[0][0]
            for row in data:
                row[0]-=t0
        return np.array(data,dtype=object)

    def process_measurement_data(self, data):
        df=pd.DataFrame(data,columns=["Time","Voltage","Current","Label"])
        read_mask=np.isclose(df["Voltage"],self.V_read,atol=0.01)
        read_data=df[read_mask].copy()
        read_data["Conductance"]=read_data["Current"]/self.V_read

        self.time_values=read_data["Time"].values
        self.voltage_values=read_data["Voltage"].values
        self.current_values=read_data["Current"].values
        self.conductance_values=read_data["Conductance"].values

        return (self.time_values,self.voltage_values,self.current_values,self.conductance_values)

    def plot_conductance_curve(self,t_vals,g_vals,save_path=None):
        if len(t_vals)==0:
            print("[Warning] no data to plot.")
            return
        plt.figure(figsize=(8,6))
        plt.plot(t_vals,g_vals,'b.-')
        plt.xlabel("Time(s)")
        plt.ylabel("Conductance(S)")
        plt.title("SRDP: Conductance vs Time")
        plt.grid(True)
        if save_path:
            plt.savefig(save_path,dpi=300)
            print(f"[Plot saved] {save_path}")
        plt.close()

    def run_test(self):
        print("\n=== [SRDP Test] starting ===")
        self.setup_test_parameters()

        suffix=f"off_{self.off_time}_pw_{self.pulse_width}_pnum_{self.pulse_num}"
        final_folder=self.prepare_save_folders("srdp_tester",suffix)
        print(f"[Info] All data in: {final_folder}")

        for idx,space_array in enumerate(self.space_arrays):
            self.current_space_array_index=idx
            print(f"\n=== Testing space_array#{idx+1}: {space_array}")
            srdp_data=self.run_srdp_test(space_array)
            raw_prefix=f"srdp_space_{idx+1}"
            self.save_data_csv(final_folder,raw_prefix,srdp_data)

            t_vals,v_vals,i_vals,g_vals=self.process_measurement_data(srdp_data)
            csv2=self.save_processed_data_csv(final_folder,raw_prefix,t_vals,v_vals,i_vals,g_vals)
            fig_path=os.path.join(final_folder,f"{raw_prefix}_conductance.png")
            self.plot_conductance_curve(t_vals,g_vals,fig_path)

        # optional LTM
        ans=input("\nRun LTM test? (y/n): ").strip().lower()
        if ans=='y':
            space_str=input("Enter space values for LTM test (comma separated): ").strip()
            if space_str:
                try:
                    space_vals=[float(x.strip()) for x in space_str.split(',')]
                except:
                    space_vals=[1.0]
            else:
                space_vals=[1.0]
            print(f"[Info] Running LTM test with {space_vals}")
            ltm_data=self.run_ltm_test(space_vals)
            self.save_data_csv(final_folder,"srdp_ltm_raw_data",ltm_data)
            t_vals,v_vals,i_vals,g_vals=self.process_measurement_data(ltm_data)
            self.save_processed_data_csv(final_folder,"srdp_ltm_data",t_vals,v_vals,i_vals,g_vals)
            fig_path=os.path.join(final_folder,"srdp_ltm_conductance.png")
            self.plot_conductance_curve(t_vals,g_vals,fig_path)

        print("\n=== [SRDP Test] done ===")
        return {
            'off_time':self.off_time,
            'pulse_width':self.pulse_width,
            'pulse_num':self.pulse_num,
            'save_folder':final_folder
        }
