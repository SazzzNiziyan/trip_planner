import pandas as pd
from flask import Flask, render_template, request
import random
import os
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics.pairwise import cosine_similarity
import warnings

# Suppress pandas warnings
warnings.filterwarnings("ignore", category=UserWarning, module='pandas')

app = Flask(__name__)

# --- Global variables for the model and data ---
travel_df = pd.DataFrame()
feature_matrix = None
vectorizer = None
scaler = None

# ---------------- Load and Preprocess Data for the Model ---------------- #
def load_and_preprocess_data():
    """
    Loads travel data, preprocesses it, and creates a feature matrix for cosine similarity.
    This function runs only once when the application starts.
    """
    global travel_df, feature_matrix, vectorizer, scaler

    try:
        # Load data
        travel_df = pd.read_csv('travel_packages.csv')
        
        # --- Feature Engineering ---
        # 1. Clean up data and handle potential NaN values
        travel_df['description'].fillna('', inplace=True)
        travel_df.dropna(subset=['price_per_adult', 'min_days', 'max_days', 'min_people', 'max_people'], inplace=True)
        
        # 2. Combine text features into a single 'tags' column for vectorization
        travel_df['tags'] = travel_df['description'] + ' ' + travel_df['season']
        
        # 3. Vectorize the 'tags' column using TF-IDF
        vectorizer = TfidfVectorizer(max_features=500, stop_words='english')
        tfidf_matrix = vectorizer.fit_transform(travel_df['tags']).toarray()
        
        # 4. Scale numerical features
        numeric_cols = ['price_per_adult', 'min_days', 'max_days', 'min_people', 'max_people']
        scaler = MinMaxScaler()
        scaled_numeric = scaler.fit_transform(travel_df[numeric_cols])
        
        # 5. Combine TF-IDF features and scaled numeric features into a final matrix
        feature_matrix = np.hstack((tfidf_matrix, scaled_numeric))
        
        print("Data loaded and preprocessed successfully.")

    except Exception as e:
        print(f"Error loading and preprocessing data: {e}")

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

    all_interests = interests + ['sightseeing']
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
    global travel_df, feature_matrix, vectorizer, scaler
    activities_db = load_activities()

    if travel_df.empty or feature_matrix is None or not activities_db:
        return "<h1>Error: Could not load or process travel data. Check the console for errors.</h1>"

    try:
        # Get user input
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

    # --- Step 1: Hard Filtering ---
    # Filter packages that are strictly not suitable
    filtered_df = travel_df[
        (travel_df['min_days'] <= days) &
        (travel_df['max_days'] >= days) &
        (travel_df['min_people'] <= total_people) &
        (travel_df['max_people'] >= total_people) &
        (travel_df['price_per_adult'] <= budget)
    ].copy()
    
    if filtered_df.empty:
        return render_template('results.html', results=[])

    # --- Step 2: Create User Preference Vector ---
    # Create a vector for the user's preferences in the same format as the feature matrix
    user_tags = ' '.join(interests) + ' ' + season
    user_tfidf = vectorizer.transform([user_tags]).toarray()
    
    # Create a dummy DataFrame for scaling the user's numeric inputs
    user_numeric_df = pd.DataFrame([[budget, days, days, total_people, total_people]], columns=['price_per_adult', 'min_days', 'max_days', 'min_people', 'max_people'])
    user_scaled_numeric = scaler.transform(user_numeric_df)
    
    user_vector = np.hstack((user_tfidf, user_scaled_numeric))

    # --- Step 3: Cosine Similarity ---
    # Get the feature matrix corresponding to the filtered_df
    filtered_indices = filtered_df.index
    filtered_feature_matrix = feature_matrix[filtered_indices]

    # Calculate cosine similarity
    similarities = cosine_similarity(user_vector, filtered_feature_matrix).flatten()

    # Add similarity scores to the filtered DataFrame
    filtered_df['similarity'] = similarities
    
    # --- Step 4: Rank and Prepare Results ---
    # Sort by similarity score in descending order and get the top 10 results
    recommended_df = filtered_df.sort_values(by='similarity', ascending=False).head(10)
    
    # Add total cost and itinerary to the recommended results
    if not recommended_df.empty:
        recommended_df['total_cost'] = (recommended_df['price_per_adult'] * adults) + (recommended_df['price_per_child'] * children)
        recommended_df['itinerary'] = recommended_df.apply(
            lambda row: generate_itinerary(row['destination'], interests, pace, days, activities_db),
            axis=1
        )

    results_list = recommended_df.to_dict('records')
    return render_template('results.html', results=results_list)


# This block runs the app and is essential for deployment
if __name__ == '__main__':
    # Load and preprocess data once at startup
    load_and_preprocess_data()
    # Get port from environment variable, default to 10000 for local testing
    port = int(os.environ.get('PORT', 10000))
    # Host '0.0.0.0' makes the server publicly available
    app.run(host='0.0.0.0', port=port)