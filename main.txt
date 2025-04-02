#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
main.py

主程序，用于选择和运行不同的测试模块 (Main program for selecting and running different test modules),
实际连接PyVISA以控制真实Keithley仪器。
"""

import time
from datetime import datetime
import pyvisa
from core import Keithley2600

# 如果有 core.py 里的基类或其他依赖，也可以在此import
# from core import MemristorTester

# 导入测试模块 (Import test modules)
from iv_curves_dc import IVCurvesDCTester
from sin_tester import SinTester
from ltp_ltd_tester import LtpLtdTester
from ppd_ppf_tester import PpdPpfTester
from srdp_tester import SrdpTester
from stdp_tester import StdpTester


def list_available_devices():
    """
    列出所有可用的 PyVISA 资源 (List all available VISA resources).
    在真实环境中，这些资源可能包括 GPIB0::24::INSTR、USB0::0xXXXX::...INSTR等。
    """
    rm = pyvisa.ResourceManager()
    devices = rm.list_resources()
    return devices


def connect_to_device(resource_name):
    """
    连接到指定资源名 (Connect to the specified VISA resource).

    :param resource_name: e.g. 'GPIB0::24::INSTR'
    :return: PyVISA instrument handle
    """
    rm = pyvisa.ResourceManager()
    instrument = rm.open_resource(resource_name)
    instrument.timeout = 10000
    print(f"[Info] Connected to {resource_name}")
    # 包一下
    keithley = Keithley2600(instrument)
    return keithley


def print_header():
    """
    打印程序头信息 (Print program header).
    """
    print("\n" + "="*60)
    print("  Keithley Memristor Testing System (Real Device via PyVISA)")
    print("  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("="*60)


def print_menu():
    """
    打印主菜单 (Print main menu).
    """
    print("\nAvailable tests:")
    print("1: IV Curves DC")
    print("2: Sine Wave")
    print("3: Long-Term Potentiation/Depression")
    print("4: Paired-Pulse Depression/Facilitation")
    print("5: Spike-Timing-Dependent Plasticity")
    print("6: Spike-Rate-Dependent Plasticity")
    print("0: Exit")


def main():
    """
    Main function.
    """
    print_header()

    # 列出可用设备
    devices = list_available_devices()
    if not devices:
        print("[Error] No VISA resources found. Please check your instrumentation and drivers.")
        return

    print("\nAvailable VISA resources:")
    for i, dev in enumerate(devices, start=1):
        print(f"{i}: {dev}")

    # 选择设备
    while True:
        try:
            idx = int(input("\nSelect device by number (or 0 to exit): ").strip())
            if idx == 0:
                print("[Info] Exiting program because no device selected.")
                return
            if 1 <= idx <= len(devices):
                selected_device = devices[idx-1]
                break
            else:
                print(f"[Error] Please enter a number between 1 and {len(devices)}, or 0 to exit.")
        except ValueError:
            print("[Error] Invalid input, please enter a number.")

    # 连接到所选设备
    keithley_resource = connect_to_device(selected_device)

    # 在本示例中，我们假设 Tester 直接用到这个 PyVISA handle
    # 你也可在 core.py 里写一个 Keithley2600 类包装 PyVISA 逻辑，Tester 再使用 Keithley2600对象

    # 主循环
    while True:
        print_menu()
        try:
            choice = int(input("\nSelect test (number): ").strip())
            if choice == 0:
                print("\n[Info] Exiting program...")
                break

            elif choice == 1:
                # IV曲线测试 (IV curve test)
                tester = IVCurvesDCTester(keithley_resource)  # 这里将PyVISA handle传给Tester
                tester.run_test()

            elif choice == 2:
                # 正弦波测试 (Sine wave test)
                tester = SinTester(keithley_resource)
                tester.run_test()

            elif choice == 3:
                # LTP/LTD测试 (LTP/LTD test)
                tester = LtpLtdTester(keithley_resource)
                tester.run_test()

            elif choice == 4:
                # PPD/PPF测试 (PPD/PPF test)
                tester = PpdPpfTester(keithley_resource)
                tester.run_test()

            elif choice == 5:
                # STDP测试 (STDP test)
                tester = StdpTester(keithley_resource)
                tester.run_test()

            elif choice == 6:
                # SRDP测试 (SRDP test)
                tester = SrdpTester(keithley_resource)
                tester.run_test()

            else:
                print("[Error] Invalid choice.")

        except ValueError:
            print("[Error] Invalid input. Please enter a valid number.")
        except Exception as e:
            print(f"[Error] {e}")

        print("\n[Info] Returning to main menu...")
        time.sleep(1)


if __name__ == "__main__":
    main()
