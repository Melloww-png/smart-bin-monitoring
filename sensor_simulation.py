#0599YFRR Daniel Clementrich Houston CW2 assignment
#Sensor simulatiion 

import random

bin_height = 100
number_of_bins = 3

print("Smart Public Bin Monitoring System")
print("==================================")

for bin_number in range(1, number_of_bins + 1):

    # Simulated the ultrasonic sensor reading
    distance = random.randint(0, 100)

    # Calculate fill level
    fill_level = ((bin_height - distance) / bin_height) * 100

    # Determine bin status, access and alert
    if fill_level >= 100:
        status = "Full"
        bin_access = "CLOSED - Not Accepting More Trash"
        alert = "ALERT: Immediate Collection Required!"

    elif fill_level >= 80:
        status = "Nearly Full"
        bin_access = "OPEN"
        alert = "ALERT: Collection Required Soon!"

    elif fill_level >= 50:
        status = "Half Full"
        bin_access = "OPEN"
        alert = "WARNING: Bin is Half Full"

    elif fill_level >= 20:
        status = "Less Than Half Full"
        bin_access = "OPEN"
        alert = "No Alert - Bin Has Enough Space"

    else:
        status = "Almost Empty"
        bin_access = "OPEN"
        alert = "No Alert - Bin is Close to Empty"

    # Display results
    print()
    print(f"Bin {bin_number}")
    print("----------------------------")
    print(f"Sensor Distance: {distance} cm")
    print(f"Fill Level: {fill_level:.1f}%")
    print(f"Bin Status: {status}")
    print(f"Bin Access: {bin_access}")
    print(f"System Alert: {alert}")