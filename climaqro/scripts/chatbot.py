from google import genai
from dotenv import load_dotenv
import os
import requests
import datetime
from concurrent.futures import ThreadPoolExecutor
import time
from google.genai import types

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

def handle_interaction(user_input, origin, destination, history, bus_stations):
    system_instruction = """
    Eres un asistente virtual de la app QroBus. Vas a interactuar en español, y tienes que estar preparado para interpretar español mexicano coloquial. 
    
    Cuando un dato está faltante, se expresa con "Nan".
    """

    # Agrega el turno actual al historial
    history.append({"role": "user", "parts": [user_input]})

    # Aquí parseas el texto para ver si hay origen/destino
    if origin == "Nan" or destination == "Nan" or origin is None or destination is None:
        print("hasta aqui llega")
        extracted_text = extract_location_from_text(user_input, bus_stations)

        # Extrae origen y destino del texto
        try:
            if origin == "Nan" or origin is None:
                origin = extracted_text.split("|origen||")[1].split("|")[0].strip()
            if destination == "Nan" or destination is None:
                destination = extracted_text.split("|destino||")[1].split("|")[0].strip()
        except IndexError:
            origin = None
            destination = None
            
    response = f"""
    Dado que el origen hasta el momento es {origin} y el destino es {destination}:
    
    Si ambos son "Nan", regresa un mensaje preguntando por ambos.
    
    Si los dos son válidos, tu trabajo termino, regresa un mensaje que diga que se ha registrado el origen y el destino.
    
    Si solo uno es válido, regresa un mensaje que diga que se ha registrado el origen o el destino, y que se está faltando el otro. Pregunta por el que falta.
    
    Los mensajes de regreso deben ser cortos, concisos y amables.
    """

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=response,
        config=types.GenerateContentConfig(
            max_output_tokens=300,
            temperature=0.5,
            system_instruction=system_instruction
        )
    )
    
    response_text = response.text
    history.append({"role": "model", "parts": [response_text]})
    
    print("llevamos aqui", origin, "|", destination)

    return origin, destination, response_text, history

def extract_location_from_text(text, bus_stations):
    station_list = "\n".join(f"- {station}" for station in bus_stations)
    prompt = f"""
    Tarea: Extraer ubicacion de un texto escrito por un usuario. Tu único objetivo es extrar la ubicación de origen o destino de acuerdo a la lista de líneas de autobús. Regresa en <ubicacion> el nombre en la lista de estaciones de autobus. No regreses una ubicacion que no esté en la lista.
    
    En ocasiones, el usuario no especifica exactamente el lugar de origen o destino, pero puedes inferir si el parecido con la ubicacion es grande con alguna ubicacion en la lista. En tal caso, regresa la ubicacion de la lista.
    
    |origen||<ubicacion>|
    |destino||<ubicacion>|
    
    Si no estás seguro de si la ubicación es de origen o destino, devuelve el texto "Nan". Las líneas de autobuses son: {station_list}. Si no estás seguro de que existe alguno de los dos, devuelve "Nan" en ambos.
    
    El texto de entrada es el siguiente:
    {text}
    """
    
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            max_output_tokens=300,
            temperature=0.2
        )
    )
    print("LA RESPUESTA extraida en esta iteracion:", response.text)
    
    return response.text
    