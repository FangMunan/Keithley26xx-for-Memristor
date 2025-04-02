#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
iv_curves_dc.py

Implements a DC IV curve test, placing outputs into:
  .../YYYYMMDD/iv_curves_dc_tester/[timestamp_salt_conc_dev_parameters]/

Auto-increments filenames, uses English prompts but preserves Chinese comments.
"""

import os
import csv
import time
import math
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt
from sklearn.metrics import r2_score
from matplotlib.patches import FancyArrowPatch

from core import MemristorTester  # make sure your updated MemristorTester is in core.py

class IVCurvesDCTester(MemristorTester):
    def __init__(self, keithley):
        super().__init__(keithley)
        self.r2_value = 0.0
        self.freqs = []
        self.loop_areas = []
        self.test_count = 0
        self.max_tests = 20

    def query_voltage_steps(self):
        default_steps = [1, 0.1, 0.01, 0.001]
        inp = input("Enter voltage steps (comma separated). Default [1, 0.1, 0.01, 0.001]: ").strip()
        if not inp:
            return default_steps
        else:
            steps = []
            for x in inp.split(','):
                try:
                    val = float(x.strip())
                    steps.append(val)
                except:
                    pass
            return steps if steps else default_steps

    def query_voltage_range(self):
        inp = input("Enter voltage range (min,max). Default [-1,1]: ").strip()
        if not inp:
            return -1.0, 1.0
        parts = inp.split(',')
        if len(parts) < 2:
            return -1.0, 1.0
        try:
            v1 = float(parts[0].strip())
            v2 = float(parts[1].strip())
            return v1, v2
        except:
            return -1.0, 1.0

    def query_source_delay(self):
        inp = input("Enter source-measure delay (seconds). Default 0.01: ").strip()
        if not inp:
            return 0.01
        try:
            val = float(inp)
            return val
        except:
            return 0.01

    def get_or_create_voltage_profile(self, csv_path, v_start, v_stop, step):
        # Creates or loads a CSV of voltage steps
        if os.path.exists(csv_path):
            volts = []
            with open(csv_path,'r') as f:
                reader = csv.reader(f)
                for row in reader:
                    try:
                        v = float(row[0])
                        volts.append(v)
                    except:
                        pass
            return volts
        else:
            v_min = min(v_start, v_stop)
            v_max = max(v_start, v_stop)
            num_steps = int(abs(v_max - v_min)/step) + 1
            volt_list = np.linspace(v_start, v_stop, num_steps)
            with open(csv_path, 'w', newline='') as f:
                writer = csv.writer(f)
                for v in volt_list:
                    writer.writerow([f"{v:.6f}"])
            return volt_list

    def compute_diff_conductance(self, arr):
        # arr: [time, voltage, current, resistance]
        voltages = arr[:,1]
        currents = arr[:,2]
        di_dv = np.zeros_like(voltages)
        for i in range(1, len(arr)):
            dv = voltages[i]-voltages[i-1]
            di = currents[i]-currents[i-1]
            if abs(dv)<1e-20:
                di_dv[i] = 0
            else:
                di_dv[i] = di/dv
        di_dv[0] = di_dv[1]
        return di_dv

    def check_iv_curve_intersection(self, v, i):
        # Checks if there's an intersection (e.g. for a loop)
        # If single-sweep, often no intersection => skip
        intersections = []
        has_intersection = False
        n = len(v)
        for i1 in range(n-1):
            for i2 in range(i1+2, n-1):
                x1,y1 = v[i1], i[i1]
                x2,y2 = v[i1+1], i[i1+1]
                x3,y3 = v[i2], i[i2]
                x4,y4 = v[i2+1], i[i2+1]
                den = (y4-y3)*(x2-x1)-(x4-x3)*(y2-y1)
                if abs(den)<1e-10:
                    continue
                ua = ((x4-x3)*(y1-y3)-(y4-y3)*(x1-x3))/den
                ub = ((x2-x1)*(y1-y3)-(y2-y1)*(x1-x3))/den
                if 0<=ua<=1 and 0<=ub<=1:
                    has_intersection = True
                    # we won't skip the loop logic, but you can record intersection or stop
                    x_intersect = x1 + ua*(x2 - x1)
                    y_intersect = y1 + ua*(y2 - y1)
                    intersections.append((x_intersect,y_intersect))
        return has_intersection, intersections

    def plot_v_c_r_g(self, arr, di_dv, step, has_intersection):
        """
        Plots I-V, R-V, and dI/dV - V curves
        """
        v = arr[:,1]
        i = arr[:,2]
        r = arr[:,3]

        fig1 = plt.figure(figsize=(5,4))
        plt.plot(v,i,'b.-')
        if len(v)>4:
            idx1 = len(v)//4
            idx2 = 3*len(v)//4
            arrow1 = FancyArrowPatch((v[idx1], i[idx1]),(v[idx1+1], i[idx1+1]),
                                arrowstyle='->', color='red', mutation_scale=15)
            arrow2 = FancyArrowPatch((v[idx2], i[idx2]),(v[idx2+1], i[idx2+1]),
                                arrowstyle='->', color='red', mutation_scale=15)
            plt.gca().add_patch(arrow1)
            plt.gca().add_patch(arrow2)
        if has_intersection:
            plt.text(0.05,0.95,"Intersection: Yes", transform=plt.gca().transAxes,
                     color='green', fontsize=10, verticalalignment='top')
        else:
            plt.text(0.05,0.95,"Intersection: No", transform=plt.gca().transAxes,
                     color='red', fontsize=10, verticalalignment='top')
        plt.xlabel('Voltage (V)')
        plt.ylabel('Current (A)')
        plt.title(f"CV Curve (step={step})")
        plt.grid(True)

        fig2 = plt.figure(figsize=(5,4))
        plt.plot(v,r,'r.-')
        plt.xlabel('Voltage (V)')
        plt.ylabel('Resistance (Ohms)')
        plt.title(f"R-V Curve (step={step})")
        plt.grid(True)

        fig3 = plt.figure(figsize=(5,4))
        plt.plot(v, di_dv, 'g.-')
        plt.xlabel('Voltage (V)')
        plt.ylabel('dI/dV')
        plt.title(f"G-V Curve (step={step})")
        plt.grid(True)

        return fig1, fig2, fig3

    def compute_loop_area(self, x, y):
        if len(x)<3:
            return 0.0
        area = 0.0
        for i in range(len(x)):
            j=(i+1)%len(x)
            area += x[i]*y[j]
            area -= y[i]*x[j]
        return abs(area)/2.0

    def compute_loop_area_and_freq(self, arr, source_delay):
        """
        计算回线面积和频率
        """
        if arr.shape[0]<2:
            return (0.0, 0.0)
        x = arr[:,1]  # V
        y = arr[:,2]  # I
        loop_area = self.compute_loop_area(x,y)
        time_span = arr[-1,0]-arr[0,0]
        freq = 0.0
        if time_span>1e-9:
            freq=1.0/time_span
        return (loop_area, freq)

    def gaussian(self,x,a,b,c):
        return a*np.exp(-(x-b)**2/(2*c**2))

    def update_hz_looparea_fig(self, fig, loop_areas, freqs, steps, r2_value=None):
        if fig is None:
            fig = plt.figure(figsize=(8,6))
        plt.figure(fig.number)
        plt.clf()

        plt.scatter(freqs, loop_areas, label="Data points", color='blue')
        for i, step in enumerate(steps):
            plt.annotate(f"step={step}", (freqs[i], loop_areas[i]),
                         xytext=(0,10), textcoords="offset points", ha='center')

        if len(freqs)>=3:
            from scipy.optimize import curve_fit
            sorted_indices = np.argsort(freqs)
            sorted_freqs   = np.array(freqs)[sorted_indices]
            sorted_areas   = np.array(loop_areas)[sorted_indices]
            x_fit = np.linspace(min(freqs), max(freqs), 100)
            try:
                params,_ = curve_fit(self.gaussian, sorted_freqs, sorted_areas,
                                     p0=[max(sorted_areas), np.mean(sorted_freqs), np.std(sorted_freqs)],
                                     maxfev=10000)
                y_pred = self.gaussian(sorted_freqs,*params)
                r2 = r2_score(sorted_areas,y_pred)
                self.r2_value = r2
                plt.plot(x_fit, self.gaussian(x_fit,*params), 'r-',
                         label=f"Gaussian fit: R²={r2:.4f}")
                plt.text(0.05,0.95, f"a={params[0]:.2e}, b={params[1]:.4f}, c={params[2]:.4f}",
                         transform=plt.gca().transAxes, fontsize=10, va='top')
                plt.axhline(y=0.98, color='green', ls='--', alpha=0.7, label="Target R²=0.98")
            except Exception as e:
                print(f"Fitting error: {e}")

        plt.title("Hz_looparea")
        plt.xlabel("Frequency (Hz)")
        plt.ylabel("Loop Area")
        plt.grid(True)
        plt.legend()
        return fig

    def run_test(self):
        print("\n=== [IV_Curves_DC] Starting test ===")
        
        # 1) gather device info
        dev_info = self.setup_device_info()
        
        # 2) user inputs
        steps = self.query_voltage_steps()
        vmin,vmax = self.query_voltage_range()
        src_delay = self.query_source_delay()

        # For naming: incorporate user-chosen steps, volt range, delay, etc.
        # e.g. "steps_1-0.1-0.01_range_-1_1_delay_0.01"
        steps_str = "-".join(str(s) for s in steps)
        suffix = f"steps_{steps_str}_range_{vmin}_{vmax}_delay_{src_delay}"

        # Prepare final folder under "iv_curves_dc_tester"
        final_folder = self.prepare_save_folders("iv_curves_dc_tester", suffix)

        print(f"[Saving outputs to]: {final_folder}")

        steps_sorted = sorted(steps, reverse=True)

        # some local variables
        fig_hz_looparea = None
        all_steps = []
        self.test_count=0

        while self.test_count<self.max_tests and (self.r2_value<0.98 or self.test_count<3):
            self.test_count+=1
            run_label = f"test_{self.test_count}_srcdelay_{src_delay}"
            # not creating a separate folder for each run, but you could if you want
            # e.g. test_run_folder = ...
            print(f"\n=== Test run {self.test_count}, source_delay={src_delay} ===")

            current_steps=[]
            current_freqs=[]
            current_loop_areas=[]

            for step in steps_sorted:
                print(f"\n[Testing] Step={step} from {vmin} to {vmax}")
                # possibly create or load a CSV for those voltage points
                # ...
                # do measurement
                # ...
                # check intersection
                # ...
                # if no intersection => skip
                # ...
                # plot, compute loop area, frequency
                # ...
                # update fig_hz_looparea
                # ...
                # store results
                # ...
                pass

            # if self.r2_value >=0.98 => break

            # else adjust src_delay, ...
            break  # remove this once you implement the real loop

        print("\n=== [IV_Curves_DC] finished ===")
        return {
            'r2_value': self.r2_value,
            'freqs': self.freqs,
            'loop_areas': self.loop_areas,
            'save_folder': final_folder
        }
