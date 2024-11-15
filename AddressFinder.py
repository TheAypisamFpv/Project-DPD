import openpyxl
from geopy.geocoders import Nominatim
from geopy.distance import distance
from time import sleep
import random
import math

def FindAddresses(centerPoint: tuple, radius: float, numAddresses: int):
    """
    Find addresses within a given radius of a center point.

    param centerPoint: A tuple containing the latitude and longitude of the center point.
    param radius: The radius in kilometers within which to find addresses.
    param numAddresses: The number of addresses to find.
    """
    print("Finding addresses...")
    geolocator = Nominatim(user_agent="address_finder")
    addresses = []
    attempts = 0
    max_attempts = numAddresses * 10  # To prevent infinite loops

    while len(addresses) < numAddresses and attempts < max_attempts:
        attempts += 1
        try:
            # Generate a random distance and bearing
            bearing = random.uniform(0, 360)
            # Ensure uniform distribution within the circle
            rand_distance = radius * math.sqrt(random.uniform(0, 1))
            destination = distance(kilometers=rand_distance).destination(centerPoint, bearing)
            new_lat, new_lon = destination.latitude, destination.longitude

            # Reverse geocode to find the nearest address
            location = geolocator.reverse((new_lat, new_lon), exactly_one=True, timeout=10)
            if location and location.address:
                address_parts = location.address.split(',')
                street_address = ', '.join(address_parts[:2]) if len(address_parts) > 1 else address_parts[0]

                # Get the accurate GPS coordinates of the address
                address_lat = location.latitude
                address_lon = location.longitude

                # Check for duplicate addresses
                if street_address not in [a[1] for a in addresses]:
                    google_maps_url = f"https://www.google.com/maps/search/?api=1&query={address_lat},{address_lon}"
                    addresses.append((len(addresses) + 1, street_address, address_lat, address_lon, google_maps_url))
                    print(f"Found {len(addresses)}/{numAddresses} addresses...", end="\r")
        except Exception as e:
            print(f"\nError retrieving address for generated point ({new_lat}, {new_lon}): {e}")
            sleep(1)  # Wait for a second before retrying

    if len(addresses) < numAddresses:
        print(f"\nOnly found {len(addresses)} addresses out of the requested {numAddresses}.")

    print()
    return addresses

def WriteToExcel(addresses: list, filename: str):
    """
    Write the addresses to an Excel file.

    param addresses: A list of tuples containing address information.
    param filename: The name of the Excel file to write.
    """
    print("\nWriting addresses to Excel file...")
    try:
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.append(["Package ID", "Address", "lat", "long", "Google Maps URL"])

        for address in addresses:
            sheet.append(address)

        workbook.save(filename)
        print(f"Addresses saved to {filename}")
    except Exception as e:
        print(f"An error occurred while writing to Excel: {e}")
        input("Press Enter to retry...")
        WriteToExcel(addresses, filename)

def main(centerPoint: tuple, radius: float, numAddresses: int, filename: str = "addresses_found.xlsx"):
    addresses = FindAddresses(centerPoint, radius, numAddresses)
    if addresses:
        WriteToExcel(addresses, filename)
    else:
        print("No addresses were found.")

if __name__ == "__main__":
    centerPoint = (49.443512, 1.098445)  # Provided GPS coordinates
    try:
        radius = float(input("Enter the radius in km: "))
        numAddresses = int(input("Enter the number of addresses to find: "))
        main(centerPoint, radius, numAddresses)
    except ValueError:
        print("Please enter valid numerical values for radius and number of addresses.")