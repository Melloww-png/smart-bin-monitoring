#0599YFRR Daniel Clementrich Houston CW2 assignment
#Sensor simulatiion 

import random

bin_height = 100

distance = random.randint(2, 100)  # Simulated distance reading from the ultrasonic sensor

print("Ultrasonic Sensor Simulation")
print("----------------------------")
print(f"Bin Height: {bin_height} cm")
print(f"Sensor Distance: {distance} cm")
fill_level = ((bin_height - distance) / bin_height) * 100

if fill_level >= 100:
    status = "Full - Immediate Collection Required"
    bin_access = "CLOSED - Not Accepting More Trash"
elif fill_level < 20:
    status = "Less than half"
    bin_access = "OPEN"
elif fill_level < 50:
    status = "Half full"
    bin_access = "OPEN"
elif fill_level < 80:
    status = "Getting Full"
    bin_access = "OPEN"
elif fill_level < 100:
    status = "Nearly Full"
    bin_access = "OPEN"

print(f"Fill Level: {fill_level:.1f}%")
print(f"Bin Status: {status}")
print(f"Bin Access: {bin_access}")