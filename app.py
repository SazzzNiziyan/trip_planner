import pandas as pd
from flask import Flask, render_template, request
import random
import os

# Initialize the Flask App
app = Flask(__name__)

# --- Itinerary Generation Logic ---
# This data is migrated from the JavaScript Itinerary Planner
ACTIVITIES_DB = {
    "Paris": [
        { "name": "Visit the Louvre Museum", "interest": "art" },
        { "name": "Climb the Eiffel Tower for sunset views", "interest": "sightseeing" },
        { "name": "Explore the historic Le Marais district", "interest": "culture" },
        { "name": "Take a day trip to the Palace of Versailles", "interest": "history" },
        { "name": "Enjoy a food tour in Montmartre", "interest": "food" },
        { "name": "Window shop on the Champs-Élysées", "interest": "shopping" },
        { "name": "Relax in the Luxembourg Gardens", "interest": "nature" },
        { "name": "Experience a show at the Moulin Rouge", "interest": "nightlife" },
        { "name": "See Impressionist art at Musée d'Orsay", "interest": "art" }
    ],
    "Goa": [
        { "name": "Relax and enjoy the shacks at Baga Beach", "interest": "beach" },
        { "name": "Explore the UNESCO World Heritage churches of Old Goa", "interest": "history" },
        { "name": "Visit a local spice plantation", "interest": "nature" },
        { "name": "Shop at the Anjuna Flea Market", "interest": "shopping" },
        { "name": "Try local Goan seafood curry", "interest": "food" },
        { "name": "Watch the sunset from Chapora Fort", "interest": "sightseeing" },
        { "name": "Experience the nightlife on Tito's Lane", "interest": "nightlife" },
        { "name": "Go on a dolphin-watching boat trip", "interest": "nature" }
    ],
    "Kyoto": [
        { "name": "Visit the golden Kinkaku-ji Temple", "interest": "history" },
        { "name": "Walk through the Arashiyama Bamboo Grove", "interest": "nature" },
        { "name": "Explore the Gion district, famous for Geishas", "interest": "culture" },
        { "name": "See thousands of red gates at Fushimi Inari Shrine", "interest": "sightseeing" },
        { "name": "Experience a traditional tea ceremony", "interest": "culture" },
        { "name": "Enjoy Nishiki Market for local snacks", "interest": "food" },
        { "name": "Visit the Kyoto Imperial Palace", "interest": "history" },
        { "name": "Browse the traditional shops on Sannenzaka street", "interest": "shopping"}
    ]
    # Add more destinations here to expand the itinerary feature
}

def generate_itinerary(destination, interests, pace, days):
    """Generates a day-by-day itinerary for a given destination."""
    if destination not in ACTIVITIES_DB:
        return None

    # Filter activities based on user's interests
    # Add 'sightseeing' as a default interest to ensure there's always something to show
    all_interests = interests + ['sightseeing']
    available_activities = [
        act for act in ACTIVITIES_DB[destination] if act['interest'] in all_interests
    ]
    
    random.shuffle(available_activities)

    activities_per_day = 4 if pace == 'packed' else 2
    itinerary = []

    for day in range(1, int(days) + 1):
        day_activities = []
        for _ in range(activities_per_day):
            if available_activities:
                day_activities.append(available_activities.pop())
        if day_activities:
            itinerary.append({"day": day, "activities": day_activities})
            
    return itinerary


# Helper function to load and clean data
def load_travel_data():
    """Loads data from CSV and handles potential errors."""
    try:
        df = pd.read_csv('travel_packages.csv')
        numeric_cols = ['price_per_adult', 'price_per_child', 'min_days', 'max_days', 'min_people', 'max_people']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col])
        return df
    except (FileNotFoundError, Exception) as e:
        print(f"Error loading or processing travel_packages.csv: {e}")
        return pd.DataFrame()

# Route for the home page (the form)
@app.route('/')
def index():
    """Renders the main input form page."""
    return render_template('index.html')

# Route to handle form submission and display results
@app.route('/results', methods=['POST'])
def results():
    """Processes form data and displays matching travel packages with itineraries."""
    df = load_travel_data()
    if df.empty:
        return "<h1>Error: Could not load travel data. Please check server logs.</h1>"

    try:
        # --- Get All Inputs from the Combined Form ---
        season = request.form['season']
        days = int(request.form['days'])
        adults = int(request.form['adults'])
        children = int(request.form['children'])
        budget = int(request.form['budget'])
        interests = request.form.getlist('interest') # Gets a list of checked interests
        pace = request.form['pace']
        total_people = adults + children
    except (KeyError, ValueError) as e:
        return f"<h1>Invalid Form Data</h1><p>Please go back and fill all fields correctly. Error: {e}</p>"

    # --- Filter for Trip Packages (Original Logic) ---
    filtered = df[df['season'].str.lower() == season.lower()]
    filtered = filtered[(filtered['min_days'] <= days) & (filtered['max_days'] >= days)]
    filtered = filtered[(filtered['min_people'] <= total_people) & (filtered['max_people'] >= total_people)]
    filtered = filtered[filtered['price_per_adult'] <= budget]
    
    filtered = filtered.copy()

    # Calculate total cost and generate itinerary for each result
    if not filtered.empty:
        filtered['total_cost'] = (filtered['price_per_adult'] * adults) + (filtered['price_per_child'] * children)
        # --- Generate Itinerary for each valid result ---
        filtered['itinerary'] = filtered.apply(
            lambda row: generate_itinerary(row['destination'], interests, pace, row['min_days']),
            axis=1
        )

    results_list = filtered.to_dict('records')

    return render_template('results.html', results=results_list)

# This block runs the app and is essential for deployment
if __name__ == '__main__':
    # Get port from environment variable, default to 10000 for local testing
    port = int(os.environ.get('PORT', 10000))
    # Host '0.0.0.0' makes the server publicly available
    app.run(host='0.0.0.0', port=port)