from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import google.generativeai as genai
from dotenv import load_dotenv
from google import genai
import os
from scripts.climate_report import generate_report, include_climate_in_time_estimated
from scripts.news_report import get_news_considerations
from scripts.chatbot import handle_interaction, last_interaction
from scripts.location_analysis import get_most_common_routes, get_home_work_locations
from scripts.route_report import get_route

# Cargar variables de entorno
load_dotenv()
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
        
        # try to predict even before user input
        # agregarle ubicacion actual consulta
        if user_input == "Ir a casa":
            home_work = get_home_work_locations()
            destination = home_work['home']
        elif user_input == "Ir a trabajo":
            home_work = get_home_work_locations()
            destination = home_work['work']
           

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
            
        
        if not city_name or not state_code or not country_code:
            city_name = "Queretaro"
            state_code = "MX-QUE"
            country_code = "MX"
        
        if os.getenv("route_found") == "True":
            print("Ruta encontrada!")
            # hay que arreglar lo del route
            ruta = get_route()
            news_awareness = get_news_considerations(ruta, client)
            print(news_awareness)
            context = generate_report(city_name, state_code, country_code)
            climate_report = include_climate_in_time_estimated(context, city_name, origin, destination, client, hour="13:00")
            print(climate_report)
            # last response_text
            response_text = last_interaction(news_awareness, climate_report, response_text, client)

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
