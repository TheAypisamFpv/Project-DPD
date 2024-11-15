import pandas as pd
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.cm as cm
import numpy as np
import matplotlib.gridspec as gridspec

# Load the CSV file
df = pd.read_csv('Valuetab.csv', sep=';')

# Strip whitespace from column names
df.columns = df.columns.str.strip()

# Drop empty rows and duplicate columns
df = df.dropna(subset=['nombre camion', 'nombre adresses', 'duree d\'execution'])

# Convert columns to numeric
df['number of trucks'] = pd.to_numeric(df['nombre camion'], errors='coerce')
df['number of addresses'] = pd.to_numeric(df['nombre adresses'], errors='coerce')
df['execution duration'] = pd.to_numeric(df['duree d\'execution'], errors='coerce')

# Drop rows with NaN after conversion
df = df.dropna()

# Get unique truck numbers
trucks = df['number of trucks'].unique()
colors = cm.get_cmap('tab10', len(trucks))

# Create a color mapping
color_dict = {truck: colors(i) for i, truck in enumerate(trucks)}

# Assign colors to each row based on truck number
df['color'] = df['number of trucks'].map(color_dict)

# Create a figure with GridSpec
fig = plt.figure(figsize=(14, 8))
gs = gridspec.GridSpec(2, 2, height_ratios=[4, 1])

# 3D Plot
ax1 = fig.add_subplot(gs[0, 0], projection='3d')
scatter = ax1.scatter(
    df['number of trucks'],
    df['number of addresses'],
    df['execution duration'],
    c=df['color'],
    marker='o'
)

ax1.set_xlabel('Number of Trucks')
ax1.set_ylabel('Number of Addresses')
ax1.set_zlabel('Execution Duration (s)')
ax1.set_title('3D Plot of Truck Data')

# Connect points with the same truck number
for truck in trucks:
    truck_data = df[df['number of trucks'] == truck].sort_values('number of addresses')
    ax1.plot(
        truck_data['number of trucks'],
        truck_data['number of addresses'],
        truck_data['execution duration'],
        color=color_dict[truck],
        label=f'Truck {truck}'
    )

# Create a legend for the 3D plot
handles = [plt.Line2D([0], [0], marker='o', color='w', label=f'{truck} truck{"s" if truck != 1 else ""}',
                      markerfacecolor=color_dict[truck], markersize=10)
           for truck in trucks]
ax1.legend(handles=handles, title='Number of Trucks', loc='upper left', bbox_to_anchor=(1, 1))

# Combined Bar Plot
labels = ['Without TSP', 'With TSP']
km = [470, 128]
time = [412, 161]

ax2 = fig.add_subplot(gs[0, 1])

x = np.arange(len(labels))  # label locations
width = 0.35  # bar width

bar1 = ax2.bar(x - width/2, km, width, label='Kilometers', color='blue')
bar2 = ax2.bar(x + width/2, time, width, label='Travel Time (min)', color='red')

ax2.set_ylabel('Values')
ax2.set_title('Comparison of Routes (with 70 packages)')
ax2.set_xticks(x)
ax2.set_xticklabels(labels)
ax2.legend()

# Add labels on top of bars
for bar in bar1 + bar2:
    height = bar.get_height()
    ax2.annotate('{}'.format(height),
                xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 3),  # 3 points vertical offset
                textcoords="offset points",
                ha='center', va='bottom')

plt.tight_layout()
plt.show()