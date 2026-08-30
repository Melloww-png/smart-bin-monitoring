#0599YFRR Daniel Clementrich Houston CW2 assignment
#Sensor simulation

import webbrowser
import random
import time
import json
import threading
from datetime import datetime

from flask import Flask, jsonify, render_template_string, request
from azure.iot.device import IoTHubDeviceClient, Message

from config import CONNECTION_STRING


app = Flask(__name__)



bin_height = 100
number_of_bins = 4

waste_increase = 5
update_time = 5


bin_fill_levels = {}
latest_bins = {}
history = []

current_scenario = None
simulation_running = False

simulation_thread = None
stop_simulation = threading.Event()



scenario_names = {
    "1": "Random Waste Percentage",
    "2": "Low Waste Percentage",
    "3": "High Waste Percentage",
    "4": "Full Waste Percentage"
}



def initialize_bins(scenario):

    global bin_fill_levels

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
            bin_fill_levels[bin_id] = random.randint(0, 40)



def calculate_bin_data(bin_id, fill_level):

    distance = bin_height - fill_level

    if fill_level >= 100:

        status = "Full"
        bin_access = "CLOSED - Not Accepting More Trash"
        alert = "Bin Full - Immediate Collection is Required"

    elif fill_level >= 75:

        status = "Nearly Full"
        bin_access = "OPEN"
        alert = "ALERT!: Bin Almost full Collection Required Soon!"

    elif fill_level >= 50:

        status = "Half Full"
        bin_access = "OPEN"
        alert = "ALERT!: Bin is Half Full"

    elif fill_level >= 20:

        status = "Less Than Half Full"
        bin_access = "OPEN"
        alert = "No Alert - Bin Has Enough Space"

    else:

        status = "Almost Empty"
        bin_access = "OPEN"
        alert = "No Alert - Bin is Close to Empty"

    return {
        "bin_id": bin_id,
        "sensor_distance": round(distance, 1),
        "fill_level": round(fill_level, 1),
        "status": status,
        "access": bin_access,
        "alert": alert,
        "updated_at": datetime.now().strftime("%H:%M:%S")
        }



def run_simulation():

    global latest_bins
    global history
    global simulation_running

    iot_client = None

    try:

        iot_client = IoTHubDeviceClient.create_from_connection_string(
            CONNECTION_STRING)

        iot_client.connect()

        print("\n==================================")
        print("Connected to Azure IoT Hub")
        print("Simulation Started")
        print("==================================")

        while not stop_simulation.is_set():

            all_bins_full = True

            for bin_number in range(1, number_of_bins + 1):

                if stop_simulation.is_set():
                    break

                bin_id = f"BIN{bin_number:03}"

                fill_level = bin_fill_levels[bin_id]

                bin_data = calculate_bin_data(
                    bin_id,
                    fill_level)

                latest_bins[bin_id] = bin_data.copy()

                history.append({
                    **bin_data,
                    "timestamp": datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                })

                if len(history) > 100:
                    history = history[-100:]

                data = {
                    "bin_id": bin_data["bin_id"],
                    "sensor_distance": bin_data["sensor_distance"],
                    "fill_level": bin_data["fill_level"],
                    "status": bin_data["status"],
                    "access": bin_data["access"],
                    "alert": bin_data["alert"],}

                message = Message(json.dumps(data))

                message.content_type = "application/json"
                message.content_encoding = "utf-8"

                iot_client.send_message(message)

                print(
                    f"{bin_id} | "
                    f"Fill: {fill_level}% | "
                    f"Status: {bin_data['status']} | "
                    f"Data sent to Azure IoT Hub")

                if fill_level < 100:

                    all_bins_full = False

                    fill_level += waste_increase
                    fill_level = min(fill_level, 100)

                    bin_fill_levels[bin_id] = fill_level

            if all_bins_full:

                print("\n==================================")
                print("ALL BINS ARE FULL")
                print("IMMEDIATE COLLECTION IS REQUIRED")
                print("ALL BINS ARE NOT ACCEPTING MORE TRASH")
                print("==================================")

                break

            stop_simulation.wait(update_time)

    except Exception as error:

        print(f"\nSimulation Error: {error}")

    finally:

        simulation_running = False

        if iot_client:
            try:
                iot_client.disconnect()
                print("Disconnected from Azure IoT Hub")
            except:
                pass



