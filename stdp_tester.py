#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
stdp_tester.py

Spike-Timing-Dependent Plasticity test.
Saves output to: .../YYYYMMDD/stdp_tester/<timestamp_salt_conc_dev_params>/
English UI + Chinese comments, with incremental file naming logic.
"""

import os
import csv
import time
import numpy as np

from core import MemristorTester

class StdpTester(MemristorTester):
    def __init__(self, keithley):
        super().__init__(keithley)
        # default parameters
        self.off_time=0.0001
        self.nplc=1
        self.V_read=0.1
        self.read_num=5

        self.V_spike=0.5
        self.spike_num=5

        self.V_active=0
        self.active_num=1

        self.V_rest=0.0
        self.V_time=0.0
        self.V_stop=0.0
        self.stop_num=5

        self.time_num=np.array([0,5,20])
        self.off_time_array=[0.0001,0.01,0.1]
        self.V_spike_array=[-0.3,-0.5,-0.7]
        self.active_num_array=[0,5,10]

        self.pre_before_post=True
        self.completed_models=[]
        self.best_fit_model=None
        self.best_fit_params=None
        self.best_r2=0.0
        self.delta_t_values=np.array([])
        self.delta_g_values=np.array([])

    def setup_test_parameters(self):
        self.setup_device_info()

        print("\nCurrent test parameters:")
        print(f"off_time={self.off_time}, nplc={self.nplc}")
        print(f"V_read={self.V_read}, V_spike={self.V_spike}, V_active={self.V_active}, active_num={self.active_num}")
        print(f"read_num={self.read_num}, spike_num={self.spike_num}, time_num={self.time_num}")
        ans=input("Modify default? (y/n): ").strip().lower()
        if ans=='y':
            try:
                self.off_time=float(input(f"Off time (default {self.off_time}): ").strip() or self.off_time)
                self.nplc=float(input(f"NPLC (default {self.nplc}): ").strip() or self.nplc)
                self.V_read=float(input(f"Read voltage (default {self.V_read}): ").strip() or self.V_read)
                self.V_spike=float(input(f"Spike voltage (default {self.V_spike}): ").strip() or self.V_spike)
                self.V_active=float(input(f"Active voltage (default {self.V_active}): ").strip() or self.V_active)
                self.active_num=int(input(f"Active pulses (default {self.active_num}): ").strip() or self.active_num)
                t_str=input(f"Time intervals (comma-separated, default {self.time_num.tolist()}): ").strip()
                if t_str:
                    arr=[float(x.strip()) for x in t_str.split(',')]
                    self.time_num=np.array(arr)
            except ValueError:
                print("[Warning] invalid input")

    def generate_voltage_sequences(self):
        pre_seq=[]
        post_seq=[]
        for t_1 in self.time_num:
            # pre sequence
            pre_seq.extend([self.V_read]*self.read_num)
            pre_seq.extend([self.V_spike]*self.spike_num)
            pre_seq.extend([self.V_rest]*(self.active_num+self.spike_num))
            pre_seq.extend([self.V_time]*int(t_1))
            pre_seq.extend([self.V_active]*self.active_num)
            pre_seq.extend([self.V_read]*self.read_num)
            pre_seq.extend([self.V_stop]*self.stop_num)

            # post sequence
            post_seq.extend([self.V_rest]*(self.read_num+self.spike_num))
            post_seq.extend([self.V_active]*self.active_num)
            post_seq.extend([self.V_time]*int(t_1))
            post_seq.extend([self.V_spike]*self.spike_num)
            post_seq.extend([self.V_rest]*(self.active_num+self.read_num))
            post_seq.extend([self.V_stop]*self.stop_num)

        return pre_seq,post_seq

    def _reset_and_setup_keithley(self):
        self.keithley.reset_device()
        self.keithley.default_setup()
        self.keithley.source_function='voltage'
        self.keithley.level_i=0
        self.keithley.limit_i=1e-7
        self.keithley.nplc=self.nplc
        self.keithley.output=True

    def run_stdp_test(self, pre_sequence, post_sequence):
        self._reset_and_setup_keithley()
        self.keithley.smu.write("smua.source.func = smua.OUTPUT_DCVOLTS")
        self.keithley.smu.write("smub.source.func = smub.OUTPUT_DCVOLTS")
        self.keithley.smu.write("smua.source.output = smua.OUTPUT_ON")
        self.keithley.smu.write("smub.source.output = smub.OUTPUT_ON")

        if self.pre_before_post:
            chanA_seq=pre_sequence
            chanB_seq=post_sequence
        else:
            chanA_seq=post_sequence
            chanB_seq=pre_sequence

        data=[]
        start=time.time()
        length=min(len(chanA_seq), len(chanB_seq))

        for i in range(length):
            vA=chanA_seq[i]
            vB=chanB_seq[i]
            self.keithley.smu.write(f"smua.source.levelv = {vA}")
            self.keithley.smu.write(f"smub.source.levelv = {vB}")

            time.sleep(self.off_time)
            iA_str=self.keithley.smu.query("print(smua.measure.i())")
            iB_str=self.keithley.smu.query("print(smub.measure.i())")

            iA=float(iA_str.strip())
            iB=float(iB_str.strip())
            t_now=time.time()-start
            data.append([t_now, vA, vB, iA, iB])

        self.keithley.smu.write("smua.source.output=smua.OUTPUT_OFF")
        self.keithley.smu.write("smub.source.output=smub.OUTPUT_OFF")

        if data:
            t0=data[0][0]
            for row in data:
                row[0]-=t0
        return np.array(data)

    def process_measurement_data(self, data):
        import pandas as pd
        df=pd.DataFrame(data,columns=[
            "Time(s)",
            "Channel A Voltage",
            "Channel B Voltage",
            "Channel A Current",
            "Channel B Current"
        ])
        if self.pre_before_post:
            preV_col="Channel A Voltage"
            preI_col="Channel A Current"
            postV_col="Channel B Voltage"
            postI_col="Channel B Current"
        else:
            preV_col="Channel B Voltage"
            preI_col="Channel B Current"
            postV_col="Channel A Voltage"
            postI_col="Channel A Current"

        # read pulses
        read_mask=np.isclose(df[preV_col], self.V_read, atol=0.01)
        read_data=df[read_mask].copy()
        read_data.reset_index(drop=True,inplace=True)
        read_groups=[]
        for idx in range(0,len(read_data),self.read_num):
            block=read_data.iloc[idx:idx+self.read_num]
            if len(block)==self.read_num:
                read_groups.append(block)
        read_currents=[]
        for block in read_groups:
            i_mean=block[preI_col].mean()
            read_currents.append(i_mean)

        # spike
        spike_pre_mask=np.isclose(df[preV_col], self.V_spike, atol=0.01)
        spike_post_mask=np.isclose(df[postV_col], self.V_spike, atol=0.01)
        spike_pre_data=df[spike_pre_mask].copy()
        spike_post_data=df[spike_post_mask].copy()
        spike_pre_data.reset_index(drop=True,inplace=True)
        spike_post_data.reset_index(drop=True,inplace=True)

        spike_pre_times=[]
        for idx in range(0,len(spike_pre_data), self.spike_num):
            block=spike_pre_data.iloc[idx:idx+self.spike_num]
            if len(block)==self.spike_num:
                spike_pre_times.append(block["Time(s)"].iloc[0])

        spike_post_times=[]
        for idx in range(0,len(spike_post_data), self.spike_num):
            block=spike_post_data.iloc[idx:idx+self.spike_num]
            if len(block)==self.spike_num:
                spike_post_times.append(block["Time(s)"].iloc[0])

        # delta_g from consecutive read group
        delta_g_list=[]
        for i in range(len(read_currents)-1):
            i1=read_currents[i]
            i2=read_currents[i+1]
            if abs(i1)<1e-20:
                dg=np.nan
            else:
                dg=(i2-i1)/i1
            delta_g_list.append(dg)

        # delta_t from spike times
        n_spike_pairs=min(len(spike_pre_times),len(spike_post_times))
        delta_t_list=[]
        for i in range(n_spike_pairs):
            dt=spike_post_times[i]-spike_pre_times[i]
            if not self.pre_before_post:
                dt=-dt
            delta_t_list.append(dt)

        n_min=min(len(delta_g_list), len(delta_t_list))
        if n_min==0:
            print("[Warning] no valid read/spike pairs found.")
            return np.array([]), np.array([])
        return np.array(delta_t_list[:n_min]), np.array(delta_g_list[:n_min])

    def save_delta_csv(self, folder, prefix, dt, dg):
        csv_filename=f"{prefix}_delta.csv"
        csv_path=os.path.join(folder,csv_filename)
        idx=1
        base_prefix=prefix+"_delta"
        while os.path.exists(csv_path):
            csv_filename=f"{base_prefix}_{idx}.csv"
            csv_path=os.path.join(folder,csv_filename)
            idx+=1
        with open(csv_path,'w',newline='') as f:
            wr=csv.writer(f)
            wr.writerow(["Delta_t","Delta_g"])
            for x_t,x_g in zip(dt,dg):
                wr.writerow([x_t,x_g])
        print(f"[Delta data saved] {csv_path}")

    def run_test(self):
        print("\n=== [STDP Test] Starting ===")
        self.setup_test_parameters()

        suffix=f"off_{self.off_time}_spike_{self.V_spike}_active_{self.active_num}"
        final_folder=self.prepare_save_folders("stdp_tester", suffix)

        print(f"All data will be saved under: {final_folder}")

        pre_seq, post_seq=self.generate_voltage_sequences()

        # 1) pre->post
        self.pre_before_post=True
        data=self.run_stdp_test(pre_seq, post_seq)
        self.save_data_csv(final_folder,"stdp_raw_data_pre",data)
        dt,dg=self.process_measurement_data(data)
        self.save_delta_csv(final_folder,"stdp_pre",dt,dg)

        # 2) optional post->pre
        ans=input("Run post->pre test as well? (y/n): ").strip().lower()
        if ans=='y':
            self.pre_before_post=False
            post_seq2, pre_seq2=self.generate_voltage_sequences()
            data2=self.run_stdp_test(post_seq2, pre_seq2)
            self.save_data_csv(final_folder,"stdp_raw_data_post",data2)
            dt2,dg2=self.process_measurement_data(data2)
            self.save_delta_csv(final_folder,"stdp_post",dt2,dg2)

        print("\n=== [STDP Test] finished ===")
        return {
            'save_folder': final_folder,
            'off_time': self.off_time,
            'V_spike': self.V_spike,
            'active_num': self.active_num
        }
