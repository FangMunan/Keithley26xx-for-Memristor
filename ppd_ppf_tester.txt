#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ppd_ppf_tester.py

Paired-Pulse Depression/Facilitation test.
Puts outputs under: .../YYYYMMDD/ppd_ppf_tester/<timestamp_salt_conc_dev_params>/

Auto-increments filenames, English UI + Chinese comments.
"""

import os
import csv
import time
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit

from core import MemristorTester

class PpdPpfTester(MemristorTester):
    def __init__(self, keithley):
        super().__init__(keithley)
        self.off_time = 0.001
        self.nplc=1
        self.pulse_width=0.1
        self.pulse_amplitude=1.0
        self.read_voltage=0.1

        self.interval_times = [0.01,0.02,0.05,0.1,0.2,0.5,1.0,2.0]
        self.repetitions=1

        self.off_time_array=[0.001,0.01,0.1]
        self.pulse_width_array=[0.1,0.2,0.5]
        self.pulse_amplitude_array=[0.5,1.0]

        self.ppd_ppf_data=[]
        self.ppd_ppf_ratios=[]
        self.time_constant=0.0
        self.r2=0.0

    def setup_test_parameters(self):
        self.setup_device_info()
        print(f"\nCurrent test parameters:")
        print(f"Off time={self.off_time}, NPLC={self.nplc}")
        print(f"Pulse width={self.pulse_width}s, amplitude={self.pulse_amplitude}V, read={self.read_voltage}V")
        print(f"Interval times={self.interval_times}, repetitions={self.repetitions}")
        ans=input("Modify default? (y/n): ").strip().lower()
        if ans=='y':
            try:
                self.off_time = float(input(f"Off time (default {self.off_time}): ").strip() or self.off_time)
                self.nplc = float(input(f"NPLC (default {self.nplc}): ").strip() or self.nplc)
                self.pulse_width = float(input(f"Pulse width (default {self.pulse_width}): ").strip() or self.pulse_width)
                self.pulse_amplitude = float(input(f"Pulse amplitude (default {self.pulse_amplitude}): ").strip() or self.pulse_amplitude)
                self.read_voltage = float(input(f"Read voltage (default {self.read_voltage}): ").strip() or self.read_voltage)

                intervals_str=input(f"Interval times (default {self.interval_times}): ").strip()
                if intervals_str:
                    try:
                        self.interval_times=[float(x.strip()) for x in intervals_str.split(',')]
                    except:
                        print("[Warning] Invalid intervals, using defaults")
                self.repetitions=int(input(f"Repetitions (default {self.repetitions}): ").strip() or self.repetitions)
            except ValueError:
                print("[Warning] invalid input, using defaults")

    def run_paired_pulse_test(self, interval):
        # single pair
        self.keithley.reset_device()
        self.keithley.default_setup()
        self.keithley.source_function='voltage'
        self.keithley.level_i=0
        self.keithley.limit_i=1e-7
        self.keithley.nplc=self.nplc
        self.keithley.output=True

        data=[]
        start=time.time()

        # pulse1
        self.keithley.level_v=self.pulse_amplitude
        time.sleep(self.pulse_width)
        i_p1,v_p1=self.keithley.measure_iv()
        t_p1=time.time()-start
        data.append([t_p1, v_p1, i_p1, "pulse1"])

        # off-> off_time
        self.keithley.output=False
        time.sleep(self.off_time)
        self.keithley.output=True

        # wait interval
        print(f"[Info] waiting {interval}s between pulses")
        time.sleep(interval)

        # pulse2
        self.keithley.level_v=self.pulse_amplitude
        time.sleep(self.pulse_width)
        i_p2,v_p2=self.keithley.measure_iv()
        t_p2=time.time()-start
        data.append([t_p2,v_p2,i_p2,"pulse2"])

        self.keithley.output=False

        if data:
            t0=data[0][0]
            for row in data:
                row[0]-=t0
        return np.array(data)

    def calculate_ppd_ppf_ratio(self, data):
        if len(data)<2:
            return 0.0,False
        i_p1=float(data[0][2])
        i_p2=float(data[1][2])
        if abs(i_p1)<1e-20:
            return 0.0,False
        ratio=(i_p2/i_p1)-1
        is_ppf=(ratio>0)
        return ratio,is_ppf

    def exponential_decay(self,x,a,tau,c):
        return a*np.exp(-x/tau)+c

    def fit_exponential_decay(self, intervals, ratios):
        if len(intervals)<3 or len(ratios)<3:
            return None,0.0
        try:
            from sklearn.metrics import r2_score
            p0=[max(abs(float(np.array(ratios)))), np.mean(intervals), np.min(ratios)]
            popt,_=curve_fit(self.exponential_decay, intervals, ratios, p0=p0, maxfev=10000)
            pred=self.exponential_decay(np.array(intervals),*popt)
            r2=r2_score(ratios, pred)
            return popt,r2
        except Exception as e:
            print(f"[Error fitting] {e}")
            return None,0.0

    def plot_paired_pulse_data(self, data, interval, save_path):
        times=[row[0] for row in data]
        volts=[row[1] for row in data]
        currs=[row[2] for row in data]
        labels=[row[3] for row in data]

        plt.figure(figsize=(8,6))
        plt.plot(times, currs, 'b.-', label='Current')
        plt.xlabel("Time(s)")
        plt.ylabel("Current(A)")
        plt.title(f"Paired pulse test, interval={interval}s")
        plt.grid(True)
        for i,lab in enumerate(labels):
            plt.text(times[i], currs[i], lab, fontsize=9)

        if save_path:
            plt.savefig(save_path,dpi=300)
            print(f"[Plot saved] {save_path}")
        plt.close()

    def plot_ppd_ppf_ratios(self, intervals, ratios, params=None, r2_val=None, save_path=None):
        plt.figure(figsize=(8,6))
        plt.scatter(intervals, ratios, color='blue', label='PPD/PPF ratio')
        if params is not None:
            x_fit=np.linspace(min(intervals), max(intervals),200)
            y_fit=self.exponential_decay(x_fit,*params)
            plt.plot(x_fit,y_fit,'r-',label=f"Exp fit (R²={r2_val:.4f})")
        plt.axhline(0, color='gray',ls='--',alpha=0.7)
        plt.xlabel("Interval(s)")
        plt.ylabel("PPD/PPF ratio")
        plt.title("PPD/PPF ratio vs interval")
        plt.grid(True)
        plt.legend()

        if save_path:
            plt.savefig(save_path,dpi=300)
            print(f"[Plot saved] {save_path}")
        plt.close()

    def run_test(self):
        print("\n=== [PPD/PPF Test] Starting ===")
        self.setup_test_parameters()

        # Make a suffix label from the main parameters
        suffix = f"off_{self.off_time}_pw_{self.pulse_width}_pa_{self.pulse_amplitude}"
        final_folder=self.prepare_save_folders("ppd_ppf_tester", suffix)

        print(f"[Info] Data will be saved to: {final_folder}")

        all_ints=[]
        all_ratios=[]
        all_is_ppf=[]

        for interval in self.interval_times:
            local_ratios=[]
            local_is_ppf=[]
            for rep in range(self.repetitions):
                print(f"[Info] interval={interval}, repetition={rep+1}/{self.repetitions}")
                data=self.run_paired_pulse_test(interval)
                ratio, is_ppf=self.calculate_ppd_ppf_ratio(data)
                local_ratios.append(ratio)
                local_is_ppf.append(is_ppf)

                prefix=f"ppd_ppf_int_{interval}_rep_{rep+1}"
                csv_path=self.save_data_csv(final_folder,prefix,data)
                self.plot_paired_pulse_data(data, interval, csv_path.replace(".csv",".png"))

                if rep<self.repetitions-1:
                    print("[Info] wait 5s before next repetition")
                    time.sleep(5)

            # compute average ratio
            avg_ratio=np.mean(local_ratios)
            avg_is_ppf=(np.mean(local_is_ppf)>0.5)
            all_ints.append(interval)
            all_ratios.append(avg_ratio)
            all_is_ppf.append(avg_is_ppf)

            if interval!=self.interval_times[-1]:
                print("[Info] wait 10s before next interval")
                time.sleep(10)

        popt, r2_val=self.fit_exponential_decay(all_ints, all_ratios)
        self.r2=r2_val
        if popt is not None:
            self.time_constant=popt[1]
            print(f"[Results] a={popt[0]:.4f}, tau={popt[1]:.4f}, c={popt[2]:.4f}, R²={r2_val:.4f}")
        else:
            self.time_constant=0.0
            print("[Warning] Exp fit failed or not enough data.")

        # plot final ratio
        ratio_png=os.path.join(final_folder,"ppd_ppf_ratios.png")
        self.plot_ppd_ppf_ratios(all_ints, all_ratios, popt, r2_val, ratio_png)

        # save ratio csv
        ratio_csv=os.path.join(final_folder,"ppd_ppf_ratios.csv")
        with open(ratio_csv,'w',newline='') as f:
            wr=csv.writer(f)
            wr.writerow(["Interval(s)","Ratio","Type"])
            for iv,rt,isf in zip(all_ints,all_ratios,all_is_ppf):
                wr.writerow([iv,rt,"PPF" if isf else "PPD"])
        print(f"[Data saved] {ratio_csv}")

        print("\n=== [PPD/PPF Test] finished ===")
        return {
            'off_time': self.off_time,
            'pulse_width': self.pulse_width,
            'pulse_amplitude': self.pulse_amplitude,
            'time_constant': self.time_constant,
            'r2': self.r2,
            'save_folder': final_folder
        }