@app.route("/start-simulation", methods=["POST"])
def start_simulation():

    global current_scenario
    global simulation_running
    global simulation_thread
    global latest_bins
    global history

    data = request.get_json()

    scenario = data.get("scenario")

    if scenario not in ["1", "2", "3", "4"]:

        return jsonify({"success": False,"message": "Invalid scenario"})

    if simulation_running:

        stop_simulation.set()

        if simulation_thread and simulation_thread.is_alive():
            simulation_thread.join(timeout=2)

    stop_simulation.clear()

    latest_bins = {}
    history = []

    current_scenario = scenario

    initialize_bins(scenario)

    simulation_running = True

    simulation_thread = threading.Thread(
        target=run_simulation,
        daemon=True)

    simulation_thread.start()

    return jsonify({"success": True,
                    "scenario": scenario_names[scenario],
                    "message": "Simulation started successfully"})



@app.route("/api/dashboard")
def dashboard_data():

    bins = list(latest_bins.values())

    if bins:

        active_alerts = sum(
            1 for bin_data in bins
            if bin_data["fill_level"] >= 50)

        collection_required = sum(
            1 for bin_data in bins
            if bin_data["fill_level"] >= 90)

        full_bins = sum(
            1 for bin_data in bins
            if bin_data["fill_level"] >= 100)

    else:

        active_alerts = 0
        collection_required = 0
        full_bins = 0

    return jsonify({

        "bins": bins,

        "summary": {
            "total_bins": number_of_bins,
            "active_alerts": active_alerts,
            "collection_required": collection_required,
            "full_bins": full_bins},

        "scenario": scenario_names.get(
            current_scenario,
            "No Simulation Selected"),

        "running": simulation_running,

        "all_bins_full": (len(bins) == number_of_bins
            and full_bins == number_of_bins)
    })




@app.route("/api/history")
def get_history():

    return jsonify(history[-30:][::-1])



# MAIN DASHBOARD
#------------------------------------------------

