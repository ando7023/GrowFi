import requests
try:
    response = requests.get('https://www.google.com', timeout=5)
    print("Google request successful:", response.status_code)
except requests.exceptions.SSLError as e:
    print("SSL Error connecting to Google:", e)
except Exception as e:
    print("Other error connecting to Google:", e)

try:
    response_binance_ping = requests.get('https://api.binance.com/api/v3/ping', timeout=5)
    print("Binance ping successful:", response_binance_ping.status_code)
except requests.exceptions.SSLError as e:
    print("SSL Error connecting to Binance ping:", e)
except Exception as e:
    print("Other error connecting to Binance ping:", e)