import os
from concurrent.futures import ThreadPoolExecutor
import time
import json

#this function is deprecated, is only used for testing and development purposes
def get_route(json_file_path=None, include_stops=True):
    """
    Read routes from a JSON file and return the first route option.
    
    Args:
        json_file_path (str): Path to the JSON file with routes data. 
                             If None, uses the default path.
        include_stops (bool): Whether to include detailed stop information
    
    Returns:
        dict: A selected route with its details
    """
    if json_file_path is None:
        # Default path to routes json file
        json_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                     'data', 'routes.json')
    
    try:
        with open(json_file_path, 'r', encoding='utf-8') as file:
            routes_data = json.load(file)
        
        if not routes_data or 'results' not in routes_data:
            print("No routes found in JSON file")
            return None
            
        # For now, just return the first route option
        # Look for routes with itinerary data
        for result in routes_data['results']:
            if 'result' in result and 'itinerary' in result['result']:
                route = result['result']['itinerary']
                
                # Extract useful info
                route_summary = {
                    'guid': route.get('guid'),
                    'sectionName': route.get('sectionName'),
                    'legs': []
                }
                
                # Process each leg of the route
                for leg in route.get('legs', []):
                    leg_info = {}
                    
                    # Handle different leg types
                    if 'bicycleLeg' in leg:
                        leg_info['type'] = 'bicycle'
                        if 'shape' in leg['bicycleLeg']:
                            leg_info['distance'] = leg['bicycleLeg']['shape'].get('distanceInMeters')
                        if 'time' in leg['bicycleLeg']:
                            start_time = leg['bicycleLeg']['time'].get('startTimeUtc')
                            end_time = leg['bicycleLeg']['time'].get('endTimeUtc')
                            if start_time and end_time:
                                leg_info['duration_ms'] = end_time - start_time
                        
                        # Extract cycling instructions if available
                        if include_stops and 'cyclingInstructions' in leg['bicycleLeg']:
                            leg_info['stops'] = []
                            for instruction in leg['bicycleLeg']['cyclingInstructions']:
                                leg_info['stops'].append({
                                    'street_name': instruction.get('streetName'),
                                    'length_meters': instruction.get('lengthInMeters'),
                                    'travel_time_ms': instruction.get('travelTimeInMs'),
                                    'location': instruction.get('startLocation')
                                })
                    
                    elif 'walkLeg' in leg:
                        leg_info['type'] = 'walk'
                        if 'shape' in leg['walkLeg']:
                            leg_info['distance'] = leg['walkLeg']['shape'].get('distanceInMeters')
                        if 'time' in leg['walkLeg']:
                            start_time = leg['walkLeg']['time'].get('startTimeUtc')
                            end_time = leg['walkLeg']['time'].get('endTimeUtc')
                            if start_time and end_time:
                                leg_info['duration_ms'] = end_time - start_time
                                
                        # Extract walking instructions
                        if include_stops and 'walkingInstructoins' in leg['walkLeg']:
                            leg_info['stops'] = []
                            for instruction in leg['walkLeg']['walkingInstructoins']:
                                leg_info['stops'].append({
                                    'street_name': instruction.get('streetName'),
                                    'length_meters': instruction.get('lengthInMeters'),
                                    'travel_time_ms': instruction.get('travelTimeInMs'),
                                    'location': instruction.get('startLocation')
                                })
                    
                    elif 'lineWithAlternativesLeg' in leg:
                        leg_info['type'] = 'transit'
                        if 'alternativeLines' in leg['lineWithAlternativesLeg'] and leg['lineWithAlternativesLeg']['alternativeLines']:
                            line = leg['lineWithAlternativesLeg']['alternativeLines'][0]
                            if 'shape' in line:
                                leg_info['distance'] = line['shape'].get('distanceInMeters')
                            if 'time' in line:
                                start_time = line['time'].get('startTimeUtc')
                                end_time = line['time'].get('endTimeUtc')
                                if start_time and end_time:
                                    leg_info['duration_ms'] = end_time - start_time
                            leg_info['lineId'] = line.get('lineId')
                            
                            # Extract transit stops
                            if include_stops and 'stopSequenceIds' in line:
                                leg_info['stops'] = []
                                stop_ids = line.get('stopSequenceIds', [])
                                
                                # Look for stop metadata in supplementalData
                                stop_metadata = {}
                                for result in routes_data.get('results', []):
                                    if 'supplementalData' in result and 'mVStopSyncedMetaDataList' in result['supplementalData']:
                                        for stop in result['supplementalData']['mVStopSyncedMetaDataList']:
                                            stop_id = stop.get('stopId')
                                            if stop_id:
                                                stop_metadata[stop_id] = {
                                                    'name': stop.get('stopName'),
                                                    'location': stop.get('stopLocation'),
                                                    'code': stop.get('stopCode')
                                                }
                                
                                # Add stop information
                                for stop_id in stop_ids:
                                    stop_info = {'id': stop_id}
                                    if stop_id in stop_metadata:
                                        stop_info.update(stop_metadata[stop_id])
                                    leg_info['stops'].append(stop_info)
                    
                    route_summary['legs'].append(leg_info)
                
                # Calculate total distance and duration
                total_distance = sum(leg.get('distance', 0) for leg in route_summary['legs'])
                total_duration = sum(leg.get('duration_ms', 0) for leg in route_summary['legs'])
                
                route_summary['total_distance_meters'] = total_distance
                route_summary['total_duration_seconds'] = total_duration / 1000 if total_duration else 0
                
                print(f"Found route: {route_summary['sectionName']} - {route_summary['total_duration_seconds']:.1f} seconds")
                return route_summary
                
        print("No valid routes with itinerary data found")
        return None
    
    except FileNotFoundError:
        print(f"Route file not found: {json_file_path}")
        return None
    except json.JSONDecodeError:
        print(f"Invalid JSON in routes file: {json_file_path}")
        return None
    except Exception as e:
        print(f"Error reading routes: {str(e)}")
        return None
