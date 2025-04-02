# core.py
import os
import csv
import time
from datetime import datetime
from pyvisa import Resource



def english_timestamp():
    """
    Generate a timestamp string like 20250401_125959 (YYYYMMDD_HHMMSS).
    """
    return datetime.now().strftime("%Y%m%d_%H%M%S")


class Keithley2600:
    """
    Keithley 2600 Source Meter class. It contains basic functions to set up the device and make measurements.
    """

    def __init__(self, device: Resource, delay=0.1, auto_reset=False):
        """
        :param device: VISA Resource 对象
        :param delay: 默认测量延时，可由 smua.source.delay 和 time.sleep 配合使用
        :param auto_reset: 是否在构造时自动执行 reset_device() + default_setup()
        """
        self.smu = device
        # 增加超时时间
        self.smu.timeout = 10000  # 设置为10秒

        if auto_reset:
            self.reset_device()
            self.default_setup()

        # 确保delay至少为0.001秒
        self.delay = max(0.001, delay)

    def __enter__(self):
        """
        实现上下文管理器，使with Keithley2600(...) as keith:能够自动清理资源
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        离开with语句自动调用，负责关闭输出，释放资源
        """
        self.close()

    def measure_resistance(self):
        """
        Get single resistance measurement
        :return: resistance, Ohm
        """
        try:
            response = self.smu.query('print(smua.measure.r())')
            resistance = float(response.strip())
            return resistance
        except Exception as e:
            print(f"Error in measure_resistance: {repr(e)}")
            return float('inf')  # 返回无穷大表示测量失败

    def measure_iv(self):
        """
        Get a single pair of the current and voltage measurement
        :return: (current(A), voltage(V))
        """
        try:
            self.smu.write("ireading, vreading = smua.measure.iv()")
            # 如果已通过 smua.source.delay 设置了等待时间，可酌情移除此处 sleep
            time.sleep(max(0.001, self.delay))
            response = self.smu.query("printnumber(ireading,vreading)").split(",")
            i = float(response[0])
            v = float(response[1])
            return i, v
        except Exception as e:
            print(f"Error in measure_iv: {repr(e)}")
            return 0.0, self.level_v

    def setup_for_IV_measurement(self, current_limit, nplc):
        """
        Configure source meter for basic IV measurement.
        :param current_limit: The current limit (A)
        :param nplc: Number of power line cycles
        """
        self.source_function = 'voltage'
        self.limit_i = current_limit
        self.nplc = nplc
        self.autorange_i = True
        self.autorange_v = True
        print(f"[setup_for_IV_measurement] current_limit={current_limit}, nplc={nplc}")

    def measure_power(self):
        """
        Get single power measurement
        :return: power, W
        """
        try:
            response = self.smu.query('print(smua.measure.p())')
            power = float(response.strip())
            return power
        except Exception as e:
            print(f"Error in measure_power: {repr(e)}")
            return 0.0

    def reset_device(self):
        """
        Reset the device to default settings
        """
        try:
            self.smu.write('reset()')
            self.smu.write('smua.reset()')
        except Exception as e:
            print(f"Error in reset_device: {repr(e)}")

    def default_setup(self):
        """
        Set up default parameters
        """
        try:
            self.smu.write('smua.source.func = smua.OUTPUT_DCVOLTS')
            self.smu.write('smua.source.autorangev = smua.AUTORANGE_ON')
            self.smu.write('smua.source.autorangei = smua.AUTORANGE_ON')
            self.smu.write('smua.measure.autorangev = smua.AUTORANGE_ON')
            self.smu.write('smua.measure.autorangei = smua.AUTORANGE_ON')
            self.smu.write('smua.measure.nplc = 1')
            self.smu.write('smua.source.limiti = 1e-3')
            self.smu.write('smua.source.levelv = 0')
            self.smu.write('smua.source.output = smua.OUTPUT_OFF')
        except Exception as e:
            print(f"Error in default_setup: {repr(e)}")

    def close(self):
        """
        Gracefully close the device connection
        """
        try:
            self.output = False
            # 是否复位可由用户决定，可保留也可注释掉
            self.reset_device()
            self.smu.close()
            print("Keithley2600 device closed successfully.")
        except Exception as e:
            print(f"Error closing device: {repr(e)}")

    def __del__(self):
        """
        兜底的资源清理：__del__不一定会被及时调用，推荐使用 with 或手动 close()
        """
        try:
            self.close()
        except Exception as e:
            print(f"Error in __del__: {repr(e)}")

    @property
    def output(self):
        """Get the output state: True if output is on, False otherwise."""
        try:
            response = self.smu.query('print(smua.source.output)')
            return int(response.strip()) == 1
        except Exception as e:
            print(f"Error in output getter: {repr(e)}")
            return False

    @output.setter
    def output(self, state):
        """Set the output state: True to turn on, False to turn off."""
        try:
            if state:
                self.smu.write('smua.source.output = smua.OUTPUT_ON')
            else:
                self.smu.write('smua.source.output = smua.OUTPUT_OFF')
        except Exception as e:
            print(f"Error in output setter: {repr(e)}")

    @property
    def source_function(self):
        """Get the source function: 'voltage' or 'current'."""
        try:
            response = self.smu.query('print(smua.source.func)')
            return 'voltage' if int(response.strip()) == 0 else 'current'
        except Exception as e:
            print(f"Error in source_function getter: {repr(e)}")
            return 'voltage'  # 默认返回电压源模式

    @source_function.setter
    def source_function(self, function):
        """Set the source function: 'voltage' or 'current'."""
        try:
            if function.lower() == 'voltage':
                self.smu.write('smua.source.func = smua.OUTPUT_DCVOLTS')
            elif function.lower() == 'current':
                self.smu.write('smua.source.func = smua.OUTPUT_DCAMPS')
            else:
                raise ValueError("Function must be 'voltage' or 'current'")
        except Exception as e:
            print(f"Error in source_function setter: {repr(e)}")

    @property
    def nplc(self):
        """Get the number of power line cycles."""
        try:
            response = self.smu.query('print(smua.measure.nplc)')
            return float(response.strip())
        except Exception as e:
            print(f"Error in nplc getter: {repr(e)}")
            return 1.0

    @nplc.setter
    def nplc(self, nplc):
        """Set the number of power line cycles (NPLC)."""
        try:
            self.smu.write(f'smua.measure.nplc = {nplc}')
        except Exception as e:
            print(f"Error in nplc setter: {repr(e)}")

    @property
    def delay(self):
        """Get the source delay (s)."""
        try:
            response = self.smu.query('print(smua.source.delay)')
            return float(response.strip())
        except Exception as e:
            print(f"Error in delay getter: {repr(e)}")
            return 0.001

    @delay.setter
    def delay(self, delay):
        """Set the source delay (s). Ensures a minimum of 0.001 s."""
        try:
            delay = max(0.001, delay)
            self.smu.write(f'smua.source.delay = {delay}')
        except Exception as e:
            print(f"Error in delay setter: {repr(e)}")

    @property
    def autorange_i(self):
        """Get the current autorange state (True/False)."""
        try:
            response = self.smu.query('print(smua.measure.autorangei)')
            return int(response.strip()) == 1
        except Exception as e:
            print(f"Error in autorange_i getter: {repr(e)}")
            return True

    @autorange_i.setter
    def autorange_i(self, state):
        """Set the current autorange state (True/False)."""
        try:
            if state:
                self.smu.write('smua.measure.autorangei = smua.AUTORANGE_ON')
            else:
                self.smu.write('smua.measure.autorangei = smua.AUTORANGE_OFF')
        except Exception as e:
            print(f"Error in autorange_i setter: {repr(e)}")

    @property
    def autorange_v(self):
        """Get the voltage autorange state (True/False)."""
        try:
            response = self.smu.query('print(smua.measure.autorangev)')
            return int(response.strip()) == 1
        except Exception as e:
            print(f"Error in autorange_v getter: {repr(e)}")
            return True

    @autorange_v.setter
    def autorange_v(self, state):
        """Set the voltage autorange state (True/False)."""
        try:
            if state:
                self.smu.write('smua.measure.autorangev = smua.AUTORANGE_ON')
            else:
                self.smu.write('smua.measure.autorangev = smua.AUTORANGE_OFF')
        except Exception as e:
            print(f"Error in autorange_v setter: {repr(e)}")

    @property
    def level_v(self):
        """Get the voltage output level (V)."""
        try:
            response = self.smu.query('print(smua.source.levelv)')
            return float(response.strip())
        except Exception as e:
            print(f"Error in level_v getter: {repr(e)}")
            return 0.0

    @level_v.setter
    def level_v(self, v_level):
        """Set the voltage output level (V)."""
        try:
            self.smu.write(f'smua.source.levelv = {v_level}')
        except Exception as e:
            print(f"Error in level_v setter: {repr(e)}")

    @property
    def level_i(self):
        """Get the current output level (A)."""
        try:
            response = self.smu.query('print(smua.source.leveli)')
            return float(response.strip())
        except Exception as e:
            print(f"Error in level_i getter: {repr(e)}")
            return 0.0

    @level_i.setter
    def level_i(self, i_level):
        """Set the current output level (A)."""
        try:
            self.smu.write(f'smua.source.leveli = {i_level}')
        except Exception as e:
            print(f"Error in level_i setter: {repr(e)}")

    @property
    def limit_i(self):
        """Get the limit of the current output (A)."""
        try:
            response = self.smu.query('print(smua.source.limiti)')
            return float(response.strip())
        except Exception as e:
            print(f"Error in limit_i getter: {repr(e)}")
            return 1e-3

    @limit_i.setter
    def limit_i(self, i_limit):
        """Set the limit of the current output (A)."""
        try:
            self.smu.write(f'smua.source.limiti = {i_limit}')
        except Exception as e:
            print(f"Error in limit_i setter: {repr(e)}")

    @property
    def limit_v(self):
        """Get the limit of the voltage output (V)."""
        try:
            response = self.smu.query('print(smua.source.limitv)')
            return float(response.strip())
        except Exception as e:
            print(f"Error in limit_v getter: {repr(e)}")
            return 20.0

    @limit_v.setter
    def limit_v(self, v_limit):
        """Set the limit of the voltage output (V)."""
        try:
            self.smu.write(f'smua.source.limitv = {v_limit}')
        except Exception as e:
            print(f"Error in limit_v setter: {repr(e)}")
