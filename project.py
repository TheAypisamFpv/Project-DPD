import osmnx as ox
import networkx as nx
import folium
import pandas as pd
from geopy.distance import geodesic
import requests
from folium.plugins import PolyLineTextPath
from ortools.constraint_solver import pywrapcp, routing_enums_pb2

# -------------------------------
# 1. Téléchargement du graphe routier de Rouen
# -------------------------------

# Define the center coordinates of your map (example: Rouen, France)
center_coords = (49.4431, 1.0993)

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

# Update the places list
places = find_nearby_cities(center_coords)

# Ensure places is a list of strings
if isinstance(places, list) and all(isinstance(place, str) for place in places):
    G = ox.graph_from_place(places, network_type='drive')
else:
    raise ValueError("The places list is not correctly formatted.")

# Récupérer les données du réseau routier (drivable uniquement)
G = ox.graph_from_place(places, network_type='drive')

# Add travel time to each edge in the graph
for u, v, k, data in G.edges(data=True, keys=True):
    if 'length' in data and 'maxspeed' in data:
        # Convert maxspeed to km/h if it's a string
        if isinstance(data['maxspeed'], list):
            maxspeed = float(data['maxspeed'][0])
        else:
            maxspeed = float(data['maxspeed'])
        # Calculate travel time in seconds
        data['travel_time'] = data['length'] / (maxspeed * 1000 / 3600)

# Visualiser une première fois le graphe pour vérifier sa création (optionnel)
ox.plot_graph(G)

# -------------------------------
# 2. Création d'une carte Folium centrée sur Rouen
# -------------------------------
center_lat, center_long = 49.4431, 1.0993  # Coordonnées approximatives de Rouen
map_folium = folium.Map(location=[center_lat, center_long], zoom_start=12)

# -------------------------------
# 4. Ajout des points de livraison à partir d'un fichier Excel
# -------------------------------
# Exemple de structure du fichier Excel : 
# | Package ID | lat     | long   |
# |------------|---------|--------|
# | 1          | 49.44   | 1.10   |
# | 2          | 49.45   | 1.11   |

# Charger les points de livraison depuis un fichier Excel
df = pd.read_excel('deliveries_data.xlsx')  # Assure-toi que le fichier se trouve dans le bon chemin

# Ajouter chaque point de livraison comme marqueur sur la carte
for index, row in df.iterrows():
    folium.Marker([row['lat'], row['long']], popup=f"Package {row['Package ID']}").add_to(map_folium)

# -------------------------------
# 5. Calculer et afficher le chemin le plus rapide pour la livraison
# -------------------------------

# Define the starting point (point of collection)
start_point = (49.4431, 1.0993)  # Example coordinates for the starting point

# Add the starting point to the delivery points
delivery_points = [(start_point[0], start_point[1], 'Start')]
for index, row in df.iterrows():
    delivery_points.append((row['lat'], row['long'], f"Package {row['Package ID']}"))

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
routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

search_parameters = pywrapcp.DefaultRoutingSearchParameters()
search_parameters.first_solution_strategy = (routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)

solution = routing.SolveWithParameters(search_parameters)

if solution:
    tsp_path = get_tsp_path(manager, routing, solution)
    print("Optimal TSP path:", tsp_path)

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
        
        # Calculate the total distance and duration
        total_distance = route_gdf['length'].sum()
        total_duration = route_gdf['travel_time'].sum()
        
        # Accumulate the total distance and duration
        total_delivery_distance += total_distance
        total_delivery_duration += total_duration
        
        # Get the coordinates of the path
        path_coords = [(G.nodes[node]['y'], G.nodes[node]['x']) for node in shortest_path]
        
        # Add the path to the Folium map with arrows
        polyline = folium.PolyLine(path_coords, color='red', weight=5, opacity=0.7)
        polyline.add_to(map_folium)
        
        # Add arrows to the path
        arrows = PolyLineTextPath(
            polyline,
            '→',  # Unicode arrow symbol
            repeat=True,
            offset=10,
            attributes={'fill': 'red', 'font-weight': 'bold', 'font-size': '24'}
        )
        map_folium.add_child(arrows)
        
        # Print the total distance and duration
        print(f"Path from {delivery_points[start_idx][2]} to {delivery_points[end_idx][2]}:")
        print(f"Total distance: {total_distance} meters")
        print(f"Total duration: {total_duration} seconds")
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