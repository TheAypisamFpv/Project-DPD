import osmnx as ox
import networkx as nx
import folium
import pandas as pd
from geopy.distance import geodesic
import requests
from folium.plugins import PolyLineTextPath
from ortools.constraint_solver import pywrapcp, routing_enums_pb2
import matplotlib.cm as cm
import numpy as np
import warnings
from tsp_solver.greedy import solve_tsp

# Suppress FutureWarnings
warnings.simplefilter(action='ignore', category=FutureWarning)


# Example file path
file_path = 'addresses_found.xlsx'

def load_points_from_excel(file_path):
    df = pd.read_excel(file_path)
    df['lat'] = df['lat'].astype(float)    # Add this line
    df['long'] = df['long'].astype(float)  # Add this line
    points = df[['lat', 'long']].values.tolist()
    names = df['Package ID'].tolist()
    return points, names

# Load points
points, names = load_points_from_excel(file_path)

def get_nearest_node(G, point):
    lat, lon = point
    lat = float(lat)  # Ensure lat is a float
    lon = float(lon)  # Ensure lon is a float
    return ox.distance.nearest_nodes(G, X=lon, Y=lat)

# Use the first point as the origin for the TSP
origin = points[0]
origin_city = (49.443512, 1.098445)

def find_nearby_cities(center_coords, radius_km=10):
    overpass_url = "http://overpass-api.de/api/interpreter"
    overpass_query = f"""
    [out:json];
    (
      node["place"="city"](around:{radius_km*1000},{center_coords[0]},{center_coords[1]});
      node["place"="town"](around:{radius_km*1000},{center_coords[0]},{center_coords[1]});
      node["place"="village"](around:{radius_km*1000},{center_coords[0]},{center_coords[1]});
    );
    out body;
    """
    response = requests.get(overpass_url, params={'data': overpass_query})
    data = response.json()
    
    nearby_cities = []
    for element in data['elements']:
        city_name = element['tags'].get('name')
        city_coords = (element['lat'], element['lon'])
        if geodesic(center_coords, city_coords).km <= radius_km:
            nearby_cities.append(city_name)
    
    return nearby_cities

# Ensure points is a list of tuples (latitude, longitude)
if not points or not all(isinstance(point, (list, tuple)) and len(point) == 2 for point in points):
    raise ValueError("The points list is not correctly formatted.")

# Create graph
G = ox.graph_from_point(
    center_point=origin_city,
    dist=5000,
    dist_type='bbox',
    network_type='drive'
)

# Get nearest nodes for all points
nodes = []
for point in points:
    node = get_nearest_node(G, point)
    nodes.append(node)

try:
    # First try to get graph from nearby cities
    places = find_nearby_cities(origin_city)
    if places:
        G = ox.graph_from_place(places, network_type='drive')
    else:
        # Fallback to getting graph from point if no cities found
        G = ox.graph_from_point(origin_city, dist=5000, network_type='drive')
except Exception as e:
    print(f"Failed to get graph from places, falling back to point: {e}")
    G = ox.graph_from_point(origin_city, dist=5000, network_type='drive')


# Add travel time to each edge in the graph
for u, v, k, data in G.edges(data=True, keys=True):
    if 'length' in data:
        # Get speed from OSM data or use defaults based on road type
        if 'maxspeed' in data:
            maxspeed_str = data['maxspeed'][0] if isinstance(data['maxspeed'], list) else data['maxspeed']
            try:
                if 'rural' in str(maxspeed_str).lower():
                    maxspeed = 80.0
                # Handle highway type that might be a list
                highway_type = data.get('highway', '')
                if isinstance(highway_type, list):
                    highway_type = highway_type[0]
                highway_type = str(highway_type).lower()
                
                if 'motorway' in highway_type:
                    maxspeed = 130.0
                elif 'trunk' in highway_type:
                    maxspeed = 110.0
                elif 'primary' in highway_type:
                    maxspeed = 90.0
                elif 'residential' in highway_type:
                    maxspeed = 30.0
                else:
                    try:
                        maxspeed = float(maxspeed_str)
                        maxspeed = min(maxspeed, 130.0)  # Cap at 130 km/h
                    except (ValueError, TypeError):
                        maxspeed = 50.0  # Default urban speed
            except (ValueError, TypeError):
                maxspeed = 50.0
        else:
            maxspeed = 50.0  # Default speed if no maxspeed data
            
        # Calculate travel time in seconds and add it to the edge data
        data['travel_time'] = data['length'] / (maxspeed * 1000 / 3600)


