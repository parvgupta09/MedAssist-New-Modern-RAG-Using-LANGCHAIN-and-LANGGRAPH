# This is the script that handles the Gogle Places API and find the relevant doctor/clinic recommendations for the patient based on the top 3 possible medical diagnosed diseases.

import requests
from langchain_core.messages import HumanMessage
from src.config import GOOGLE_PLACES_API_KEY, get_light_llm

def search_local_doctors(diseases: list, location: str) -> list:
    llm = get_light_llm()
    prompt = f"The patient has been diagnosed with these possible conditions: {diseases}. What specific type of medical specialist should they see? (e.g., Pulmonologist, Dermatologist, General Physician, Cardiologist). Reply ONLY with the name of the specialty, nothing else."

    speciality = llm.invoke([HumanMessage(content=prompt)]).content.strip()

    query = f"Top rated {speciality} in {location}"
    
    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_PLACES_API_KEY,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.rating"
    }
    payload = {
        "textQuery": query,
        "maxResultCount": 5,
        "minRating": 4.0
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 200:
        places = response.json().get("places",[])
        results = []
        for place in places:
            name = place.get("displayName",{}).get("text","Unknown Clinic")
            address  = place.get("formattedAddress","Unknown Address")
            rating = place.get("rating", "N/A")

            results.append(f"{name} ({address}) - Rating: {rating}/5")
        return results if results else [f"No highly rated {speciality} found in your area."]
    else:
        return ["Error connecting to the google places API. Please try again later."]