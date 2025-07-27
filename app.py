import os
import pandas as pd
from flask import Flask, render_template, request

# 1. Initialize the Flask App
app = Flask(__name__)

# 2. Helper function to load and clean data
def load_travel_data():
    """Loads data from CSV and converts price columns to numbers."""
    try:
        df = pd.read_csv('travel_packages.csv')
        # Convert price columns to a number type to prevent errors
        df['price_per_adult'] = pd.to_numeric(df['price_per_adult'])
        df['price_per_child'] = pd.to_numeric(df['price_per_child'])
        # Convert other numeric columns to be safe
        df['min_days'] = pd.to_numeric(df['min_days'])
        df['max_days'] = pd.to_numeric(df['max_days'])
        df['min_people'] = pd.to_numeric(df['min_people'])
        df['max_people'] = pd.to_numeric(df['max_people'])
        return df
    except FileNotFoundError:
        print("Error: 'travel_packages.csv' not found. Make sure the file is in the correct directory.")
        return pd.DataFrame()
    except Exception as e:
        print(f"An error occurred while processing the CSV: {e}")
        return pd.DataFrame()

# 3. Route for the home page (the form)
@app.route('/')
def index():
    """Renders the main input form page."""
    return render_template('index.html')

# 4. Route to handle form submission and display results
@app.route('/results', methods=['POST'])
def results():
    """Processes form data and displays matching travel packages."""
    df = load_travel_data()
    if df.empty:
        return "<h1>Error: Could not load travel data.</h1><p>Please check the server console for details.</p>"

    # Get user input from the form
    try:
        season = request.form['season']
        days = int(request.form['days'])
        adults = int(request.form['adults'])
        children = int(request.form['children'])
        budget = int(request.form['budget'])
        total_people = adults + children
    except (KeyError, ValueError) as e:
        return f"<h1>Invalid Form Data</h1><p>Please go back and fill all fields correctly. Error: {e}</p>"

    # Filter the DataFrame based on user preferences
    filtered = df[df['season'].str.lower() == season.lower()]
    filtered = filtered[(filtered['min_days'] <= days) & (filtered['max_days'] >= days)]
    filtered = filtered[(filtered['min_people'] <= total_people) & (filtered['max_people'] >= total_people)]
    filtered = filtered[filtered['price_per_adult'] <= budget]
    
    # Use .copy() to avoid a SettingWithCopyWarning from pandas
    filtered = filtered.copy()

    # Calculate total cost for each remaining package
    if not filtered.empty:
        filtered['total_cost'] = (filtered['price_per_adult'] * adults) + (filtered['price_per_child'] * children)

    # Convert results to a list of dictionaries
    results_list = filtered.to_dict('records')

    # Display the results
    if not results_list:
        return "<h1>No matching trips found! 😞</h1><p>Try adjusting your preferences and search again.</p>"
    else:
        response_html = "<h1>Here are your personalized trip options! ✨</h1>"
        for item in results_list:
            response_html += f"""
            <div style='border: 1px solid #ccc; border-radius: 8px; padding: 15px; margin: 15px; font-family: sans-serif;'>
                <h2>{item['destination']}</h2>
                <p><strong>Description:</strong> {item['description']}</p>
                <p><strong>Days:</strong> {item['min_days']} - {item['max_days']}</p>
                <p><strong>Total Estimated Cost:</strong> ₹{int(item['total_cost'])}</p>
            </div>
            """
        return response_html

# 5. Run the app
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
import os