# Visualize the graph (optional)
# ox.plot_graph(G)

# Create the map centered on the origin
map_folium = folium.Map(location=origin, zoom_start=12)

# Create the map with package information
map_folium_final = folium.Map(location=origin, zoom_start=12)

# Define the starting point (point of collection)
delivery_points = [
    (point, name, f"PKG{i:04d}") # Generate package IDs like PKG0001
    for i, (point, name) in enumerate(zip(points, names), 1)
]

# Add points to the map with package IDs in tooltips
for point, name, pkg_id in delivery_points:
    tooltip_text = f"{name} (Tracking ID: {pkg_id})"
    folium.Marker(location=point, tooltip=tooltip_text).add_to(map_folium)

# Add points to the map with package IDs in tooltips
for point, name, pkg_id in delivery_points:
    tooltip_text = f"{name} (Tracking ID: {pkg_id})"
    folium.Marker(location=point, tooltip=tooltip_text).add_to(map_folium_final)

# Save the map to an HTML file
map_folium.save('map.html')

# -------------------------------
# 5. Calculer et afficher le chemin le plus rapide pour la livraison
# -------------------------------

# Add the depot address to the delivery points
depot_address = (49.377805, 1.115311)  # Replace with actual depot coordinates
delivery_points.insert(0, [depot_address])

# Create a distance matrix
num_points = len(delivery_points)
distance_matrix = [[0] * num_points for _ in range(num_points)]


for i in range(num_points):
    for j in range(num_points):
        if i != j:
            start_point = delivery_points[i][0]
            end_point = delivery_points[j][0]
            start_lat, start_lon = float(start_point[0]), float(start_point[1])
            end_lat, end_lon = float(end_point[0]), float(end_point[1])
            start_node = get_nearest_node(G, (start_lat, start_lon))
            end_node = get_nearest_node(G, (end_lat, end_lon))
            try:
                route_length = nx.shortest_path_length(G, start_node, end_node, weight='travel_time')
                distance_matrix[i][j] = route_length
            except nx.NetworkXNoPath:
                distance_matrix[i][j] = float('inf')


# Solve the TSP using OR-Tools
def create_data_model():
    data = {}
    data['distance_matrix'] = distance_matrix
    data['num_vehicles'] = 3
    data['depot'] = 0
    data['demands'] = [0, 1, 1, 2, 4, 2, 3, 1, 2, 1]  # Example demands for each location
    data['vehicle_capacities'] = [7, 7, 7]  # Capacities for each vehicle
    return data

data = create_data_model()
manager = pywrapcp.RoutingIndexManager(len(data['distance_matrix']), data['num_vehicles'], data['depot'])
routing = pywrapcp.RoutingModel(manager)

def distance_callback(from_index, to_index):
    from_node = manager.IndexToNode(from_index)
    to_node = manager.IndexToNode(to_index)
    return data['distance_matrix'][from_node][to_node]

transit_callback_index = routing.RegisterTransitCallback(distance_callback)

# Define cost of each arc
routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

# Add capacity constraint
def demand_callback(from_index):
    from_node = manager.IndexToNode(from_index)
    return data['demands'][from_node]

demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
routing.AddDimensionWithVehicleCapacity(
    demand_callback_index,
    0,  # null capacity slack
    data['vehicle_capacities'],  # vehicle maximum capacities
    True,  # start cumul to zero
    'Capacity')

# Setting first solution heuristic
search_parameters = pywrapcp.DefaultRoutingSearchParameters()
search_parameters.first_solution_strategy = (routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)

# Solve the problem
solution = routing.SolveWithParameters(search_parameters)



def get_tsp_paths(manager, routing, solution):
    tsp_paths = []
    for vehicle_id in range(data['num_vehicles']):
        index = routing.Start(vehicle_id)
        route = []
        while not routing.IsEnd(index):
            route.append(manager.IndexToNode(index))
            index = solution.Value(routing.NextVar(index))
        route.append(manager.IndexToNode(index))
        tsp_paths.append(route)
    return tsp_paths

if solution:
    tsp_paths = get_tsp_paths(manager, routing, solution)

# Define a list of colors for the vehicles
vehicle_colors = ['#FF0000', '#00FF00', '#0000FF']  # Red, Green, Blue

