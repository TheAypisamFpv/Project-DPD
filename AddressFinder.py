import openpyxl
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from time import sleep
import random
import math

def FindAddresses(centerPoint:tuple, radius:float, numAddresses:int):
    """
    Find addresses within a given radius of a center point.

    param centerPoint: A tuple containing the latitude and longitude of the center point.
    param radius: The radius in kilometers within which to find addresses.
    param numAddresses: The number of addresses to find.
    """
    print("Finding addresses...")
    geolocator = Nominatim(user_agent="address_finder")
    addresses = []
    lat, lon = centerPoint

    for i in range(numAddresses):
        try:
            location = geolocator.reverse((lat, lon), exactly_one=True, timeout=10)
            if location:
                address_parts = location.address.split(',')
                if len(address_parts) > 1:
                    street_address = address_parts[0] + ', ' + address_parts[1]
                else:
                    street_address = address_parts[0]
                google_maps_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
                addresses.append((i + 1, street_address, lat, lon, google_maps_url))
                print(f"Found {len(addresses)}/{numAddresses} addresses...", end="\r")
        except Exception as e:
            print(f"Error retrieving address for point ({lat}, {lon}): {e}")
            sleep(1)  # Wait for a second before retrying

        # Adjust the lat/lon slightly to get a new point within the radius
        angle = random.uniform(0, 360)
        distance = random.uniform(0, radius)
        delta_lat = distance * 0.009 / 1.609 * math.cos(math.radians(angle))
        delta_lon = distance * 0.009 / 1.609 * math.sin(math.radians(angle))
        new_lat = lat + delta_lat
        new_lon = lon + delta_lon

        if geodesic(centerPoint, (new_lat, new_lon)).km <= radius:
            lat, lon = new_lat, new_lon

    print()
    return addresses

def WriteToExcel(addresses:list, filename:str):
    """
    Write the addresses to an Excel file.

    param addresses: A list of tuples containing address information.
    param filename: The name of the Excel file to write to with .xlsx.
    """
    print("\nWriting addresses to Excel file...")
    try:
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.append(["Package ID", "Address", "lat", "long", "Google Maps URL"])

        for address in addresses:
            sheet.append(address)

        workbook.save(filename)
        print("Addresses saved to Excel file.")
    except Exception as e:
        input(f"An error occurred: {e}\nPress Enter to retry...")
        WriteToExcel(addresses, filename)

def main(centerPoint:tuple, radius:float, numAddresses:int, filename="addresses_found.xlsx"):
    """
    Main function to find addresses and write them to an Excel file.

    param centerPoint: A tuple containing the latitude and longitude of the center point.
    param radius: The radius in kilometers within which to find addresses.
    param numAddresses: The number of addresses to find.
    param filename: The name of the Excel file to write to with .xlsx.
    """
    addresses = FindAddresses(centerPoint, radius, numAddresses)
    WriteToExcel(addresses, filename)

if __name__ == "__main__":
    centerPoint = (49.443512, 1.098445)  # Provided GPS coordinates
    radius = float(input("Enter the radius in km: "))
    numAddresses = int(input("Enter the number of addresses to find: "))
    main(centerPoint, radius, numAddresses)