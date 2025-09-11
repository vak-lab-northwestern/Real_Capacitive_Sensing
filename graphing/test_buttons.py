import matplotlib.pyplot as plt
from matplotlib.widgets import Button
import time

# Test button functionality
def test_button_click():
    print("Button clicked!")

# Create a simple plot with buttons
fig, ax = plt.subplots()
ax.plot([1, 2, 3, 4], [1, 4, 2, 3])
ax.set_title("Test Plot")

# Create buttons
ax_start = plt.axes([0.7, 0.02, 0.1, 0.05])
ax_stop = plt.axes([0.81, 0.02, 0.1, 0.05])

btn_start = Button(ax_start, "Start")
btn_stop = Button(ax_stop, "Stop")

btn_start.on_clicked(test_button_click)
btn_stop.on_clicked(test_button_click)

fig.subplots_adjust(bottom=0.18)
plt.show()

print("Test window opened. Click the buttons to test functionality.")
print("Close the window to exit.") 