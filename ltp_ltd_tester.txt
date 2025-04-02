#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ltp_ltd_tester.py

LTP/LTD test module, demonstrating:
1) Subfolder "ltp_ltd_tester" inside the date folder
2) Time-stamped unique folder name including salt/concentration/device
3) Automatic incremental filename checks
4) English UI while preserving Chinese comments
"""

import time
import numpy as np
import matplotlib.pyplot as plt
import os

from core import MemristorTester

class LtpLtdTester(MemristorTester):
    def __init__(self, keithley):
        super().__init__(keithley)
        # Default parameters
        self.nplc = 1
        self.pulse_width = 0.1
        self.pulse_time = 10
        
        self.read_voltage = 0.1
        self.write_p_voltage = 1.0
        self.write_d_voltage = -1.0

        self.data_all = None

    def setup_test_parameters(self):
        """
        Prompt for user to modify default parameters (English with Chinese comments).
        """
        self.setup_device_info()

        print(f"\nCurrent test parameters:")
        print(f"NPLC: {self.nplc}")
        print(f"Pulse width: {self.pulse_width}s")
        print(f"Pulse time (LTP + LTD): {self.pulse_time}")
        print(f"Read voltage: {self.read_voltage}V")
        print(f"Positive write voltage (LTP): {self.write_p_voltage}V")
        print(f"Negative write voltage (LTD): {self.write_d_voltage}V")

        choice = input("Do you want to modify default parameters? (y/n): ").strip().lower()
        if choice == 'y':
            try:
                self.nplc = float(input(f"NPLC (default {self.nplc}): ").strip() or self.nplc)
                self.pulse_width = float(input(f"Pulse width (default {self.pulse_width}): ").strip() or self.pulse_width)
                self.pulse_time = int(input(f"Pulse time for LTP and LTD each (default {self.pulse_time}): ").strip() or self.pulse_time)
                self.read_voltage = float(input(f"Read voltage (default {self.read_voltage}): ").strip() or self.read_voltage)
                self.write_p_voltage = float(input(f"LTP write voltage (default {self.write_p_voltage}): ").strip() or self.write_p_voltage)
                self.write_d_voltage = float(input(f"LTD write voltage (default {self.write_d_voltage}): ").strip() or self.write_d_voltage)
            except ValueError:
                print("Invalid input, keeping defaults.")

    def _run_ltp_ltd_sequence(self):
        """
        1) reset & default_setup
        2) do LTP pulses (read -> +V) multiple times
        3) immediately do LTD pulses (read -> -V) multiple times
        4) no waiting or output off in between
        """
        self.keithley.reset_device()
        self.keithley.default_setup()
        self.keithley.source_function = 'voltage'
        self.keithley.limit_i = 1e-7
        self.keithley.nplc = self.nplc
        self.keithley.output = True

        data = []
        start_time = time.time()

        # LTP segment
        for i in range(self.pulse_time):
            # read
            self.keithley.level_v = self.read_voltage
            time.sleep(self.pulse_width)
            i_read, v_read = self.keithley.measure_iv()
            t_read = time.time() - start_time
            data.append([t_read, v_read, i_read, "LTP_read"])

            # write (positive)
            self.keithley.level_v = self.write_p_voltage
            time.sleep(self.pulse_width)
            i_write, v_write = self.keithley.measure_iv()
            t_write = time.time() - start_time
            data.append([t_write, v_write, i_write, "LTP_write"])

        # direct switch to LTD
        for i in range(self.pulse_time):
            # read
            self.keithley.level_v = self.read_voltage
            time.sleep(self.pulse_width)
            i_read, v_read = self.keithley.measure_iv()
            t_read = time.time() - start_time
            data.append([t_read, v_read, i_read, "LTD_read"])

            # write (negative)
            self.keithley.level_v = self.write_d_voltage
            time.sleep(self.pulse_width)
            i_write, v_write = self.keithley.measure_iv()
            t_write = time.time() - start_time
            data.append([t_write, v_write, i_write, "LTD_write"])

        self.keithley.output = False

        # time alignment
        if data:
            t0 = data[0][0]
            for row in data:
                row[0] -= t0

        return np.array(data, dtype=object)

    def extract_data_by_label(self, data, label_substring):
        """
        Filter rows by matching label (e.g., 'LTP_read', 'LTD_write', etc.).
        """
        results = []
        for row in data:
            if label_substring.lower() in str(row[3]).lower():
                results.append(row)
        return np.array(results)

    def plot_current_vs_time(self, data, title, save_path=None):
        if data.size == 0:
            print(f"[Warning] No data to plot for {title}.")
            return
        
        t = data[:, 0].astype(float)
        i = data[:, 2].astype(float)

        plt.figure(figsize=(8,5))
        plt.plot(t, i, '.-', label=title)
        plt.xlabel("Time (s)")
        plt.ylabel("Current (A)")
        plt.title(title)
        plt.grid(True)
        plt.legend()

        if save_path:
            plt.savefig(save_path, dpi=300)
            print(f"[Plot saved] {save_path}")
        plt.close()

    def run_test(self):
        """
        Run LTP->LTD back to back with no delay between them.
        """
        print("\n=== [LTP/LTD Test] Starting (no gap) ===")
        self.setup_test_parameters()

        # Build a "suffix_label" that includes the main test parameters
        suffix_label = f"NOGAP_pw_{self.pulse_width}_pt_{self.pulse_time}"

        # Build the final folder path: 
        #   date/ltp_ltd_tester/[timestamp_salt_conc_dev_suffix_label]
        final_folder = self.prepare_save_folders("ltp_ltd_tester", suffix_label)
        
        # Actually run the test
        self.data_all = self._run_ltp_ltd_sequence()

        # Save the raw data
        csv_prefix = "ltp_ltd_raw_data"
        self.save_data_csv(final_folder, csv_prefix, self.data_all)

        # Sub-group data
        ltp_read  = self.extract_data_by_label(self.data_all, "LTP_read")
        ltp_write = self.extract_data_by_label(self.data_all, "LTP_write")
        ltd_read  = self.extract_data_by_label(self.data_all, "LTD_read")
        ltd_write = self.extract_data_by_label(self.data_all, "LTD_write")

        # Plot
        self.plot_current_vs_time(ltp_read,  "LTP_READ",  
            os.path.join(final_folder, "ltp_read_plot.png"))
        self.plot_current_vs_time(ltp_write, "LTP_WRITE", 
            os.path.join(final_folder, "ltp_write_plot.png"))
        self.plot_current_vs_time(ltd_read,  "LTD_READ",  
            os.path.join(final_folder, "ltd_read_plot.png"))
        self.plot_current_vs_time(ltd_write, "LTD_WRITE", 
            os.path.join(final_folder, "ltd_write_plot.png"))

        # Overviews
        ltp_all = self.extract_data_by_label(self.data_all, "LTP_")
        self.plot_current_vs_time(ltp_all, "LTP_all",  
            os.path.join(final_folder, "ltp_all.png"))
        ltd_all = self.extract_data_by_label(self.data_all, "LTD_")
        self.plot_current_vs_time(ltd_all, "LTD_all",  
            os.path.join(final_folder, "ltd_all.png"))

        # Compare read
        plt.figure(figsize=(9,5))
        if ltp_read.size>0:
            plt.plot(ltp_read[:,0],  ltp_read[:,2], 'b.-', label='LTP_read')
        if ltd_read.size>0:
            plt.plot(ltd_read[:,0], ltd_read[:,2], 'r.-', label='LTD_read')
        plt.title("LTP vs LTD (read current)")
        plt.xlabel("Time (s)")
        plt.ylabel("Current (A)")
        plt.grid(True)
        plt.legend()
        compare_png = os.path.join(final_folder, "ltp_ltd_compare.png")
        plt.savefig(compare_png, dpi=300)
        plt.close()
        print(f"[Plot saved] {compare_png}")

        print("\n=== [LTP/LTD Test Done] Data & plots in:", final_folder)

        return {
            'pulse_width': self.pulse_width,
            'pulse_time': self.pulse_time,
            'save_folder': final_folder
        }
