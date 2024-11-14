import pandas as pd
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.cm as cm
import numpy as np

# Load the CSV file
df = pd.read_csv('Tableau de valeurs.csv', sep=';')

# Strip whitespace from column names
df.columns = df.columns.str.strip()

# Drop empty rows and duplicate columns
df = df.dropna(subset=['nombre camion', 'nombre adresses', 'duree d\'execution'])

# Convert columns to numeric
df['nombre camion'] = pd.to_numeric(df['nombre camion'], errors='coerce')
df['nombre adresses'] = pd.to_numeric(df['nombre adresses'], errors='coerce')
df['duree d\'execution'] = pd.to_numeric(df['duree d\'execution'], errors='coerce')

# Drop rows with NaN after conversion
df = df.dropna()

# Get unique camion numbers
camions = df['nombre camion'].unique()
colors = cm.get_cmap('tab10', len(camions))

# Create a color mapping
color_dict = {camion: colors(i) for i, camion in enumerate(camions)}

# Assign colors to each row based on camion number
df['color'] = df['nombre camion'].map(color_dict)

# Create 3D plot
fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')

scatter = ax.scatter(
    df['nombre camion'],
    df['nombre adresses'],
    df['duree d\'execution'],
    c=df['color'],
    marker='o'
)

ax.set_xlabel('Nombre Camion')
ax.set_ylabel('Nombre Adresses')
ax.set_zlabel('Durée d\'Execution (s)')

plt.title('3D Plot of Camion Data')

# Connect points with the same camion number
for camion in camions:
    camion_data = df[df['nombre camion'] == camion].sort_values('nombre adresses')
    ax.plot(
        camion_data['nombre camion'],
        camion_data['nombre adresses'],
        camion_data['duree d\'execution'],
        color=color_dict[camion],
        label=f'Camion {camion}'
    )

# Create a legend
handles = [plt.Line2D([0], [0], marker='o', color='w', label=f'{camion} camion{"" if camion == 1 else "s"}',
                      markerfacecolor=color_dict[camion], markersize=10)
           for camion in camions]
plt.legend(handles=handles, title='Nombre Camion')

plt.show()