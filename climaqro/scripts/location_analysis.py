import json
import os
from collections import Counter, defaultdict
from datetime import datetime
import math
from typing import List, Tuple, Dict, Any

# calculate probable work and home location to improve interaction
# P.D para un futuro que filtre los mas comunes que sean redundantes
def load_location_history(file_path: str) -> List[Dict[str, Any]]:
    """Load location history from a JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('locations', [])
    except Exception as e:
        print(f"Error loading location history: {e}")
        return []

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the Haversine distance between two points in kilometers."""
    # Convert latitude and longitude from E7 format if needed
    if abs(lat1) > 180:
        lat1 = lat1 / 1e7
    if abs(lon1) > 180:
        lon1 = lon1 / 1e7
    if abs(lat2) > 180:
        lat2 = lat2 / 1e7
    if abs(lon2) > 180:
        lon2 = lon2 / 1e7
        
    # Earth radius in kilometers
    radius = 6371.0
    
    # Convert to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # Haversine formula
    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    distance = radius * c
    
    return distance

def cluster_locations(locations: List[Dict[str, Any]], threshold_km: float = 0.1) -> List[Dict[str, Any]]:
    """Group nearby locations into clusters to identify common places."""
    clusters = []
    
    for location in locations:
        lat = location.get('latitudeE7')
        lon = location.get('longitudeE7')
        
        # Skip if location data is missing
        if lat is None or lon is None:
            continue
            
        # Check if this location belongs to an existing cluster
        found_cluster = False
        for cluster in clusters:
            cluster_lat = cluster['center_lat']
            cluster_lon = cluster['center_lon']
            
            distance = calculate_distance(lat, lon, cluster_lat, cluster_lon)
            
            if distance <= threshold_km:
                # Add to existing cluster
                cluster['locations'].append(location)
                # Update center (simple average)
                cluster['center_lat'] = (cluster['center_lat'] * (len(cluster['locations']) - 1) + lat) / len(cluster['locations'])
                cluster['center_lon'] = (cluster['center_lon'] * (len(cluster['locations']) - 1) + lon) / len(cluster['locations'])
                found_cluster = True
                break
        
        if not found_cluster:
            # Create new cluster
            clusters.append({
                'center_lat': lat,
                'center_lon': lon,
                'locations': [location]
            })
    
    return clusters

