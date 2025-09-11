import numpy as np
import matplotlib.pyplot as plt

# Example: suppose ch1 is one of your processed channels (replace with real data)
# For demo, I'll fake a channel signal:
time = np.linspace(0, 130, 1000)   # 130 seconds, 1000 samples
ch1 = 500 + 50*np.sin(2*np.pi*3*time/130)  # fake capacitance just for structure

# 🔹 Force cycles: 3 ramps from 0 → 10 N
force = np.linspace(0, 10, np.size(ch1))

# Plot Force vs Time
plt.figure(figsize=(10,6))
plt.plot(time, force, color="red", label="Force (N)", linewidth=2)
plt.xlabel("Time (s)")
plt.ylabel("Force (N)")
plt.title("Force vs Time")
plt.grid(True, alpha=0.4)
plt.legend()
plt.tight_layout()
plt.show()

# # 🔹 If you want Force vs Capacitance (instead of vs time):
# plt.figure(figsize=(10,6))
# plt.plot(force, ch1, color="blue", label="CH1 vs Force", linewidth=2)
# plt.xlabel("Force (N)")
# plt.ylabel("Capacitance (pF)")
# plt.title("Force vs Capacitance (CH1)")
# plt.grid(True, alpha=0.4)
# plt.legend()
# plt.tight_layout()
# plt.show()
