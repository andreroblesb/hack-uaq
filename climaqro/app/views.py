from django.shortcuts import render
from scripts.climate_report import generate_report, include_climate_in_time_estimated
from scripts.chatbot import handle_interaction
from django.http import HttpResponse
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

# Create your views here.


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
                origin = " Av. Candiles y Plaza Candiles"
                destination = "Juan N. Frias"
        
        context = generate_report(city_name, state_code, country_code)
        print("terminamos!")
        climate_report = include_climate_in_time_estimated(context, city_name, origin, destination, hour="13:00")
    
    return HttpResponse(f"Info given: {context}, climate_report: {climate_report}")

@csrf_exempt
def chatbot(request):
    if request.method == 'POST':
        # print("🔎 Sesión actual:", dict(request.session))  
        user_input = request.POST.get('user_input')  # <- Django espera POST con x-www-form-urlencoded

        origin = request.session.get('origin')
        destination = request.session.get('destination')
        history = request.session.get('history', [])
        
        bus_stations = [
            "Av. Candiles y Plaza Candiles",
            "Juan N. Frias",
        ]

        origin, destination, response_text, updated_history = handle_interaction(
            user_input, origin, destination, history, bus_stations
        )

        request.session['origin'] = origin
        request.session['destination'] = destination
        request.session['history'] = updated_history
        
        request.session.modified = True

        return JsonResponse({'response': response_text})
    if request.method == 'GET':
        return render(request, 'app/chat.html')