def identify_places(clusters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Identify significant places from location clusters."""
    # Filter clusters by size (more points = more significant place)
    significant_places = [c for c in clusters if len(c['locations']) >= 2]
    
    # Sort places by number of visits
    significant_places.sort(key=lambda x: len(x['locations']), reverse=True)
    
    # Add cluster ID and extract most common activity
    for i, place in enumerate(significant_places):
        place['id'] = i
        
        # Get most common activity
        activities = []
        for loc in place['locations']:
            if 'activity' in loc:
                for activity_group in loc['activity']:
                    if 'activities' in activity_group:
                        for activity in activity_group['activities']:
                            activities.append(activity['type'])
        
        if activities:
            place['common_activity'] = Counter(activities).most_common(1)[0][0]
        else:
            place['common_activity'] = 'UNKNOWN'
            
    return significant_places

def find_common_routes(locations: List[Dict[str, Any]], places: List[Dict[str, Any]]) -> List[Tuple[int, int, int]]:
    """Find common routes between places."""
    # Sort locations by timestamp
    sorted_locations = sorted(locations, key=lambda x: int(x.get('timestampMs', 0)))
    
    # Assign each location to a place
    location_places = []
    for loc in sorted_locations:
        lat = loc.get('latitudeE7')
        lon = loc.get('longitudeE7')
        
        closest_place = None
        min_distance = float('inf')
        
        for place in places:
            distance = calculate_distance(lat, lon, place['center_lat'], place['center_lon'])
            if distance < min_distance:
                min_distance = distance
                closest_place = place
                
        # Only assign if within 0.5km
        if min_distance <= 0.5:
            location_places.append((loc, closest_place['id']))
    
    # Extract routes (pairs of consecutive places)
    routes = []
    for i in range(len(location_places) - 1):
        current_loc, current_place = location_places[i]
        next_loc, next_place = location_places[i + 1]
        
        # Only count if places are different
        if current_place != next_place:
            # Calculate time difference
            time_diff = (int(next_loc.get('timestampMs', 0)) - int(current_loc.get('timestampMs', 0))) / 1000 / 60  # in minutes
            
            # Only count if time difference is reasonable (< 2 hours)
            if time_diff < 120:
                routes.append((current_place, next_place))
    
    # Count route frequencies
    route_counts = Counter(routes)
    
    # Get the most common routes
    return route_counts.most_common()

def get_most_common_routes(file_path=None):
    """Main function to analyze location history and find common routes."""
    if file_path is None:
        file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                'data', 'user_location_history.json')
    
    # Load location history
    locations = load_location_history(file_path)
    if not locations:
        return None
        
    # Cluster locations
    clusters = cluster_locations(locations)
    
    # Identify significant places
    places = identify_places(clusters)
    
    # Find common routes
    common_routes = find_common_routes(locations, places)
    
    # Prepare results
    results = []
    for (origin, destination), count in common_routes[:10]:  # Top 10 routes
        origin_place = next(p for p in places if p['id'] == origin)
        destination_place = next(p for p in places if p['id'] == destination)
        
        results.append({
            'origin': {
                'lat': origin_place['center_lat'],
                'lon': origin_place['center_lon'],
                'activity': origin_place['common_activity'],
                'visit_count': len(origin_place['locations'])
            },
            'destination': {
                'lat': destination_place['center_lat'],
                'lon': destination_place['center_lon'],
                'activity': destination_place['common_activity'],
                'visit_count': len(destination_place['locations'])
            },
            'frequency': count
        })
    
    return results

def get_home_work_locations(file_path=None):
    """
    Analyze location history and determine the most likely home and work locations.
    
    Args:
        file_path: Path to the location history JSON file
        
    Returns:
        dict: Dictionary with 'home' and 'work' coordinates
    """
    results = {
        'home': {'lat': None, 'lon': None},
        'work': {'lat': None, 'lon': None}
    }
    
    # Get common routes first
    common_routes = get_most_common_routes(file_path)
    
    # If we have common routes, use them to determine home and work
    if common_routes and len(common_routes) > 0:
        # The most common route is likely between home and work
        most_common_route = common_routes[0]
        
        origin_activity = most_common_route['origin']['activity'].upper()
        dest_activity = most_common_route['destination']['activity'].upper()
        
        # Determine which is home and which is work based on activity
        if origin_activity in ['STILL', 'HOME', 'SLEEPING', 'UNKNOWN'] and \
           dest_activity in ['STILL', 'IN_VEHICLE', 'WALKING', 'WORKING']:
            # Origin is likely home, destination is likely work
            results['home']['lat'] = most_common_route['origin']['lat']
            results['home']['lon'] = most_common_route['origin']['lon']
            results['work']['lat'] = most_common_route['destination']['lat']
            results['work']['lon'] = most_common_route['destination']['lon']
        elif dest_activity in ['STILL', 'HOME', 'SLEEPING', 'UNKNOWN'] and \
             origin_activity in ['STILL', 'IN_VEHICLE', 'WALKING', 'WORKING']:
            # Destination is likely home, origin is likely work
            results['home']['lat'] = most_common_route['destination']['lat']
            results['home']['lon'] = most_common_route['destination']['lon']
            results['work']['lat'] = most_common_route['origin']['lat']
            results['work']['lon'] = most_common_route['origin']['lon']
        else:
            # If we can't determine based on activity, use frequency and time patterns
            # Assuming the first place with highest visit count is home
            # and the second place with high visit count is work
            if len(common_routes) >= 2:
                # The origin of the most frequent route is likely home
                results['home']['lat'] = most_common_route['origin']['lat']
                results['home']['lon'] = most_common_route['origin']['lon']
                
                # The destination of the second most frequent route is likely work
                second_route = common_routes[1]
                results['work']['lat'] = second_route['destination']['lat']
                results['work']['lon'] = second_route['destination']['lon']
            else:
                # We only have one route, so use origin as home and destination as work
                results['home']['lat'] = most_common_route['origin']['lat']
                results['home']['lon'] = most_common_route['origin']['lon']
                results['work']['lat'] = most_common_route['destination']['lat']
                results['work']['lon'] = most_common_route['destination']['lon']
        
        print(f"Found home at: {results['home']['lat']}, {results['home']['lon']}")
        print(f"Found work at: {results['work']['lat']}, {results['work']['lon']}")
    
    return results

if __name__ == "__main__":
    # Default path to the location history file
    history_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                              'data', 'user_location_history.json')
    
    # Test the function
    #
    #
    #
    home_work = get_home_work_locations(history_file)
    print("\n=== Home and Work Locations ===")
    print(f"Home: {home_work['home']}")
    print(f"Work: {home_work['work']}")
    
    # Also show the most common routes
    results = get_most_common_routes(history_file)
    
    if results:
        print("\n=== Most Common Routes ===")
        for i, route in enumerate(results):
            print(f"\n{i+1}. Route taken {route['frequency']} times:")
            print(f"   Origin: ({route['origin']['lat']}, {route['origin']['lon']}) - Activity: {route['origin']['activity']}")
            print(f"   Destination: ({route['destination']['lat']}, {route['destination']['lon']}) - Activity: {route['destination']['activity']}")
    else:
        print("No location data found or processing failed.")
