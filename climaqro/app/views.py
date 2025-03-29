from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import google.generativeai as genai
from dotenv import load_dotenv
import os
from scripts.climate_report import generate_report, include_climate_in_time_estimated
from scripts.news_report import get_news_considerations
from scripts.chatbot import handle_interaction

# Cargar variables de entorno
load_dotenv()
route_found = False
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))


@csrf_exempt
def chatbot(request):
    if request.method == 'POST':
        # input from chatbot
        user_input = request.POST.get('user_input')
        
        # global input from user
        city_name = None
        state_code = None
        country_code = None

        origin = request.session.get('origin')
        destination = request.session.get('destination')
        history = request.session.get('history', [])
        
        bus_stations = [
            "Av. Candiles y Plaza Candiles",
            "Juan N. Frias",
            "Juan penurias",
            "Tejeda"
        ]

        origin, destination, response_text, updated_history = handle_interaction(
            user_input, origin, destination, history, bus_stations, client
        )

        request.session['origin'] = origin
        request.session['destination'] = destination
        request.session['history'] = updated_history
        
        request.session.modified = True
        
        if origin is not None and destination is not None and origin != "Nan" and destination != "Nan":
            route_found = True
        
        
        if not city_name or not state_code or not country_code:
            city_name = "Queretaro"
            state_code = "MX-QUE"
            country_code = "MX"
        
        if route_found:
            news_awareness = get_news_considerations(user_input, client)
            context = generate_report(city_name, state_code, country_code)
            climate_report = include_climate_in_time_estimated(context, city_name, origin, destination, client, hour="13:00")

        return JsonResponse({
            'response': response_text,
            'origin': origin,
            'destination': destination
        })
    if request.method == 'GET':
        return render(request, 'app/chat.html')

            

def health_check(request):
    """Vista para verificar el estado de la API"""
    return JsonResponse({'status': 'ok'})



# Deprecated: This endpoint is not used anymore, just for development purposes
def weather_report(request):
    if request.method == 'GET':
        city_name = request.GET.get('city_name')
        state_code = request.GET.get('state_code')
        country_code = request.GET.get('country_code')
        origin = request.GET.get('origin')
        destination = request.GET.get('destination')
        
        if city_name == None and state_code == None and country_code == None:
                city_name = "Queretaro"
                state_code = "MX-QUE"
                country_code = "MX"
                origin = "Av. Candiles y Plaza Candiles"
                destination = "Juan N. Frias"
        
        context = generate_report(city_name, state_code, country_code)
        climate_report = include_climate_in_time_estimated(context, city_name, origin, destination, hour="13:00")
    
        return JsonResponse({
            'context': context,
            'climate_report': climate_report
        })
