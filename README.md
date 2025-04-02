# Memristor Testing Suite

This repository provides a modular Python-based suite for testing memristive devices using a Keithley 2600 source meter. The system is designed to support various protocols inspired by neuromorphic plasticity.

（本仓库为基于 Python 的忆阻器测试程序，使用 Keithley 2600 仪器，可支持多种类脑可塑性测试协议。）

---

## 📁 Contents

- `main.py` – Entry point for selecting and running test modules  
  （主程序：用于选择不同测试模块并运行）
- `core.py` – Base class and Keithley 2600 control logic  
  （核心控制模块，封装 Keithley 的基本操作）
- `iv_curves_dc.py` – DC I-V curve measurement  
  （直流电压-电流曲线测试）
- `sin_tester.py` – Sine wave input and analysis  
  （正弦波测试）
- `ltp_ltd_tester.py` – Long-Term Potentiation / Depression  
  （长时程增强 / 抑制）
- `ppd_ppf_tester.py` – Paired-Pulse Depression / Facilitation  
  （成对脉冲抑制 / 促进）
- `stdp_tester.py` – Spike-Timing Dependent Plasticity  
  （脉冲时序依赖可塑性）
- `srdp_tester.py` – Spike-Rate Dependent Plasticity  
  （脉冲频率依赖可塑性）

---

## 🛠 Requirements

- Python ≥ 3.8  
- Dependencies:

```bash
pip install numpy matplotlib scipy scikit-learn pyvisa pandas
（依赖项包括 numpy, matplotlib, scipy 等，请确保安装。）

🚀 How to Use
Connect the Keithley 2600 device via USB/GPIB （将 Keithley 2600 仪器通过 USB 或 GPIB 接入电脑）

Run the main program:

bash
Copy
Edit
python main.py
Follow the prompts to select a test type and input parameters
（根据提示选择测试类型并输入参数）

Data and plots will be saved automatically
（程序会自动保存数据和图像）

📊 Output Structure
Test results are saved in a structured folder format:

css
Copy
Edit
Spyder 6 measurement data/
└── YYYYMMDD/
    └── [test_type]/
        └── [timestamp_salt_concentration_device_parameters]/
Each test folder contains:

Raw CSV data

Plots (PNG)

Parameter summaries

（每次测试都会自动创建时间戳子文件夹，包含原始数据和图像。）

🌍 Language and UI
The UI is in English for international accessibility
（程序界面使用英文，便于国际交流）

Chinese comments are included for local understanding
（代码中保留中文注释，方便中文用户理解）

📥 File Naming and Safety
All filenames auto-increment to prevent overwriting
（自动编号，避免文件覆盖）

Each test session gets a unique folder name based on timestamp + parameters
（每次测试生成唯一文件夹名，包含参数信息）

📬 Contact
Feel free to reach out if you have questions or suggestions.
（如有问题或建议，欢迎联系作者。）
