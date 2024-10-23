# Rouen Delivery Route Optimization

## Description

This project utilizes Python libraries to optimize delivery routes in Rouen, France, based on a set of delivery points. The program retrieves a road network using the OpenStreetMap data, calculates the optimal route for deliveries using the Traveling Salesman Problem (TSP) solver from Google OR-Tools, and visualizes the results on an interactive Folium map.

## Features

- Downloads the road network for Rouen and calculates travel times based on speed limits.
- Finds nearby cities within a specified radius.
- Loads delivery points from an Excel file.
- Calculates the shortest delivery route using the TSP algorithm.
- Visualizes the route on an interactive map with markers for delivery points.
- Outputs total delivery distance and duration.

## Prerequisites

Before running the project, ensure you have the following software installed:

- Python 3.6 or higher
- pip (Python package installer)

## Installation

To install the required Python libraries, run the following command:

```bash
pip install -r requirements.txt
```

Additionally, make sure you have an Excel file named `deliveries_data.xlsx` in the same directory as the script, structured as follows:

| Package ID | lat     | long   |
|------------|---------|--------|
| 1          | 49.44   | 1.10   |
| 2          | 49.45   | 1.11   |

## Usage

1. Clone or download the repository to your local machine.
2. Ensure the `deliveries_data.xlsx` file is in the project directory with the correct format.
3. Run the Python script:

```bash
python delivery_route_optimization.py
```

4. After the execution, an HTML file named `rouen_deliveries_map.html` will be generated, which contains the interactive map of delivery routes.

## Output

The output will include:

- A printed log of the optimal TSP path.
- Total delivery distance and duration.
- An interactive HTML map (`rouen_deliveries_map.html`) with the delivery points and optimized route visualized.

## Example of Output

```
Optimal TSP path: [0, 1, 2, ...]
Total delivery distance: 5000 meters
Total delivery duration: 600 seconds
Carte de Rouen avec points de livraison et réseau routier générée : 'rouen_deliveries_map.html'
```

## Conclusion

This project provides an efficient way to optimize delivery routes using real road data, making it beneficial for logistics and delivery services. Future improvements could include implementing a user interface for easier data input and additional route optimization features.