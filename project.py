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

# Define the starting point (point of collection)
delivery_points = [
    (point, name, f"PKG{i:04d}") # Generate package IDs like PKG0001
    for i, (point, name) in enumerate(zip(points, names), 1)
]

# Add points to the map with package IDs in tooltips
for point, name, pkg_id in delivery_points:
    tooltip_text = f"{name} (Tracking ID: {pkg_id})"
    folium.Marker(location=point, tooltip=tooltip_text).add_to(map_folium)

# Save the map to an HTML file
map_folium.save('map.html')

# -------------------------------
# 5. Calculer et afficher le chemin le plus rapide pour la livraison
# -------------------------------

# Create a distance matrix
num_points = len(delivery_points)
distance_matrix = [[0] * num_points for _ in range(num_points)]


for i, (point1, _, _) in enumerate(delivery_points):
    lat1, lon1 = point1  # Unpack point1 into lat1 and lon1
    for j, (point2, _, _) in enumerate(delivery_points):
        if i != j:
            lat2, lon2 = point2  # Unpack point2 into lat2 and lon2
            node1 = get_nearest_node(G, (lat1, lon1))
            node2 = get_nearest_node(G, (lat2, lon2))
            try:
                # Use travel time as the weight for the shortest path calculation
                length = nx.shortest_path_length(G, node1, node2, weight='travel_time')
                distance_matrix[i][j] = length
            except nx.NetworkXNoPath:
                distance_matrix[i][j] = float('inf')
        else:
            distance_matrix[i][j] = 0  # Distance to self is zero


# Solve the TSP using OR-Tools
def create_data_model():
    data = {}
    data['distance_matrix'] = distance_matrix
    data['num_vehicles'] = 1
    data['depot'] = 0
    return data

def get_tsp_path(manager, routing, solution):
    index = routing.Start(0)
    tsp_path = []
    while not routing.IsEnd(index):
        tsp_path.append(manager.IndexToNode(index))
        index = solution.Value(routing.NextVar(index))
    tsp_path.append(manager.IndexToNode(index))  # Return to the starting point
    return tsp_path

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

# Setting first solution heuristic
search_parameters = pywrapcp.DefaultRoutingSearchParameters()
search_parameters.first_solution_strategy = (routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)

# Solve the problem
solution = routing.SolveWithParameters(search_parameters)

if solution:
    tsp_path = get_tsp_path(manager, routing, solution)
    print("Optimal TSP path:", tsp_path)

# Create a color map for the paths
colors = []
for i in range(len(tsp_path)-1):
    # Convert numpy color to hex string
    rgb = cm.rainbow(i / (len(tsp_path)-1))[:3]  # Get RGB values
    hex_color = '#{:02x}{:02x}{:02x}'.format(
        int(rgb[0]*255),
        int(rgb[1]*255),
        int(rgb[2]*255)
    )
    colors.append(hex_color)

# Initialize total distance and duration
total_delivery_distance = 0
total_delivery_duration = 0

# Iterate over the TSP path and calculate the shortest path
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
    end_node = ox.distance.nearest_nodes(G, end_lon, end_lat)
    
    try:
        # Calculate the shortest path based on travel time
        shortest_path = nx.shortest_path(G, start_node, end_node, weight='travel_time')
    except nx.NetworkXNoPath:
        print(f"No path between node {start_node} and node {end_node}")
        
        # Convert the route to a GeoDataFrame
        route_gdf = ox.routing.route_to_gdf(G, shortest_path)
        
        # Calculate total distance
        total_distance = route_gdf['length'].sum()
        
        # Calculate total duration by summing travel times from the graph
        total_duration = sum(G[u][v][0]['travel_time'] for u, v in zip(shortest_path[:-1], shortest_path[1:]))
        
        # Add the values to running totals
        total_delivery_distance += total_distance
        total_delivery_duration += total_duration
        
        # Get the coordinates of the path
        path_coords = [(G.nodes[node]['y'], G.nodes[node]['x']) for node in shortest_path]
        
        # Add the path to the Folium map with arrows
        polyline = folium.PolyLine(path_coords, color='grey', weight=5, opacity=0.7)
        polyline.add_to(map_folium)
        
        # Add arrows to the path
        arrows = PolyLineTextPath(
            polyline,
            '→',  # Unicode arrow symbol
            repeat=True,
            offset=10,
            attributes={'fill': colors[i], 'font-weight': 'bold', 'font-size': '24'}  # Use the same color as the path
        )
        map_folium.add_child(arrows)
        
        # Print the total distance and duration
        print(f"Path from {delivery_points[start_idx][2]} to {delivery_points[end_idx][2]}:")
        print(f"Total distance: {total_distance} meters")
        print(f"Total duration: {total_duration} seconds")

        # Print the total distance and duration
        print(f"Path from {delivery_points[start_idx][2]} to {delivery_points[end_idx][2]}:")
        print(f"Total distance: {total_distance/1000:.2f} km")
        print(f"Total duration: {total_duration/60:.2f} minutes")
        
        # Calculate and print average speed
        average_speed = (total_distance / 1000) / (total_duration / 3600)  # km/h
        print(f"Average speed: {average_speed:.2f} km/h")
        
        # # Print speeds for each segment
        # print("Segment speeds:")
        # for u, v in zip(shortest_path[:-1], shortest_path[1:]):
        #     edge_data = G.get_edge_data(u, v)[0]
        #     segment_speed = edge_data['length'] / edge_data['travel_time'] * 3.6  # Convert to km/h
        #     print(f"  Segment speed: {segment_speed:.2f} km/h")
    except nx.NetworkXNoPath:
        print(f"No path between {delivery_points[start_idx][2]} and {delivery_points[end_idx][2]}")
        

# -------------------------------
# 6. Sauvegarder la carte finale avec les routes et les points de livraison
# -------------------------------

# Create the map with package information
map_folium = folium.Map(location=origin, zoom_start=12)

# Add points to the map with package IDs in tooltips
for point, name, pkg_id in delivery_points:
    tooltip_text = f"{name} (Tracking ID: {pkg_id})"
    folium.Marker(location=point, tooltip=tooltip_text).add_to(map_folium)

# When displaying the optimal path in terminal:
def print_route_with_packages(route):
    print("\nDelivery Route with Package IDs:")
    print("--------------------------------")
    for i, node in enumerate(route, 1):
        point_index = points.index((node[1], node[0]))  # Convert node coords to point index
        pkg_id = delivery_points[point_index][2]
        location_name = delivery_points[point_index][1]
        print(f"Stop {i}: {location_name} - Package ID: {pkg_id}")