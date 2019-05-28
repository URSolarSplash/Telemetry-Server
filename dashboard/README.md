# Telemetry UI Dashboard

## Summary
The Rochester Solar Splash team has a need to collect extensive telemetry from sensors around our boat. Previously, we lacked a single system which could collect and log all the data from the boat in a single place for analysis.

The URSS Telemetry System is our effort to consolidate telemetry into a single system which is easy to use: The hardware is simple to setup, can be programmed with a minimal amount of code, and the network is expandable. The system consists of a number of sensors connected to a central hub on the boat, which relays data to a shore computer over radio. The data is replicated in a database on both the boat and shore computer, and a UI software allows for monitoring of the live data.

This repository contains the Telemetry Dashboard UI, which allows for monitoring of the live streaming data from the telemetry system. The UI charts important data points, displays a live list of all data, and displays alarms for data points.

This version of the UI is designed for the system onboard the boat. The UI is optimized for deployment to a Raspberry Pi, and it shows dashboard information most relevant to the driver with large font sizes to improve readability.

### Telemetry System Components
**Telemetry Nodes** - Devices which collect and stream sensor data through a USB-serial connection to a central telemetry hub or computer. The Telemetry Node SDK is designed to pack data for the boat's sensors in order to improve transmission rate. The team has build an Arduino library which handles all data transmission functionality, and can be used in sensor board programming. The Telemetry Server will automatically detect and connect to
The SDK also includes the ability to poll data, allowing node devices to act based on data points in the telemetry system. This provides the capability for closed-loop control of the boat, for example during the Endurance event.

**Telemetry Server** - A command-line program which runs in the background and handles scanning for devices, collection of telemetry data, parsing and storage into a database, and an API for live data access. This software is run on both the telemetry hub and shore computer, and automatically replicates data between hubs connected by a radio serial transmitter.

**Telemetry UI (This Repository)** - See summary above.

## How to Use

## Screenshots

## UI System Design
