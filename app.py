import pandas as pd
from flask import Flask, render_template, request
import random
import os

app = Flask(__name__)

# ---------------- Load CSV Files ---------------- #
def load_travel_data():
    """Load travel packages from CSV."""
    try:
        df = pd.read_csv('travel_packages.csv')
        numeric_cols = ['price_per_adult', 'price_per_child', 'min_days', 'max_days', 'min_people', 'max_people']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col])
        return df
    except Exception as e:
        print(f"Error loading travel_packages.csv: {e}")
        return pd.DataFrame()

def load_activities():
    """Load activities from CSV and group by destination."""
    try:
        df = pd.read_csv('activities.csv')
        activities = {}
        for dest in df['destination'].unique():
            dest_activities = df[df['destination'] == dest][['name', 'interest']].to_dict('records')
            activities[dest] = dest_activities
        return activities
    except Exception as e:
        print(f"Error loading activities.csv: {e}")
        return {}

# ---------------- Itinerary Generator ---------------- #
def generate_itinerary(destination, interests, pace, days, activities_db):
    """Generates a day-by-day itinerary for a given destination."""
    if destination not in activities_db:
        return None

    all_interests = interests + ['sightseeing']  # Ensure default content
    available_activities = [
        act for act in activities_db[destination] if act['interest'] in all_interests
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

# ---------------- Flask Routes ---------------- #
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/results', methods=['POST'])
def results():
    df = load_travel_data()
    activities_db = load_activities()

    if df.empty or not activities_db:
        return "<h1>Error: Could not load travel or activity data. Check the CSV files.</h1>"

    try:
        season = request.form['season']
        days = int(request.form['days'])
        adults = int(request.form['adults'])
        children = int(request.form['children'])
        budget = int(request.form['budget'])
        interests = request.form.getlist('interest')
        pace = request.form['pace']
        total_people = adults + children
    except (KeyError, ValueError) as e:
        return f"<h1>Invalid Form Data</h1><p>Error: {e}</p>"

    # Filter packages
    filtered = df[df['season'].str.lower() == season.lower()]
    filtered = filtered[
        (filtered['min_days'] <= days) & (filtered['max_days'] >= days) &
        (filtered['min_people'] <= total_people) & (filtered['max_people'] >= total_people) &
        (filtered['price_per_adult'] <= budget)
    ]

    filtered = filtered.copy()
    if not filtered.empty:
        filtered['total_cost'] = (filtered['price_per_adult'] * adults) + (filtered['price_per_child'] * children)
        filtered['itinerary'] = filtered.apply(
            lambda row: generate_itinerary(row['destination'], interests, pace, row['min_days'], activities_db),
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