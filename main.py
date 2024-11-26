import requests
from datetime import datetime
from math import radians, sin, cos, sqrt, atan2
import csv
from typing import List, Dict, Tuple

class EasyJetCollector:
    def __init__(self, api_key: str, client_id: str):
        self.base_url = "https://api.easyjet.com/v1"
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'X-Client-ID': client_id,
            'Accept': 'application/json'
        }
        
        # Airport coordinates database
        self.airport_coords = self._load_airport_coordinates()

    def _load_airport_coordinates(self) -> Dict[str, Tuple[float, float]]:
        """
        Load airport coordinates from local database
        Returns dict with airport codes as keys and (lat, lon) tuples as values
        """
        # This would typically load from a database, but for example we'll include some common airports
        return {
            'LGW': (51.1537, -0.1821),  # London Gatwick
            'BCN': (41.2974, 2.0833),   # Barcelona
            'CDG': (49.0097, 2.5479),   # Paris Charles de Gaulle
            # Add more airports as needed
        }

    def calculate_distance(self, origin: str, destination: str) -> float:
        """
        Calculate distance between two airports using Haversine formula
        Returns distance in kilometers
        """
        if origin not in self.airport_coords or destination not in self.airport_coords:
            return 0.0  # Return 0 if we don't have coordinates
            
        lat1, lon1 = self.airport_coords[origin]
        lat2, lon2 = self.airport_coords[destination]
        
        R = 6371  # Earth's radius in kilometers

        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        distance = R * c

        return round(distance, 2)

    def get_all_flights(self, origin_airport: str, date: str) -> List[List]:
        """
        Get all flights from specified airport on given date
        Returns list of [distance, airport, price]
        
        Args:
            origin_airport: IATA code (e.g., 'LGW')
            date: Date in YYYY-MM-DD format
        """
        try:
            # First get all possible routes from this airport
            routes_endpoint = f"{self.base_url}/routes"
            params = {'departure': origin_airport}
            
            response = requests.get(routes_endpoint, headers=self.headers, params=params)
            response.raise_for_status()
            
            all_destinations = response.json().get('routes', [])
            flight_data = []

            # For each destination, get flight prices for the specified date
            for route in all_destinations:
                destination = route['destination']
                
                # Get specific flight data
                flights_endpoint = f"{self.base_url}/flights"
                flight_params = {
                    'origin': origin_airport,
                    'destination': destination,
                    'outboundDate': date,
                    'adult': 1
                }
                
                flight_response = requests.get(
                    flights_endpoint, 
                    headers=self.headers, 
                    params=flight_params
                )
                flight_response.raise_for_status()
                
                flights = flight_response.json().get('flights', [])
                
                # Get the lowest price for this route on this date
                if flights:
                    lowest_price = min(
                        flight.get('pricing', {}).get('lowestFare', float('inf')) 
                        for flight in flights
                    )
                    
                    # Calculate distance
                    distance = self.calculate_distance(origin_airport, destination)
                    
                    # Add to our results
                    flight_data.append([
                        distance,
                        destination,
                        lowest_price
                    ])
            
            return flight_data

        except requests.exceptions.RequestException as e:
            print(f"Error fetching flight data: {e}")
            return []

    def save_to_csv(self, data: List[List], filename: str):
        """Save flight data to CSV file"""
        with open(filename, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['Distance (km)', 'Destination', 'Lowest Price'])
            writer.writerows(data)

def main():
    API_KEY = "your_api_key_here"
    CLIENT_ID = "your_client_id_here"
    
    collector = EasyJetCollector(API_KEY, CLIENT_ID)
    
    # Get all flights from London Gatwick for a specific date
    flights = collector.get_all_flights(
        origin_airport='LGW',
        date='2024-12-01'
    )
    
    # Sort by distance
    flights.sort(key=lambda x: x[0])
    
    # Save to CSV
    collector.save_to_csv(flights, 'easyjet_flights.csv')
    
    # Print results
    print("Flights found:")
    print("Distance (km) | Destination | Price")
    print("-" * 40)
    for distance, destination, price in flights:
        print(f"{distance:11.2f} | {destination:11} | {price:5.2f}")

if __name__ == "__main__":
    main()