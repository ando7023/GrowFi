# api_client.py

import requests
import config
import time # For sleep
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

def requests_retry_session(
    retries=3,
    backoff_factor=0.3,
    status_forcelist=(500, 502, 503, 504), # Retry on these server errors
    session=None,
):
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session


def get_klines_from_api(symbol, interval, limit, end_time=None):
    """
    Fetches klines from the configured API (Binance example).
    Kline format: [open_time, open, high, low, close, volume, close_time, ...]
    """
    endpoint = f"{config.API_BASE_URL}klines"
    params = {'symbol': symbol, 'interval': interval, 'limit': limit}
    if end_time:
        params['endTime'] = end_time

    session = requests_retry_session()
    try:
        response = session.get(endpoint, params=params, timeout=(5, 15)) # connect timeout 5s, read timeout 15s
        response.raise_for_status()  # Raises HTTPError for bad responses (4XX or 5XX)
        # Return structure: list of dictionaries
        return [
            {
                'open_time': int(k[0]), 'open': float(k[1]), 'high': float(k[2]),
                'low': float(k[3]), 'close': float(k[4]), 'volume': float(k[5]),
                'close_time': int(k[6])
            } for k in response.json()
        ]
    except requests.exceptions.RequestException as e:
        print(f"API Error (get_klines) for {symbol} ({interval}, {limit}): {e}")
        return []
    except ValueError as e:  # JSON decoding error
        print(f"API Error decoding JSON (get_klines) for {symbol}: {e}")
        return []

def get_current_ticker_data(symbol):
    """
    Fetches the latest 24hr ticker data for a symbol from Binance.
    Includes current price and 24h price change percentage.
    """
    endpoint = f"{config.API_BASE_URL}ticker/24hr"  # Binance specific endpoint
    params = {'symbol': symbol}

    # Check if symbol is None or empty before making API call
    if not symbol:
        print(f"API Error: Symbol is None or empty in get_current_ticker_data.")
        return None

    session = requests_retry_session()
    try:
        response = session.get(endpoint, params=params, timeout=(5,10)) # connect 5s, read 10s
        response.raise_for_status()
        data = response.json()
        return {
            'price': float(data.get('lastPrice', 0.0)),
            'price_change_percent': float(data.get('priceChangePercent', 0.0))
        }
    except requests.exceptions.RequestException as e:
        print(f"API Error (get_ticker) for {symbol}: {e}")
        return None
    except ValueError as e:  # JSON decoding error
        print(f"API Error decoding JSON (get_ticker) for {symbol}: {e}")
        return None
    except KeyError as e:  # If expected keys are missing in response
        print(f"API Error: Unexpected key in ticker data for {symbol} - {e}")
        return None


if __name__ == '__main__':
    # Quick test for the api_client
    print("Testing API client (get_klines_from_api)...")
    test_symbol_klines = "BTCUSDT"
    # Reduced limit for testing if large requests are an issue
    klines = get_klines_from_api(test_symbol_klines, config.KLINE_INTERVAL, 50) 
    if klines:
        print(f"Successfully fetched {len(klines)} klines for {test_symbol_klines}:")
        # for kline in klines:
        #     print(kline)
    else:
        print(f"Failed to fetch klines for {test_symbol_klines}.")

    print("\nTesting API client (get_current_ticker_data)...")
    test_symbol_ticker = "ETHUSDT"
    ticker_data = get_current_ticker_data(test_symbol_ticker)
    if ticker_data:
        print(f"Successfully fetched ticker data for {test_symbol_ticker}: {ticker_data}")
    else:
        print(f"Failed to fetch ticker data for {test_symbol_ticker}.")