# Initialize total distance and duration
total_delivery_distance = 0
total_delivery_duration = 0

# Iterate over the TSP path and calculate the shortest path
for i in range(num_points):
    for j in range(num_points):
        if i != j:
            start_point = delivery_points[i][0]
            end_point = delivery_points[j][0]
            start_lat, start_lon = float(start_point[0]), float(start_point[1])
            end_lat, end_lon = float(end_point[0]), float(end_point[1])
            start_node = get_nearest_node(G, (start_lat, start_lon))
            end_node = get_nearest_node(G, (end_lat, end_lon))
            try:
                route_length = nx.shortest_path_length(G, start_node, end_node, weight='travel_time')
                distance_matrix[i][j] = route_length
            except nx.NetworkXNoPath:
                distance_matrix[i][j] = float('inf')

# Solve the TSP problem
tsp_path = solve_tsp(distance_matrix)

# Ensure the depot is the start and end point
if tsp_path[0] != 0:
    tsp_path.insert(0, 0)
if tsp_path[-1] != 0:
    tsp_path.append(0)

# Iterate over the TSP paths and calculate the shortest path
for vehicle_id, tsp_path in enumerate(tsp_paths):
    vehicle_color = vehicle_colors[vehicle_id % len(vehicle_colors)]  # Assign a color to each vehicle
    for i in range(len(tsp_path) - 1):
        start_idx = tsp_path[i]
        end_idx = tsp_path[i + 1]

        # Get the start and end points from delivery_points
        start_point = delivery_points[start_idx][0]
        end_point = delivery_points[end_idx][0]

        # Unpack the coordinates
        start_lat, start_lon = start_point
        end_lat, end_lon = end_point

        # Ensure coordinates are floats
        start_lat = float(start_lat)
        start_lon = float(start_lon)
        end_lat = float(end_lat)
        end_lon = float(end_lon)

        # Get the nearest nodes
        start_node = get_nearest_node(G, (start_lat, start_lon))
        end_node = get_nearest_node(G, (end_lat, end_lon))

        # Find the shortest path between the nodes using travel_time as the weight
        try:
            route = nx.shortest_path(G, start_node, end_node, weight='travel_time')
            # Get the route coordinates
            route_coords = [(G.nodes[node]['y'], G.nodes[node]['x']) for node in route]

            # Add the route to the map
            polyline = folium.PolyLine(route_coords, color=vehicle_color, weight=5, opacity=0.7).add_to(map_folium_final)

            # Add arrows to the path
            arrows = PolyLineTextPath(
                polyline,
                '→',  # Unicode arrow symbol
                repeat=True,
                offset=10,
                attributes={'fill': vehicle_color, 'font-weight': 'bold', 'font-size': '24'}  # Use the same color as the path
            )
            map_folium_final.add_child(arrows)

            # Add markers for the start and end points
            folium.Marker(
                location=[start_lat, start_lon],
                icon=folium.Icon(color='white', icon_color=vehicle_color, icon='truck', prefix='fa')
            ).add_to(map_folium_final)
            folium.Marker(
                location=[end_lat, end_lon],
                icon=folium.Icon(color='white', icon_color=vehicle_color, icon='truck', prefix='fa')
            ).add_to(map_folium_final)

            # Calculate route length and duration
            length = sum(ox.utils_graph.get_route_edge_attributes(G, route, 'length'))
            duration = sum(ox.utils_graph.get_route_edge_attributes(G, route, 'travel_time'))

            # Update totals
            total_delivery_distance += length
            total_delivery_duration += duration

        except nx.NetworkXNoPath:
            print(f"No path between node {start_node} and node {end_node}")

# -------------------------------
# 6. Sauvegarder la carte finale avec les routes et les points de livraison
# -------------------------------

map_folium_final.save('rouen_deliveries_map.html')

print("distance de livraison totale:", total_delivery_distance)
print("temps de livraison totale:", total_delivery_duration)


# When displaying the optimal path in terminal:
def print_route_with_packages(route):
    print("\nDelivery Route with Package IDs:")
    print("--------------------------------")
    for i, node in enumerate(route, 1):
        point_index = points.index((node[1], node[0]))  # Convert node coords to point index
        pkg_id = delivery_points[point_index][2]
        location_name = delivery_points[point_index][1]
        print(f"Stop {i}: {location_name} - Package ID: {pkg_id}")