#0599YFRR Daniel Clementrich Houston CW2 assignment
#Sensor simulatiion 

import random
import json 

from azure.iot.device import IoTHubDeviceClient, Message
from config import CONNECTION_STRING

client = IoTHubDeviceClient.create_from_connection_string(CONNECTION_STRING)


print("==================================")
print("Smart Public Bin Monitoring System")
print("==================================")

bin_height = 100
number_of_bins = 3
try:
    client.connect()
    print("\nConnected to Azure IoT Hub")

    for bin_number in range(1, number_of_bins + 1):

        # Ultrasonic sensor reading
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

        # sending data to Azure IoT Hub
        data = {
            "bin_id": f"BIN{bin_number:03}",
            "sensor_distance": distance,
            "fill_level": round(fill_level, 1),
            "status": status,
            "access": bin_access,
            "alert": alert
        }

        message = Message(json.dumps(data))
        message.content_type = "application/json"
        message.content_encoding = "utf-8"

        client.send_message(message)

        print("Data sent to Azure IoT Hub!")

finally:    
    client.disconnect()
    print("Disconnected from Azure IoT Hub")