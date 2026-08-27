#0599YFRR Daniel Clementrich Houston CW2 assignment
#Sensor simulation

import random
import time
import json
from azure.iot.device import IoTHubDeviceClient, Message

from config import CONNECTION_STRING


iot_client = IoTHubDeviceClient.create_from_connection_string(
    CONNECTION_STRING
)

print("==================================")
print("Smart Public Bin Monitoring System")
print("==================================")


bin_height = 100
number_of_bins = 3

waste_increase = 5

update_time = 5


print("\nSelect Simulation Scenario")
print("1. Random Waste Percentage")
print("2. Low Waste Percentage")
print("3. High Waste Percentage")
print("4. Full Waste Percentage")

scenario = input("Enter scenario number (1-4): ")


bin_fill_levels = {}


for bin_number in range(1, number_of_bins + 1):

    bin_id = f"BIN{bin_number:03}"



    if scenario == "1":
        bin_fill_levels[bin_id] = random.randint(0, 40)


    elif scenario == "2":
        bin_fill_levels[bin_id] = random.randint(0, 30)


    elif scenario == "3":
        bin_fill_levels[bin_id] = random.randint(50, 79)


    elif scenario == "4":
        bin_fill_levels[bin_id] = 100


    else:

        print("Invalid scenario selected. Using random simulation.")

        bin_fill_levels[bin_id] = random.randint(0, 40)


try:

    iot_client.connect()

    print("\nConnected to Azure IoT Hub")

    while True:


        for bin_number in range(1, number_of_bins + 1):

            bin_id = f"BIN{bin_number:03}"

            fill_level = bin_fill_levels[bin_id]

            distance = bin_height - fill_level



            if fill_level >= 100:

                status = "Full"

                bin_access = "CLOSED - Not Accepting More Trash"

                alert = "Bin Full - Immediate Collection is Required"


            elif fill_level >= 75:

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


            print()
            print(f"Bin {bin_number}")
            print("----------------------------")
            print(f"Bin ID: {bin_id}")
            print(f"Sensor Distance: {distance:.1f} cm")
            print(f"Fill Level: {fill_level:.1f}%")
            print(f"Bin Status: {status}")
            print(f"Bin Access: {bin_access}")
            print(f"System Alert: {alert}")


            data = {
                "bin_id": bin_id,
                "sensor_distance": round(distance, 1),
                "fill_level": round(fill_level, 1),
                "status": status,
                "access": bin_access,
                "alert": alert
            }


            message = Message(json.dumps(data))

            message.content_type = "application/json"

            message.content_encoding = "utf-8"

            iot_client.send_message(message)

            print("Data sent to Azure IoT Hub!")


            if fill_level < 100:

                fill_level += waste_increase

                fill_level = min(fill_level, 100)

                bin_fill_levels[bin_id] = fill_level


            if fill_level >= 100:

                print()
                print("==================================")
                print(f"{bin_id} IS FULL")
                print("BIN FULL")
                print("IMMEDIATE COLLECTION IS REQUIRED")
                print("BIN IS NOT ACCEPTING MORE TRASH")
                print("==================================")


        all_bins_full = all(
            bin_fill_levels[f"BIN{bin_number:03}"] >= 100
            for bin_number in range(1, number_of_bins + 1)
        )


        if all_bins_full:

            print()
            print("==================================")
            print("ALL BINS ARE FULL")
            print("IMMEDIATE COLLECTION IS REQUIRED")
            print("ALL BINS ARE NOT ACCEPTING MORE TRASH")
            print("==================================")

            break


        print()
        print(f"Waiting {update_time} seconds for more trash...")

        time.sleep(update_time)


finally:

    iot_client.disconnect()

    print("Disconnected from Azure IoT Hub")




# SMART BIN DASHBOARD

