import pandas as pd
import matplotlib.pyplot as plt

# ==========================
# Load your CSV file
# ==========================
df = pd.read_csv("data/11182025_nomux_differential_Node1_CH0.csv")

# Assume your columns are named something like:
# timestamp, ch0, ch1
# (Print df.head() if you need to confirm)

time = df.iloc[:, 0]   # first column
ch0  = df.iloc[:, 1]   # second column
ch1  = df.iloc[:, 2]   # third column

# ==========================
# Make the Plot
# ==========================
plt.figure(figsize=(10,5))
plt.plot(time, ch0, label="CH0", linewidth=1.5)
# plt.plot(time, ch1, label="CH1", linewidth=1.5)

plt.title("CH0 and CH1 vs Time")
plt.xlabel("Time (s)")
plt.ylabel("Capacitance / Raw Units")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()
