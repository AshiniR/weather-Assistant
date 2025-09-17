import re

from core.config import geolocator


def parse_location(user_input: str):
    """Extract city and country if provided, else return just the first part."""
    
    # Remove all punctuation/marks and trim spaces
    user_input = re.sub(r'[^\w\s]', '', user_input).strip()
    # Try to extract after 'in <location>' or 'at <location>'
    match = re.search(r'\b(?:in|at)\s+([A-Za-z\s]+)', user_input, re.IGNORECASE)
    if match:
        location_text = match.group(1).strip()
    else:
        # Try to extract after 'wear in <location>'
        match2 = re.search(r'wear in ([A-Za-z\s]+)', user_input, re.IGNORECASE)
        if match2:
            location_text = match2.group(1).strip()
        else:
            # Try to extract after 'weather in <location>'
            match3 = re.search(r'weather in ([A-Za-z\s]+)', user_input, re.IGNORECASE)
            if match3:
                location_text = match3.group(1).strip()
            else:
                # Try to extract last word if it looks like a place
                tokens = user_input.strip().split()
                # Remove common trailing words
                trailing = {'today', 'now', 'please', 'tomorrow', 'tonight', 'currently', 'week', 'morning', 'evening', 'weather', 'wear', 'should', 'i', 'what'}
                filtered = [t for t in tokens if t.lower() not in trailing]
                # If any capitalized word left, use last one
                cap_words = [t for t in filtered if t and t[0].isupper()]
                if cap_words:
                    location_text = cap_words[-1]
                elif filtered:
                    location_text = filtered[-1]
                else:
                    location_text = user_input.strip()

    # Remove trailing non-location words (e.g., 'today', 'now', 'please', 'tomorrow')
    location_text = re.sub(r'\b(today|now|please|tomorrow|right now|currently|this week|tonight|in the morning|in the evening|weather|wear|should|i|what)\b', '', location_text, flags=re.IGNORECASE).strip()
    # Remove any double spaces left after removal
    location_text = re.sub(r'\s+', ' ', location_text)
    parts = [p.strip() for p in location_text.split(",")]
    if len(parts) == 2:
        return parts[0], parts[1]
    else:
        return parts[0], None

def get_location(city: str, country: str = None):
    """Geocode city + optional country into lat/lon."""
    if country:
        query = f"{city}, {country}"
    else:
        query = city
    place = geolocator.geocode(query, timeout=10)
    if not place:
        # If no country was provided, ask the user for it
        if not country or country.strip() == "":
            return {"need_country": True, "city": city}
        return None
    # Use the resolved place name if available
    resolved_city = getattr(place, 'raw', {}).get('display_name', None)
    if resolved_city:
        resolved_city = resolved_city.split(',')[0]
    return {
        "city": resolved_city or city,
        "country": country or "",
        "latitude": place.latitude,
        "longitude": place.longitude,
    }