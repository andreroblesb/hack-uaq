from google import genai
from dotenv import load_dotenv
import os
import requests
import datetime
from concurrent.futures import ThreadPoolExecutor
import time
from google.genai import types

# 

load_dotenv()


def include_climate_in_time_estimated(weather_context, city_name, origin, destination, hour):
    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

    prompt_recomendaciones = f"""
    Tarea recomendaciones:
    
    Proporciona recomendaciones para una persona que viaja en la ciudad de {city_name} a las {hour} (es muy importante para las recomendaciones tomar en cuenta la hora del día), dadas las siguientes condiciones climáticas: un pronóstico de un día con lapsos de 3 horas {weather_context["forecasted"]} | el clima actual es {weather_context["weather"]} | la temperatura percibida actual es {weather_context["feels_like"]} | la temperatura mínima es {weather_context["temp_min"]} | la temperatura máxima es {weather_context["temp_max"]} | la humedad es {weather_context["humidity"]}. Toma en cuenta la proporción de cantidad de nubes {weather_context["clouds"]}, la velocidad del viento {weather_context["wind_speed"]}, y la visibilidad en metros {weather_context["visibility"]} solo si son inusualmente altos. Proporciona una lista de recomendaciones que incluya: ropa, precauciones (como gafas de sol, paraguas, bloqueador, etc.), y cualquier otra información relevante, pero concisa. Tono amigable. Empieza diciendo |Antes de tomar tu viaje, te recomiendo...|
    
    No te alargues, no incluyas información innecesaria, y no incluyas recomendaciones de viaje. Solo incluye recomendaciones relacionadas con el clima. 
    """
    
    print("Prompt recomendaciones:", prompt_recomendaciones)
    
    prompt_minutos = f"""
    Tarea minutos:
    Dado que el usuario va desde {origin} hasta {destination}, y el clima actual es {weather_context["weather"]} | la temperatura percibida actual es {weather_context["feels_like"]} | la temperatura mínima es {weather_context["temp_min"]} | la temperatura máxima es {weather_context["temp_max"]} | la humedad es {weather_context["humidity"]}, ¿cuánto tiempo estimas que tomará el viaje? Proporciona una respuesta concisa y amigable. No incluyas recomendaciones, solo devuelve el número en minutos de tiempo estimado. 
    
    Si no eres capaz de estimar un número de minutos, devuelve el número 0.
    """
    
    def get_recomendaciones():
        return  client.models.generate_content(
            model="gemini-2.0-flash", contents=prompt_recomendaciones,
            config=types.GenerateContentConfig(
            max_output_tokens=300,
            temperature=0.2
            )
        )
        
    def get_minutos():
        return client.models.generate_content(
            model="gemini-2.0-flash", contents=prompt_minutos,
            config=types.GenerateContentConfig(
            max_output_tokens=1,
            temperature=0
            )
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        future_recomendaciones = executor.submit(get_recomendaciones)
        future_minutos = executor.submit(get_minutos)
        
        response_recomendaciones = future_recomendaciones.result()
        response_minutos = future_minutos.result()

    return {"minutos": response_minutos.text, "recomendaciones": response_recomendaciones.text}

def get_forecast(lat, lon, api_key):
    request_forecast = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={api_key}"
    response_forecast = requests.get(request_forecast)
    response_forecast.raise_for_status()
    return response_forecast.json()

def get_current_weather(lat, lon, api_key):
    request_weather = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}"
    response_weather = requests.get(request_weather)
    response_weather.raise_for_status()
    return response_weather.json()

def generate_report(city_name, state_code, country_code):
    context = {}
    
    print(city_name, state_code, country_code)

    try:
        api_key = os.getenv("api_key")
        if not api_key:
            raise ValueError("API key not found. Make sure 'api_key' is set in environment variables.")

        # Step 1: Obtener coordenadas
        request_coordinates = f"http://api.openweathermap.org/geo/1.0/direct?q={city_name},{state_code},{country_code}&limit=1&appid={api_key}"
        response_coords = requests.get(request_coordinates)
        response_coords.raise_for_status()  # lanza error si status != 200
        coordinates = response_coords.json()

        if not coordinates:
            raise ValueError(f"No se encontraron coordenadas para: {city_name}, {state_code}, {country_code}")

        lat = coordinates[0]["lat"]
        lon = coordinates[0]["lon"]

        context["lat"] = lat
        context["lon"] = lon
        print("Latitud y longitud:", lat, lon)

        # Step 2: Hacer requests en paralelo
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_forecast = executor.submit(get_forecast, lat, lon, api_key)
            future_weather = executor.submit(get_current_weather, lat, lon, api_key)
            
            forecasted_weather = future_forecast.result()
            weather_conditions = future_weather.result()

        # Procesar pronóstico
        context["forecasted"] = []
        for i in range(8):
            # tupla de timestamp, feels_like, description
            try:
                timestamp = forecasted_weather["list"][i]["dt"]
                dt = datetime.datetime.fromtimestamp(timestamp)
                print(dt)
                feels_like = forecasted_weather["list"][i]["main"]["feels_like"]
                print(feels_like, "feels_like")
                temperature = f"{(feels_like - 273.15):.1f}"  # format to exactly 1 decimal
                description = forecasted_weather["list"][i]["weather"][0]["description"]
                context["forecasted"].append((dt, float(temperature), description))
            except (IndexError, KeyError) as e:
                print(f"Error al procesar la entrada {i} del pronóstico: {e}")

        # Procesar clima actual
        try:
            context["weather"] = weather_conditions["weather"][0]["description"]
            context["feels_like"] = float(f"{(weather_conditions['main']['feels_like'] - 273.15):.1f}")
            context["temp_min"] = float(f"{(weather_conditions['main']['temp_min'] - 273.15):.1f}")
            context["temp_max"] = float(f"{(weather_conditions['main']['temp_max'] - 273.15):.1f}")
            context["humidity"] = weather_conditions["main"]["humidity"]
            context["visibility"] = weather_conditions.get("visibility", 0)
            context["wind_speed"] = weather_conditions.get("wind", {}).get("speed", 0)
            context["clouds"] = weather_conditions.get("clouds", {}).get("all", 0)
        except (KeyError, TypeError) as e:
            print(f"Error processing weather data: {e}")
            context["error"] = f"Error processing weather data: {e}"
            return context

    except requests.exceptions.RequestException as e:
        print(f"Error al hacer una solicitud HTTP: {e}")
        context["error"] = "Error al conectarse a la API"
    except KeyError as e:
        print(f"Clave faltante en la respuesta: {e}")
        context["error"] = f"Error procesando los datos: falta {e}"
    except ValueError as e:
        print(f"Valor inválido: {e}")
        context["error"] = str(e)
    except Exception as e:
        print(f"Error inesperado: {e}")
        context["error"] = "Ha ocurrido un error inesperado"
        

    return context
