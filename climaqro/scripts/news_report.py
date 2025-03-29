from google import genai
from dotenv import load_dotenv
import os
from concurrent.futures import ThreadPoolExecutor
import time
from google.genai import types
import json

def load_news_scrapped():
    # Cargar el archivo data.json
    try:
        with open('data.json', 'r', encoding='utf-8') as file:
            data = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {
            'noticias_transporte': [],
            'obras_queretaro': {
                'content_text': '',
                'date': '',
                'location': '',
                'time': '',
                'type': '',
                'details': ''
            }
    }
    return data

def format_transport_data(data):
    """Formatea los datos sobre transporte para incluirlos en el contexto"""
    formatted_data = "Información sobre Transporte en México:\n\n"
    
    # Formatear noticias de transporte
    formatted_data += "Últimas Noticias de Transporte:\n"
    for noticia in data['noticias_transporte']:
        formatted_data += f"\n📰 {noticia['titulo']}\n"
        formatted_data += f"📅 Fecha: {noticia['fecha']}\n"
        formatted_data += f"📍 Ubicación: {noticia['ubicacion']}\n"
        formatted_data += f"📝 Contenido: {noticia['contenido']}\n"
        if noticia['hashtags']:
            formatted_data += f"🏷️ Hashtags: {' '.join(noticia['hashtags'])}\n"
    
    # Formatear información específica de Querétaro
    obras_queretaro = data['obras_queretaro']
    formatted_data += "\n⚠️ ATENCIÓN - Obras en Querétaro:\n"
    formatted_data += f"{obras_queretaro['content_text']}\n"
    formatted_data += f"\nDetalles:\n"
    formatted_data += f"- Fecha: {obras_queretaro['date']}\n"
    formatted_data += f"- Ubicación: {obras_queretaro['location']}\n"
    formatted_data += f"- Hora: {obras_queretaro['time']}\n"
    formatted_data += f"- Tipo: {obras_queretaro['type']}\n"
    formatted_data += f"- Detalles: {obras_queretaro['details']}\n"
    
    return formatted_data


def get_news_considerations(user_message, client):
    data = load_news_scrapped()
    # Crear el prompt con el contexto y el mensaje del usuario
    transport_data = format_transport_data(data)
    SYSTEM_INSTRUCTION = """Eres un asistente especializado en transporte público en Querétaro, México. 
    Tu objetivo es proporcionar información precisa y útil sobre las rutas de transporte, 
    paradas, horarios y servicios disponibles en la ciudad.

    Información importante:
    - Debes responder solo preguntas relacionadas con transporte en Querétaro
    - Utiliza la información proporcionada en el archivo data.json
    - Si no tienes información específica sobre algo, indícalo claramente
    - Mantén un tono profesional y amigable
    - Proporciona información detallada y precisa
    """
    prompt = f"{SYSTEM_INSTRUCTION}\n\n{transport_data}\n\nPregunta del usuario: {user_message}\n\nPor favor, responde basándote en la información disponible sobre transporte en Querétaro."
    
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            max_output_tokens=300,
            temperature=0.5
        )
    )
    
    return response