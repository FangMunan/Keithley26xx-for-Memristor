#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
sin_tester.py

Demonstrates a sine-wave style measurement, with output placed under:
  .../YYYYMMDD/sin_tester/<timestamp_salt_conc_dev_params>/

Auto-increment filenames, English UI with Chinese comments.
"""

import time
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import r2_score

from core import MemristorTester

class SinTester(MemristorTester):
    def __init__(self, keithley):
        super().__init__(keithley)
        self.off_time_list = [0.01, 0.2]
        self.pulse_width_list = [0.1]
        self.points_per_half_list = [6]
        self.nplc = 1
        self.r2_pos = 0.0
        self.r2_neg = 0.0

    def generate_custom_sine_points(self, amplitude, points_per_half, cycles):
        # Chinese comment: 生成正弦序列
        part1 = [np.sin(i*np.pi/points_per_half) for i in range(points_per_half)]
        part2 = [np.sin(i*np.pi/points_per_half) for i in range(points_per_half,2*points_per_half)]
        seq_pos = part1*cycles
        seq_neg = part2*cycles
        full_seq = seq_pos+seq_neg + [0.0]
        return [amplitude*v for v in full_seq]

    def run_sine_test(self, voltage_points, pw, off_time):
        self.keithley.reset_device()
        self.keithley.default_setup()
        self.keithley.source_function = 'voltage'
        self.keithley.level_i=0
        self.keithley.limit_i = 1e-7
        self.keithley.nplc = self.nplc
        self.keithley.output = True

        # optionally fix range
        self.keithley.smu.write("smua.measure.rangei = 1e-7")
        self.keithley.smu.write("smua.measure.autorangei = smua.AUTORANGE_OFF")

        data=[]
        for v in voltage_points:
            self.keithley.level_v=v
            time.sleep(pw)
            i, v_meas = self.keithley.measure_iv()
            t_now = time.time()
            data.append([t_now, v_meas, i])
            time.sleep(off_time)

        self.keithley.output=False

        if data:
            t0=data[0][0]
            for row in data:
                row[0]-=t0
        return np.array(data)

    def extract_peak_currents(self, data, v_target, tol=0.05):
        # scan for rows where |voltage - v_target|<tol
        return [row[2] for row in data if abs(row[1]-v_target)<tol]

    def fit_linear(self, x, y):
        if len(x)<2:
            return 0,0,0
        slope, intercept=np.polyfit(x,y,1)
        y_pred = slope*np.array(x)+intercept
        r2 = r2_score(y,y_pred)
        return slope, intercept, r2

    def determine_m_type(self, currents):
        # just an example
        half=len(currents)//2
        x1=range(1,half+1)
        x2=range(1, len(currents)-half+1)
        y1=currents[:half]
        y2=currents[half:]
        k1,_,_ = self.fit_linear(x1,y1)
        k2,_,_ = self.fit_linear(x2,y2)
        if k1<0 and k2>0:
            return "M1"
        elif k1<0 and k2<0:
            return "M2"
        elif k1>0 and k2<0:
            return "M3"
        elif k1>0 and k2>0:
            return "M4"
        return "M0"

    def plot_current_vs_time(self, data, save_path):
        t=data[:,0]
        i=data[:,2]
        plt.figure(figsize=(8,6))
        plt.plot(t,i,label='Current vs Time')
        plt.xlabel("Time(s)")
        plt.ylabel("Current(A)")
        plt.title("Sine wave test: current over time")
        plt.grid(True)
        plt.legend()
        plt.savefig(save_path,dpi=300)
        plt.close()

    def run_test(self):
        print("\n=== [Sine Tester] starting ===")
        dev_info = self.setup_device_info()

        # build a folder name suffix from the main parameters
        # e.g. "sine_offTime_0.5_pw_0.1_pph_6"
        # but we have multiple lists => let's store the last iteration
        test_id = "sin_main"  # or "Sine_test"
        final_folder = self.prepare_save_folders("sin_tester", test_id)

        for off_t in self.off_time_list:
            for pw in self.pulse_width_list:
                for pph in self.points_per_half_list:
                    print(f"\n[Test] off_time={off_t}, pulse_width={pw}, points_per_half={pph}")
                    voltage_points = self.generate_custom_sine_points(1.0, pph, cycles=4)
                    data=self.run_sine_test(voltage_points, pw, off_t)

                    pos = self.extract_peak_currents(data,1.0)
                    neg = self.extract_peak_currents(data,-1.0)

                    pos_slope,pos_int,self.r2_pos=self.fit_linear(range(1,len(pos)+1), pos)
                    neg_slope,neg_int,self.r2_neg=self.fit_linear(range(1,len(neg)+1), neg)

                    mtype=self.determine_m_type(pos)
                    fileprefix = f"{mtype}_off{off_t}_pw{pw}_pph{pph}"

                    csv_path = self.save_data_csv(final_folder, fileprefix, data)
                    self.plot_current_vs_time(data, csv_path.replace(".csv","_plot.png"))

                    # wait if you want
                    print("[Info] Wait 5s before next iteration")
                    time.sleep(5)

        print("=== [Sine Tester] done ===")
        return {
            'r2_pos': self.r2_pos,
            'r2_neg': self.r2_neg,
            'save_folder': final_folder
        }
