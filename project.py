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

# -------------------------------
# 1. Téléchargement du graphe routier de Rouen
# -------------------------------

# Load points from the Excel file
def load_points_from_excel(file_path):
    df = pd.read_excel(file_path)
    points = df[['lat', 'long']].values.tolist()
    names = df['Package ID'].tolist()  # Add this line
    return points, names  # Change this line

# Example file path
file_path = 'deliveries_data.xlsx'

# Load points
points, names = load_points_from_excel(file_path)

# Ensure points is a list of tuples (latitude, longitude)
if not points or not all(isinstance(point, (list, tuple)) and len(point) == 2 for point in points):
    raise ValueError("The points list is not correctly formatted.")

# Use the first point as the origin for the TSP
origin = points[0]

# Function to find cities within a 10-kilometer radius using Overpass API
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

# Find nearby cities based on the origin
places = find_nearby_cities(origin)

# Ensure places is a list of strings
if isinstance(places, list) and all(isinstance(place, str) for place in places):
    G = ox.graph_from_place(places, network_type='drive')
else:
    raise ValueError("The places list is not correctly formatted.")


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


# # Visualize the graph (optional)
# ox.plot_graph(G)

# Create the map centered on the origin
map_folium = folium.Map(location=origin, zoom_start=12)

# Add points to the map with names visible on hover
for point, name in zip(points, names):
    folium.Marker(location=point, tooltip=name).add_to(map_folium)

# Save the map to an HTML file
map_folium.save('map.html')

# -------------------------------
# 5. Calculer et afficher le chemin le plus rapide pour la livraison
# -------------------------------

# Define the starting point (point of collection)
delivery_points = []
for point, name in zip(points, names):
    folium.Marker(location=point, tooltip=name).add_to(map_folium)
    delivery_points.append((point[0], point[1], f"Package {name}"))

# Create a distance matrix
num_points = len(delivery_points)
distance_matrix = [[0] * num_points for _ in range(num_points)]

for i, (lat1, lon1, _) in enumerate(delivery_points):
    for j, (lat2, lon2, _) in enumerate(delivery_points):
        if i != j:
            node1 = ox.distance.nearest_nodes(G, lon1, lat1)
            node2 = ox.distance.nearest_nodes(G, lon2, lat2)
            try:
                # Use travel time as the weight for the shortest path calculation
                length = nx.shortest_path_length(G, node1, node2, weight='travel_time')
                distance_matrix[i][j] = length
            except nx.NetworkXNoPath:
                distance_matrix[i][j] = float('inf')

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
    start_lat, start_lon, _ = delivery_points[start_idx]
    end_lat, end_lon, _ = delivery_points[end_idx]
    start_node = ox.distance.nearest_nodes(G, start_lon, start_lat)
    end_node = ox.distance.nearest_nodes(G, end_lon, end_lat)
    
    try:
        # Calculate the shortest path based on travel time
        shortest_path = nx.shortest_path(G, start_node, end_node, weight='travel_time')
        
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
        
        # Print speeds for each segment
        print("Segment speeds:")
        for u, v in zip(shortest_path[:-1], shortest_path[1:]):
            edge_data = G.get_edge_data(u, v)[0]
            segment_speed = edge_data['length'] / edge_data['travel_time'] * 3.6  # Convert to km/h
            print(f"  Segment speed: {segment_speed:.2f} km/h")
    except nx.NetworkXNoPath:
        print(f"No path between {delivery_points[start_idx][2]} and {delivery_points[end_idx][2]}")
        

# -------------------------------
# 6. Sauvegarder la carte finale avec les routes et les points de livraison
# -------------------------------
map_folium.save('rouen_deliveries_map.html')

# Print total delivery distance and duration
print(f"Total delivery distance: {total_delivery_distance} meters")
print(f"Total delivery duration: {total_delivery_duration} seconds")

# Affichage final
print("Carte de Rouen avec points de livraison et réseau routier générée : 'rouen_deliveries_map.html'")