class MemristorTester:
    """
    Base class for memristor testers.
    Provides common functionality for all tester classes.
    """
    def __init__(self, keithley):
        self.keithley = keithley
        self.device_info = {
            'salt_type': '',
            'concentration': '',
            'device_number': ''
        }

    def setup_device_info(self):
        """
        Prompt user input for device info (Chinese comments remain).
        """
        self.device_info['salt_type'] = input("Enter salt type (e.g. NaCl): ")
        self.device_info['concentration'] = input("Enter concentration (e.g. 1M): ")
        self.device_info['device_number'] = input("Enter device number: ")
        return self.device_info

    def prepare_save_folders(self, tester_type: str, suffix_label: str):
        """
        Prepare the folder structure:
          C:/Users/Lab/Desktop/Spyder 6 measurement data/YYYYMMDD/tester_type/[timestamp_salt_conc_dev_suffix_label]
        
        :param tester_type: a short string indicating the test type (e.g. 'ltp_ltd_tester')
        :param suffix_label: a unique label, e.g. "NOGAP_pw_0.1_pt_10"
        :return: final_folder path
        """
        # 1) Base directory
        base_dir = r"C:/Users/Lab/Desktop/Spyder 6 mesurement data"
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)

        # 2) Date folder
        today_str = datetime.now().strftime("%Y%m%d")
        date_folder = os.path.join(base_dir, today_str)
        if not os.path.exists(date_folder):
            os.makedirs(date_folder)

        # 3) Tester type folder
        tester_folder = os.path.join(date_folder, tester_type)
        if not os.path.exists(tester_folder):
            os.makedirs(tester_folder)

        # 4) Build a final subfolder name incorporating
        #    - a timestamp
        #    - salt type, concentration, device number
        #    - user-provided suffix (test parameters)
        stamp = english_timestamp()  # e.g. "20250401_125959"
        salt = self.device_info.get('salt_type','salt')
        conc = self.device_info.get('concentration','conc')
        dev  = self.device_info.get('device_number','dev')
        final_dir_name = f"{stamp}_{salt}_{conc}_Dev{dev}_{suffix_label}"

        final_path = os.path.join(tester_folder, final_dir_name)
        if not os.path.exists(final_path):
            os.makedirs(final_path)

        return final_path

    def save_data_csv(self, folder, prefix, data):
        """
        Save data to CSV with a time-based prefix and checking for existing files.
        This ensures we do not overwrite files, and each file name includes a time stamp.
        """
        # Build base file name with prefix
        base_name = f"{prefix}"
        # We can add a time stamp if you want for each CSV:
        # e.g. f"{prefix}_{english_timestamp()}"
        # or just do it once in folder creation. 
        # For demonstration, let's keep time stamp in prefix:
        # prefix = prefix + "_" + english_timestamp()

        csv_name = f"{base_name}.csv"
        save_path = os.path.join(folder, csv_name)

        # If file exists, increment a numerical suffix
        if os.path.exists(save_path):
            idx = 1
            while os.path.exists(save_path):
                new_name = f"{base_name}_{idx}.csv"
                save_path = os.path.join(folder, new_name)
                idx += 1

        with open(save_path, 'w', newline='') as f:
            writer = csv.writer(f)
            # You can adapt column headers as needed
            writer.writerow(["Time(s)", "Voltage(V)", "Current(A)"])
            for row in data:
                writer.writerow(row)

        print(f"[Data saved] {save_path}")
        return save_path

    def run_test(self):
        """
        Base class: each child class must implement run_test.
        """
        raise NotImplementedError("Subclasses must implement run_test.")
