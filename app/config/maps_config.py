"""
Xarita konfiguratsiyasi
Map configuration for switching between providers
"""

# Xarita provayderi: 'yandex' yoki 'google'
# Map provider: 'yandex' or 'google'
MAP_PROVIDER = 'yandex'

# Yandex Maps API Key (https://developer.tech.yandex.ru/ — bepul kalit olish mumkin)
YANDEX_MAPS_API_KEY = '096da66c-342b-4bab-80cd-3b44b851429c'

# Google Maps API Key (faqat MAP_PROVIDER='google' bo'lganda kerak)
# Google Maps API Key (only needed when MAP_PROVIDER='google')
GOOGLE_MAPS_API_KEY = ''  # Bu yerga API key kiriting / Enter your API key here

# Default xarita markazi (Toshkent)
# Default map center (Tashkent)
DEFAULT_CENTER = {
    'latitude': 41.311081,
    'longitude': 69.240562,
    'zoom': 12
}

# Marker ranglari
# Marker colors
MARKER_COLORS = {
    'agent': '#0d6efd',      # Ko'k / Blue
    'driver': '#0dcaf0',     # Moviy / Cyan
    'partner': '#198754'     # Yashil / Green
}
