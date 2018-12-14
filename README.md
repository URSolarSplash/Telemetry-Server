# Telemetry Server SDK
## Summary
The Rochester Solar Splash team has a need to collect extensive telemetry from sensors around our boat. Previously, we lacked a single system which could collect and log all the data from the boat in a single place for analysis.

The Telemetry Server is our effort to consolidate telemetry into a single system which is easy to use: The hardware is simple to setup, can be programmed with a minimal amount of code, and the network is expandable.

The Telemetry Server is a command-line application which runs in the background and handles the following tasks:
- Scanning of USB ports on the device for input sources
- Collection of telemetry data
- Parsing of data points and storage into a database
- API for retrieving data points or sets of data from another program (Telemetry UI)
- API for data over a radio transmitter
- Support for "proxy mode"; builts a database mirror of a remove computer and downloads data over radio

## Terminology
- *Telemetry Node* - Devices which collect data and use the Telemetry Client SDK to communicate over the network. Devices can read & write data points. Currently, the Client SDK is designed for Arduino boards.
- *Telemetry Server* - A device which scans the network for nodes, collecting and aggregating data from all nodes. The Telemetry Server can read in data points from nodes, send data to nodes, and output data to a file or over radio to a monitoring software.
- *Telemetry Store* - A data structure on the Telemetry Server, which stores the values of the telemetry data points. The Telemetry Store saves historical values for a data point, and can provide several metrics including last value, average, median, sum, etc.
- *Telemetry Network* - A system for connecting multiple Nodes to a single Server. Currently, this consists of a USB network in which all telemetry devices are connected via USB cable to the Server. This network is expandable through the use of USB hubs, which allow up to 127 devices to connect to the server.

## Design

The telemetry system consists of a single Telemetry Server, connected to multiple Telemetry Nodes.

This repository contains the SDK which handles all functionality for the Telemetry Server. The Server has been created in Python.

The server runs in a background thread. Once started, it will:
- Once per second, scan for new USB devices and attempt to connect to them.
- Scan ports for incoming data, and parse this data and store it in the Telemetry Store.
- Send data to any telemetry nodes that have requested to receive data.
- Send data over radio, if available.
- Periodically save data points to a file.
- If a network is connected, upload the data points to a remote server.

## How to Use
The Telemetry Server can be run in headless mode, or as part of the Telemetry UI. The Telemetry UI will automatically run the Server when it is started, so manual installation of the Telemetry Server is only needed for headless mode. In both cases, the Server requires some prerequisite libraries to be installed.

### Prerequisite Libraries
#### Python
`pip install websockets`<br>
`pip install peewee`<br>
`pip install jsonpickle`<br>
