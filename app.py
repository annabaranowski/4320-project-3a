from flask import Flask, render_template, request, flash, url_for, redirect
import requests
import pygal
import lxml
import os
import webbrowser 
from datetime import datetime
import csv

API_KEY = "93BVEKRT85P73950"
BASE_URL = "https://www.alphavantage.co/query"

app = Flask(__name__)
app.config["DEBUG"] = True
app.config["SECRET_KEY"] = 'your secret key'
app.secret_key = 'your secret key'

def get_symbols_from_file(filepath='stocks.csv'):
    symbols = []
    with open(filepath, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            symbols.append(row['Symbol'])
    return symbols

@app.route('/', methods=['GET', 'POST'])
def index():
    symbols = get_symbols_from_file()

    if request.method == 'POST':
        #get the form data
        symbol = request.form.get('symbol')
        chart_type = request.form.get('chart_type')
        time_series = request.form.get('time_series')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')

        # Get and validate the start date
        while True:
            try:
                # Get the start date as a string and remove any whitespace
                start_date = start_date.strip()
                # Convert the string to a datetime object for validation and comparison
                # This also verifies that the date format is correct
                start_date = datetime.strptime(start_date, "%Y-%m-%d")
                # If we reach this point, the date format is valid, so exit the loop
                break
            except ValueError:
                # This exception is raised if the date format is incorrect or if the date is invalid
                # (e.g., February 30th or text instead of a date)
                flash("Error: Please enter a valid date in the format YYYY-MM-DD.")
        
        # Get and validate the end date
        while True:
            try:
                # Get the end date as a string and remove any whitespace
                end_date = end_date.strip()
                # Convert the string to a datetime object for validation and comparison
                end_date = datetime.strptime(end_date, "%Y-%m-%d")
                
                # Check that the end date is not before the start date
                # This is a logical validation to ensure the date range makes sense
                if end_date < start_date:
                    flash("Error: End date cannot be before start date. Please enter a valid end date.")
                    break
                else:
                    # If the end date is valid and after the start date, exit the loop
                    break
            except ValueError:
                # This exception is raised if the date format is incorrect or if the date is invalid
                flash("Error: Please enter a valid date in the format YYYY-MM-DD.")
                break

        time_series_map = {
            "intraday": "TIME_SERIES_INTRADAY",  # For intraday data (typically with a 60min interval)
            "daily": "TIME_SERIES_DAILY",     # For daily data
            "weekly": "TIME_SERIES_WEEKLY",    # For weekly data
            "monthly": "TIME_SERIES_MONTHLY"    # For monthly data
        }

        time_series_function = time_series_map.get(time_series)

        inputs = {
            "symbol": symbol,                              # Stock symbol (e.g., "AAPL" for Apple)
            "chart_type": chart_type,                      # Chart type (1 for Bar, 2 for Line)
            "time_series_function": time_series_function,  # API function name
            "start_date": start_date,                      # Start date as datetime object
            "end_date": end_date,                          # End date as datetime object
            "time_series_option": time_series              # Original time series selection (1-4)
        }

        stock_data = fetch_data(inputs)

        time_series, open_prices, high_prices, low_prices, close_prices = get_stock_data(stock_data, inputs)
        dates = time_series.keys()

        chart = get_chart_type(chart_type, inputs, dates, open_prices, high_prices, low_prices, close_prices)
        
        if chart:
            return render_template('index.html', chart=chart, symbols=symbols)
        else:
            flash("Error fetching data.")
            return render_template('index.html')
    
    return render_template('index.html', symbols=symbols)

def fetch_data(user_input):
    # Build a dictionary of parameters to send to the Alpha Vantage API
    # These parameters tell the API what data we're requesting
    params = {
        "function": user_input["time_series_function"],  # Which time series to retrieve (daily, weekly, etc.)
        "symbol": user_input["symbol"],                  # The stock ticker symbol
        "apikey": API_KEY,                               # Authentication key for API access
        "month": "{}-{:02}".format(user_input["start_date"].year, user_input["start_date"].month), # Month to pull data from
        "outputsize": "full"                             # Request entire data so it does not cut off
    }
    
    # For intraday data (option 1), we need to also specify how frequently we want data points
    # This adds a parameter requesting data at 60-minute intervals
    # Also need to specify that we want the entire month of data to be pulled
    if user_input["time_series_option"] == "intraday":
        params["interval"] = "60min"
    
    try:
        # Make the HTTP GET request to the Alpha Vantage API
        response = requests.get(BASE_URL, params=params)
        
        # Parse the JSON response into a Python dictionary
        data = response.json()
        
        # Return the data for further processing
        return data
        
    except requests.exceptions.RequestException as e:
        # This catches any errors related to the request itself
        flash(f"Error fetching data: {e}")
        return None
   
#function to retrieve the open, high, low, and close
def get_stock_data(data, inputs):
    print(data)
    # Get the keys since we won't know what the time series will be called in the dictionary
    keys = list(data.keys())
    #grab the time series key since we
    time_series_data = keys[1]
    
    #declare variables to hold separated data points
    open_prices = []
    high_prices = []
    low_prices = []
    close_prices = []
    
    #access the time series data using the time_series_data key
    time_series = data.get(time_series_data)

    # only use data that falls between the start and end dates
    # filter for intraday (uses timestamp with time)
    if inputs["time_series_option"] == "intraday":
        filtered_time_series = {
            timestamp: values for timestamp, values in time_series.items()
            if inputs["start_date"] < datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S") < inputs["end_date"]
        }
    # filter for all others (uses timestamp with just date)
    else:
        filtered_time_series = {
            timestamp: values for timestamp, values in time_series.items()
            if inputs["start_date"] < datetime.strptime(timestamp, "%Y-%m-%d") < inputs["end_date"]
        }
    
    #iterate through the time series data and add stock data points associated with that time stamp to their lists
    for timestamp, values in filtered_time_series.items():
        open_price = values.get('1. open')
        open_prices.append(int(float(open_price)))
        high_price = values.get('2. high')
        high_prices.append(int(float(high_price)))
        low_price = values.get('3. low')
        low_prices.append(int(float(low_price)))
        close_price = values.get('4. close')
        close_prices.append(int(float(close_price)))

    return filtered_time_series, open_prices, high_prices, low_prices, close_prices

def get_chart_type(chart_type, inputs, dates, open_prices, high_prices, low_prices, close_prices):
    if chart_type == "bar":
        bar_chart = pygal.Bar()
        if inputs["time_series_option"] == "intraday":
            bar_chart.title = f'Intraday Stock Data for {inputs["symbol"]} from {inputs["start_date"]} to {inputs["end_date"]}'
        elif inputs["time_series_option"] == "daily":
            bar_chart.title = f'Daily Stock Data for {inputs["symbol"]} from {inputs["start_date"]} to {inputs["end_date"]}'
        elif inputs["time_series_option"] == "weekly":
            bar_chart.title = f'Weekly Stock Data for {inputs["symbol"]} from {inputs["start_date"]} to {inputs["end_date"]}'
        elif inputs["time_series_option"] == "monthly":
            bar_chart.title = f'Monthly Stock Data for {inputs["symbol"]} from {inputs["start_date"]} to {inputs["end_date"]}'
        bar_chart.x_labels = dates
        bar_chart.x_label_rotation = 90 # rotate labels so they fit better
        bar_chart.add('Open', open_prices)
        bar_chart.add('High', high_prices)
        bar_chart.add('Low', low_prices)
        bar_chart.add('Close', close_prices)
        return bar_chart.render_data_uri()
    else:
        line_chart = pygal.Line()
        if inputs["time_series_option"] == "intraday":
            line_chart.title = f'Intraday Stock Data for {inputs["symbol"]} from {inputs["start_date"]} to {inputs["end_date"]}'
        elif inputs["time_series_option"] == "daily":
            line_chart.title = f'Daily Stock Data for {inputs["symbol"]} from {inputs["start_date"]} to {inputs["end_date"]}'
        elif inputs["time_series_option"] == "weekly":
            line_chart.title = f'Weekly Stock Data for {inputs["symbol"]} from {inputs["start_date"]} to {inputs["end_date"]}'
        elif inputs["time_series_option"] == "monthly":
            line_chart.title = f'Monthly Stock Data for {inputs["symbol"]} from {inputs["start_date"]} to {inputs["end_date"]}'
        line_chart.x_labels = dates
        line_chart.x_label_rotation = 90 # rotate labels so they fit better
        line_chart.add('Open', open_prices)
        line_chart.add('High', high_prices)
        line_chart.add('Low', low_prices)
        line_chart.add('Close', close_prices)
        return line_chart.render_data_uri()

app.run(host="0.0.0.0", port=5000)