@app.route("/")
def dashboard():

    return render_template_string("""
<!DOCTYPE html>
<html lang="en">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<title>Smart Public Bin Monitoring System</title>


<style>

/* ==================================
   FONT
================================== */

@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap');


/* ==================================
   COLOURS
   Muted Sage + Dusty Olive
================================== */

:root {

    --background: #E9ECE4;
    --surface: #F7F8F4;

    --sage: #8F9B87;
    --sage-dark: #65715E;

    --olive: #6F7455;
    --olive-dark: #50543D;

    --border: #CDD3C8;

    --text: #30362D;
    --text-light: #697064;

    --warning: #A08B5B;
    --danger: #8A655C;

}


/* ==================================
   GLOBAL
================================== */

* {
    box-sizing: border-box;
    scroll-behavior: smooth;
}

body {

    margin: 0;

    background: var(--background);

    color: var(--text);

    font-family: "Manrope", sans-serif;

}

button {
    font-family: inherit;
}


/* ==================================
   HEADER
================================== */

header {

    background: var(--surface);

    border-bottom: 1px solid var(--border);

    position: sticky;

    top: 0;

    z-index: 100;

}

.header-container {

    max-width: 1300px;

    margin: auto;

    padding: 18px 30px;

    display: flex;

    align-items: center;

    justify-content: space-between;

}

.logo h1 {

    margin: 0;

    font-size: 19px;

    font-weight: 800;

    letter-spacing: -0.5px;

}

.logo p {

    margin: 4px 0 0;

    font-size: 11px;

    color: var(--text-light);

}


/* ==================================
   NAVIGATION
================================== */

nav {

    display: flex;

    gap: 8px;

}

.nav-button {

    background: transparent;

    border: none;

    padding: 9px 14px;

    cursor: pointer;

    border-radius: 7px;

    color: var(--text-light);

    font-size: 13px;

    font-weight: 700;

}

.nav-button:hover {

    background: var(--background);

    color: var(--olive-dark);

}


/* ==================================
   MAIN
================================== */

main {

    max-width: 1300px;

    margin: auto;

    padding: 40px 30px 70px;

}

section {

    scroll-margin-top: 100px;

    margin-bottom: 45px;

}


/* ==================================
   SECTION HEADER
================================== */

.section-title {

    margin-bottom: 20px;

}

.section-title h2 {

    margin: 0 0 5px;

    font-size: 22px;

}

.section-title p {

    margin: 0;

    color: var(--text-light);

    font-size: 13px;

}


/* ==================================
   SIMULATION BUTTONS
================================== */

.simulation-grid {

    display: grid;

    grid-template-columns: repeat(4, 1fr);

    gap: 14px;

}

.scenario-button {

    border: 1px solid var(--border);

    background: var(--surface);

    padding: 20px;

    border-radius: 10px;

    cursor: pointer;

    text-align: left;

    transition: 0.2s;

}

.scenario-button:hover {

    border-color: var(--sage-dark);

    transform: translateY(-2px);

}

.scenario-button.active {

    background: var(--sage);

    border-color: var(--sage-dark);

    color: white;

}

.scenario-number {

    display: block;

    font-size: 11px;

    font-weight: 800;

    margin-bottom: 8px;

}

.scenario-name {

    font-size: 13px;

    font-weight: 700;

}


/* ==================================
   SYSTEM STATUS
================================== */

.system-bar {

    margin-top: 20px;

    padding: 14px 18px;

    background: var(--surface);

    border: 1px solid var(--border);

    border-radius: 9px;

    display: flex;

    justify-content: space-between;

    align-items: center;

    font-size: 13px;

}

.status-indicator {

    display: flex;

    align-items: center;

    gap: 8px;

}

.status-dot {

    width: 9px;

    height: 9px;

    border-radius: 50%;

    background: var(--text-light);

}

.status-dot.running {

    background: var(--olive);

}


/* ==================================
   SUMMARY
================================== */

.summary-grid {

    display: grid;

    grid-template-columns: repeat(3, 1fr);

    gap: 15px;

}

.summary-card {

    background: var(--surface);

    border: 1px solid var(--border);

    border-radius: 10px;

    padding: 20px;

}

.summary-label {

    color: var(--text-light);

    font-size: 11px;

    font-weight: 700;

    text-transform: uppercase;

}

.summary-value {

    font-size: 28px;

    font-weight: 800;

    margin-top: 10px;

}


/* ==================================
   BIN GRID
================================== */

.bin-grid {

    display: grid;

    grid-template-columns: repeat(2, 1fr);

    gap: 18px;

}

.bin-card {

    background: var(--surface);

    border: 1px solid var(--border);

    border-radius: 10px;

    padding: 22px;

}

.bin-card.full {
    border-color: var(--danger);
    background: #F7F1EF;
}

.bin-card.full .progress-fill {
    background: var(--danger);
}

.bin-top {

    display: flex;

    justify-content: space-between;

    align-items: center;

    margin-bottom: 18px;

}

.bin-name {

    font-size: 16px;

    font-weight: 800;

}

.bin-status {

    font-size: 11px;

    font-weight: 800;

    padding: 6px 10px;

    border-radius: 20px;

    background: var(--background);

}

.bin-status.empty {
    background: var(--background);
    color: var(--text-light);
}

.bin-status.space {
    background: #E3E8DF;
    color: var(--sage-dark);
}

.bin-status.half {
    background: #E8E1CE;
    color: var(--warning);
}

.bin-status.nearly {
    background: #E6D8C8;
    color: #80654A;
}

.bin-status.full {
    background: #E8D5D0;
    color: var(--danger);
}


/* ==================================
   BIN ACCESS
================================== */

.access-open {
    color: var(--sage-dark);
}

.access-closed {
    color: var(--danger);
    font-weight: 800;

.bin-details {

    display: grid;

    grid-template-columns: repeat(2, 1fr);

    gap: 15px;

}

.detail-label {

    font-size: 10px;

    color: var(--text-light);

    font-weight: 700;

    text-transform: uppercase;

}

.detail-value {

    margin-top: 5px;

    font-size: 13px;

    font-weight: 700;

}


/* ==================================
   FILL BAR
================================== */

.progress-container {

    margin-top: 20px;

}

.progress-label {

    display: flex;

    justify-content: space-between;

    font-size: 11px;

    font-weight: 700;

    margin-bottom: 8px;

}

.progress-bar {

    height: 10px;

    background: var(--background);

    border-radius: 10px;

    overflow: hidden;

}

.progress-fill {

    height: 100%;

    background: var(--sage-dark);

    border-radius: 10px;

    transition: width 0.5s;

}


/* ==================================
   ALERT
================================== */

.bin-alert {

    margin-top: 18px;

    padding: 12px;

    background: var(--background);

    border-left: 3px solid var(--olive);

    font-size: 11px;

    font-weight: 700;

}

.bin-alert.danger {

    border-left-color: var(--danger);

}


/* ==================================
   FULL BINS WARNING
================================== */

.full-warning {

    display: none;

    background: var(--olive-dark);

    color: white;

    padding: 30px;

    border-radius: 10px;

}

.full-warning.show {

    display: block;

}

.full-warning h2 {

    margin: 0 0 10px;

}

.full-warning p {

    margin: 7px 0;

    font-size: 13px;

    font-weight: 700;

}


/* ==================================
   HISTORY
================================== */

.history-table {

    width: 100%;

    border-collapse: collapse;

    background: var(--surface);

    border: 1px solid var(--border);

    border-radius: 10px;

    overflow: hidden;

}

.history-table th {

    text-align: left;

    padding: 14px;

    font-size: 10px;

    text-transform: uppercase;

    color: var(--text-light);

    background: var(--background);

}

.history-table td {

    padding: 14px;

    border-top: 1px solid var(--border);

    font-size: 12px;

}


/* ==================================
   RESPONSIVE
================================== */

@media (max-width: 850px) {

    .simulation-grid,
    .summary-grid {
        grid-template-columns: repeat(2, 1fr);
    }

}

@media (max-width: 650px) {

    .header-container {

        flex-direction: column;

        align-items: flex-start;

        gap: 15px;

    }

    nav {

        width: 100%;

        overflow-x: auto;

    }

    .bin-grid {

        grid-template-columns: 1fr;

    }

    .simulation-grid,
    .summary-grid {

        grid-template-columns: 1fr;

    }

    main {

        padding: 30px 18px;

    }

}

</style>

</head>


<body>


<!-- ==================================
     HEADER
================================== -->

<header>

    <div class="header-container">

        <div class="logo">

            <h1>SMART PUBLIC BIN MONITORING SYSTEM</h1>

            <p>
                Azure IoT Hub • Stream Analytics • Cosmos DB
            </p>

        </div>


        <nav>

            <button
                class="nav-button"
                onclick="scrollToSection('overview')"
            >
                Overview
            </button>

            <button
                class="nav-button"
                onclick="scrollToSection('bins')"
            >
                Bins
            </button>

            <button
                class="nav-button"
                onclick="scrollToSection('alerts')"
            >
                Alerts
            </button>

            <button
                class="nav-button"
                onclick="scrollToSection('history')"
            >
                History
            </button>

        </nav>

    </div>

</header>


<!-- ==================================
     MAIN
================================== -->

<main>


<!-- ==================================
     SIMULATION
================================== -->

<section id="overview">

    <div class="section-title">

        <h2>Simulation Scenario</h2>

        <p>
            Select a scenario to begin the smart bin simulation.
        </p>

    </div>


    <div class="simulation-grid">

        <button
            class="scenario-button"
            onclick="startSimulation('1', this)"
        >

            <span class="scenario-number">SCENARIO 01</span>

            <span class="scenario-name">
                Random Waste Percentage
            </span>

        </button>


        <button
            class="scenario-button"
            onclick="startSimulation('2', this)"
        >

            <span class="scenario-number">SCENARIO 02</span>

            <span class="scenario-name">
                Low Waste Percentage
            </span>

        </button>


        <button
            class="scenario-button"
            onclick="startSimulation('3', this)"
        >

            <span class="scenario-number">SCENARIO 03</span>

            <span class="scenario-name">
                High Waste Percentage
            </span>

        </button>


        <button
            class="scenario-button"
            onclick="startSimulation('4', this)"
        >

            <span class="scenario-number">SCENARIO 04</span>

            <span class="scenario-name">
                Full Waste Percentage
            </span>

        </button>

    </div>


    <div class="system-bar">

        <div class="status-indicator">

            <div
                id="statusDot"
                class="status-dot"
            ></div>

            <span id="systemStatus">
                Waiting for simulation
            </span>

        </div>

        <strong id="scenarioDisplay">
            No Simulation Selected
        </strong>

    </div>

</section>


<!-- ==================================
     SUMMARY
================================== -->

<section>

    <div class="section-title">

        <h2>System Overview</h2>

        <p>
            Current smart public bin monitoring data.
        </p>

    </div>


    <div class="summary-grid">

        <div class="summary-card">

            <div class="summary-label">
                Total Bins
            </div>

            <div
                id="totalBins"
                class="summary-value"
            >
                4
            </div>

        </div>



        <div class="summary-card">

            <div class="summary-label">
                Active Alerts
            </div>

            <div
                id="activeAlerts"
                class="summary-value"
            >
                0
            </div>

        </div>


        <div class="summary-card">

            <div class="summary-label">
                 Bins Requiring Collection
            </div>

            <div
                id="collectionRequired"
                class="summary-value"
            >
                0
            </div>

        </div>

    </div>

</section>


<!-- ==================================
     BIN MONITORING
================================== -->

<section id="bins">

    <div class="section-title">

        <h2>Bin Monitoring Overview</h2>

        <p>
            Live sensor readings from all four public bins.
        </p>

    </div>


    <div
        id="binGrid"
        class="bin-grid"
    >

        <div class="bin-card">
            Waiting for simulation data...
        </div>

    </div>

</section>


<!-- ==================================
     ALERTS
================================== -->

<section id="alerts">

    <div class="section-title">

        <h2>Collection Alert</h2>

        <p>
            Immediate collection warnings appear here.
        </p>

    </div>


    <div
        id="fullWarning"
        class="full-warning"
    >

        <h2>ALL BINS ARE FULL</h2>

        <p>IMMEDIATE COLLECTION IS REQUIRED</p>

        <p>ALL BINS ARE NOT ACCEPTING MORE TRASH</p>

    </div>


    <div
        id="individualAlerts"
        class="bin-grid"
    ></div>

</section>


<!-- ==================================
     HISTORY
================================== -->

<section id="history">

    <div class="section-title">

        <h2>Monitoring History</h2>

        <p>
            Latest simulation readings.
        </p>

    </div>


    <table class="history-table">

        <thead>

            <tr>

                <th>Time</th>

                <th>Bin ID</th>

                <th>Fill Level</th>

                <th>Status</th>

                <th>Alert</th>

            </tr>

        </thead>


        <tbody id="historyBody">

            <tr>

                <td colspan="5">
                    No monitoring data available.
                </td>

            </tr>

        </tbody>

    </table>

</section>


</main>


<script>


/* ==================================
   NAVIGATION
================================== */

function scrollToSection(id) {

    document
        .getElementById(id)
        .scrollIntoView({
            behavior: "smooth",
            block: "center"
        });

}


/* ==================================
   START SIMULATION
================================== */

async function startSimulation(
    scenario,
    button
) {

    document
        .querySelectorAll(".scenario-button")
        .forEach(btn => {
            btn.classList.remove("active");
        });

    button.classList.add("active");

    document.getElementById(
        "systemStatus"
    ).textContent = "Starting simulation...";


    try {

        const response = await fetch(
            "/start-simulation",
            {
                method: "POST",

                headers: {
                    "Content-Type":
                        "application/json"
                },

                body: JSON.stringify({
                    scenario: scenario
                })
            }
        );


        const result = await response.json();


        if (result.success) {

            document.getElementById(
                "scenarioDisplay"
            ).textContent = result.scenario;

            document.getElementById(
                "systemStatus"
            ).textContent = "Simulation Running";

            document
                .getElementById("statusDot")
                .classList.add("running");

        }

    }

    catch (error) {

        document.getElementById(
            "systemStatus"
        ).textContent =
            "Unable to start simulation";

        console.error(error);

    }

}


/* ==================================
   LOAD DASHBOARD
================================== */

async function updateDashboard() {

    try {

        const response = await fetch(
            "/api/dashboard"
        );

        const data = await response.json();


        // Summary
        document.getElementById(
            "totalBins"
        ).textContent =
            data.summary.total_bins;



        document.getElementById(
            "activeAlerts"
        ).textContent =
            data.summary.active_alerts;


        document.getElementById(
            "collectionRequired"
        ).textContent =
            data.summary.collection_required;


        // Scenario
        document.getElementById(
            "scenarioDisplay"
        ).textContent =
            data.scenario;


        // Running status
        const statusDot =
            document.getElementById("statusDot");


        if (data.running) {

            document.getElementById(
                "systemStatus"
            ).textContent =
                "Simulation Running";

            statusDot.classList.add("running");

        }

        else if (
            data.bins.length > 0
        ) {

            document.getElementById(
                "systemStatus"
            ).textContent =
                "Simulation Finished";

            statusDot.classList.remove("running");

        }


        // Bin cards
        const binGrid =
            document.getElementById("binGrid");


        if (data.bins.length > 0) {

            binGrid.innerHTML = "";

            data.bins.forEach(bin => {

                const isFull =
                    bin.fill_level >= 100;
                    let statusClass = "empty";
                    if (bin.fill_level >= 100) {
                        statusClass = "full";
                    } else if (bin.fill_level >= 75) {
                        statusClass = "half";
                    } else if (bin.fill_level >= 50) {
                        statusClass = "nearly";
                    } else if (bin.fill_level >= 20) {
                        statusClass = "space";
                    }

                binGrid.innerHTML += `

                    <div
                        class="bin-card ${
                            isFull ? "full" : ""
                        }"
                    >

                        <div class="bin-top">

                            <div class="bin-name">
                                ${bin.bin_id}
                            </div>

                            <div class="bin-status ${statusClass}">
                                ${bin.status}
                            </div>

                        </div>


                        <div class="bin-details">

                            <div>

                                <div class="detail-label">
                                    Sensor Distance
                                </div>

                                <div class="detail-value">
                                    ${bin.sensor_distance} cm
                                </div>

                            </div>


                            <div>

                                <div class="detail-label">
                                    Bin Access
                                </div>
                                <div class="detail-value ${
                                    bin.access.startsWith("CLOSED")
                                        ? "access-closed"
                                        : "access-open"
                                }">
                                    ${bin.access}
                                </div>

                            </div>

                        </div>


                        <div class="progress-container">

                            <div class="progress-label">

                                <span>
                                    Fill Level
                                </span>

                                <span>
                                    ${bin.fill_level}%
                                </span>

                                <div
                                    class="progress-fill ${
                                        bin.fill_level >= 100
                                            ? "full"
                                            : bin.fill_level >= 75
                                            ? "nearly"
                                            : bin.fill_level >= 50
                                            ? "half"
                                            : ""
                                    }"
                                    style="
                                        width: ${bin.fill_level}%
                                    "
                                ></div>

                            </div>

                        </div>


                        <div
                            class="bin-alert ${
                                isFull ? "danger" : ""
                            }"
                        >

                            ${bin.alert}

                        </div>

                    </div>

                `;

            });

        }


        // All bins full warning
        const fullWarning =
            document.getElementById(
                "fullWarning"
            );


        if (data.all_bins_full) {

            fullWarning.classList.add("show");

        }

        else {

            fullWarning.classList.remove("show");

        }


        // Individual alerts
        const alertsContainer =
            document.getElementById(
                "individualAlerts"
            );


        const alertBins =
            data.bins.filter(
                bin => bin.fill_level >= 50
            );


        if (alertBins.length > 0) {

            alertsContainer.innerHTML = "";

            alertBins.forEach(bin => {

                const isFull =
                    bin.fill_level >= 100;

                alertsContainer.innerHTML += `

                    <div class="bin-card ${
                        isFull ? "full" : ""
                    }">

                        <div class="bin-top">

                            <div class="bin-name">
                                ${bin.bin_id}
                            </div>

                            <div class="bin-status ${
                                isFull
                                    ? "full"
                                    : bin.fill_level >= 75
                                    ? "nearly"
                                    : "half"
                            }">

                                ${bin.status}

                            </div>

                        </div>

                        <div class="bin-alert ${
                            isFull ? "danger" : ""
                        }">

                            ${bin.alert}

                        </div>

                        <div class="detail-value ${
                            isFull
                                ? "access-closed"
                                : "access-open"
                        }">

                            ${bin.access}

                        </div>

                    </div>

                `;

            });

        }

        else {

            alertsContainer.innerHTML =
                `
                <div class="bin-card">
                    No active collection alerts.
                </div>
                `;

        }

    }

    catch (error) {

        console.error(
            "Dashboard update error:",
            error
        );

    }

}


/* ==================================
   LOAD HISTORY
================================== */

async function updateHistory() {

    try {

        const response =
            await fetch("/api/history");

        const history =
            await response.json();


        const historyBody =
            document.getElementById(
                "historyBody"
            );


        if (history.length > 0) {

            historyBody.innerHTML = "";

            history.forEach(item => {

                historyBody.innerHTML += `

                    <tr>

                        <td>
                            ${item.timestamp}
                        </td>

                        <td>
                            ${item.bin_id}
                        </td>

                        <td>
                            ${item.fill_level}%
                        </td>

                        <td>
                            ${item.status}
                        </td>

                        <td>
                            ${item.alert}
                        </td>

                    </tr>

                `;

            });

        }

    }

    catch (error) {

        console.error(
            "History update error:",
            error
        );

    }

}


/* ==================================
   AUTO REFRESH
================================== */

updateDashboard();
updateHistory();

setInterval(
    updateDashboard,
    2000
);

setInterval(
    updateHistory,
    5000
);


</script>


</body>
</html>
""")



if __name__ == "__main__":

    print()
    print("==================================")
    print("SMART BIN DASHBOARD")
    print("Opening website automatically...")
    print("==================================")


    def open_browser():
        webbrowser.open_new("http://127.0.0.1:5000")


    threading.Timer(1,open_browser).start()


    app.run(host="127.0.0.1",
            port=5000,
            debug=True,
            use_reloader=False)