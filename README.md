
# Delivery Route Optimizer and Tetris Truck Loader

This project consists of three main Python scripts designed to assist in logistics planning by optimizing delivery routes and simulating truck loading using a Tetris-like approach.

## Table of Contents
1. [Project Overview](#project-overview)
2. [Features](#features)
3. [Installation](#installation)
4. [Usage](#usage)
5. [Files Description](#files-description)
6. [Dependencies](#dependencies)

## Project Overview

The project aims to streamline the process of logistics and delivery by providing tools to:
- Optimize delivery routes based on time and distance using real-world map data.
- Visualize delivery paths on an interactive map.
- Simulate the loading of a truck using a Tetris-inspired approach, where each piece represents a package.

## Features

- **AddressFinder**: Finds delivery points and optimizes routes using real-time geolocation data.
- **Tetris Truck Loader**: Simulates the loading of packages in a truck using Tetris-like mechanics to maximize space utilization.
- **Route Visualization**: Generates an interactive map displaying the optimized delivery routes and delivery points.

## Installation

To run this project, follow these steps:

1. Clone the repository:
    ```bash
    git clone <repository-url>
    cd <repository-folder>
    ```
2. Create a virtual environment and activate it:
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```
3. Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

### 1. AddressFinder.py
Run this script to find and visualize optimal delivery routes based on provided delivery points.

```bash
python AddressFinder.py
```

### 2. dpdTetris.py
Run this script to simulate the Tetris-like truck loading.

```bash
python dpdTetris.py
```

### 3. project.py
Run this script to execute the complete process, from fetching delivery points to route optimization and visualization.

```bash
python project.py
```

## Files Description

- **AddressFinder.py**: 
    - Handles geocoding and route optimization using Google API, OSMNX, and NetworkX.
    - Visualizes the optimized routes on a map using Folium.

- **dpdTetris.py**: 
    - Implements a Tetris-like game where packages are represented as blocks.
    - Simulates the loading process of a truck to maximize space utilization.

- **project.py**: 
    - Integrates functionalities from both scripts to perform delivery point analysis, optimize routes, and provide a terminal output of the delivery sequence.

## Dependencies

To install these dependencies, use:
```bash
pip install -r requirements.txt
```
