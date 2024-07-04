import pandas as pd
import numpy as np
import plotly.graph_objs as go
from plotly.subplots import make_subplots
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time
import datetime
import logging
# Global variables to store processed data
processed_data = {}

# Function to process data and filter by time range
# =============================================================================
# def process_data(filename, resample_interval='1Min', start_time='05:30', end_time='11:59'):
#     """Process the data from CSV file into a resampled format and filter only today's data in a specific time range."""
#     try:
#         data = pd.read_csv(filename, header=None, names=['Token', 'Price', 'Timestamp', 'oi'])
#         data['Timestamp'] = pd.to_datetime(data['Timestamp'], errors='coerce')
#         data.set_index('Timestamp', inplace=True, drop=False)
#         data.sort_index(inplace=True)
#         
#         # Define today's date range
#         today = pd.Timestamp.now().normalize()
#         start_time = pd.to_datetime(start_time).time()
#         end_time = pd.to_datetime(end_time).time()
# 
#         # Filter data for today and within the specified time range
#         filtered_data = data[(data['Timestamp'].dt.date == today.date()) &
#                              (data['Timestamp'].dt.time >= start_time) &
#                              (data['Timestamp'].dt.time <= end_time)]
#         
#         if filtered_data.empty:
#             print(f"No data available for {filename} in the specified time range.")
#             return pd.DataFrame()  # Return an empty DataFrame if no data is available
# 
#         # Resample to the specified interval and calculate the mean price
#         resampled_data = filtered_data.resample(resample_interval, on='Timestamp').mean()
#         return resampled_data
#     except Exception as e:
#         print(f"Error processing data from {filename}: {e}")
#         return pd.DataFrame()
# =============================================================================
def process_data(filename, resample_interval='1Min', start_time='09:15', end_time='15:33'):
    """Process the data from CSV file into a resampled format and filter only today's data in a specific time range."""
    try:
        data = pd.read_csv(filename, header=None, names=['Token', 'Price', 'Timestamp', 'oi'])
        data['Timestamp'] = pd.to_datetime(data['Timestamp'], errors='coerce')
        data.set_index('Timestamp', inplace=True, drop=False)
        data.sort_index(inplace=True)
        
        # Define today's date range
        today = pd.Timestamp.now().normalize()
        start_time = pd.Timestamp.combine(today, pd.to_datetime(start_time).time())
        end_time = pd.Timestamp.combine(today, pd.to_datetime(end_time).time())

        # Filter data for today and within the specified time range
        filtered_data = data[(data['Timestamp'] >= start_time) & (data['Timestamp'] <= end_time)]
        
        if filtered_data.empty:
            logging.info(f"No data available for {filename} in the specified time range.")
            return pd.DataFrame(), None  # Return an empty DataFrame and None if no data is available

        # Find the latest token
        latest_token = filtered_data.loc[filtered_data['Timestamp'] == filtered_data['Timestamp'].max(), 'Token'].values[0]
        
        # Filter data for the latest token
        token_data = filtered_data[filtered_data['Token'] == latest_token]
        # Resample to the specified interval and calculate the mean price
        resampled_data = token_data.resample(resample_interval, on='Timestamp').mean()
    
        logging.info(f"Processed data for token {latest_token} from {start_time} to {end_time}.")
        return resampled_data, latest_token
    except Exception as e:
        logging.error(f"Error processing data from {filename}: {e}")
        return pd.DataFrame(), None  # Ensure it returns a tuple with an empty DataFrame and None

# Function to calculate Simple Moving Average (SMA)
def calculate_sma(data, window=5):
    """Calculate the Simple Moving Average (SMA) for the given data."""
    return data['Price'].rolling(window=window).mean()

# Function to update the chart
def update_chart(fig, new_data_call, new_data_put, new_data_index):
    fig.data = []  # Clear previous traces
    fig.add_trace(go.Scatter(x=new_data_call.index, y=new_data_call['Price'], mode='lines', name='Call Data'), row=1, col=1)
    fig.add_trace(go.Scatter(x=new_data_put.index, y=new_data_put['Price'], mode='lines', name='Put Data'), row=1, col=1)
    fig.add_trace(go.Scatter(x=new_data_index.index, y=new_data_index['Price'], mode='lines', name='Index Data'), row=2, col=1)
    
    sma_call = calculate_sma(new_data_call)
    sma_put = calculate_sma(new_data_put)
    print("call")
    print(sma_call)
    print("put")
    print(sma_put)
    # Save SMA data to CSV files
    if not sma_call.empty:
        latest_sma_call = sma_call.dropna().iloc[-1:]
        latest_sma_call.to_csv('sma_call.csv', header=['SMA_Call'], mode='w', index_label='Timestamp')

    if not sma_put.empty:
        latest_sma_put = sma_put.dropna().iloc[-1:]
        latest_sma_put.to_csv('sma_put.csv', header=['SMA_Put'], mode='w', index_label='Timestamp')

    fig.add_trace(go.Scatter(x=sma_call.index, y=sma_call, mode='lines', name='SMA Call', line=dict(color='blue')), row=1, col=1)
    fig.add_trace(go.Scatter(x=sma_put.index, y=sma_put, mode='lines', name='SMA Put', line=dict(color='black')), row=1, col=1)

    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="Price", row=2, col=1)
    
    return fig

# Function to raise alarm notification
def raise_alarm(previous_call_price, previous_put_price, current_call_price, current_put_price):
    if current_call_price > current_put_price and previous_call_price <= previous_put_price:
        print("ALARM: Call price has crossed Put price!")
    elif current_put_price > current_call_price and previous_put_price <= previous_call_price:
        print("ALARM: Put price has crossed Call price!")

# Event Handler Class
class ChartUpdateHandler(FileSystemEventHandler):
    def __init__(self, filenames, fig):
        super().__init__()
        self.filenames = filenames
        self.fig = fig
        self.previous_call_price = None
        self.previous_put_price = None

    

# Initial Data Processing and Chart Setup
call_data, latest_token_call = process_data('call_data.csv')
put_data, latest_token_put = process_data('put_data.csv')
index_data, latest_token_index = process_data('index_data.csv')

def on_modified(self, event):
    if event.src_path in self.filenames:
        logging.info(f"Files modified: {event.src_path}")
        new_data_call, latest_token_call = process_data('call_data.csv')
        new_data_put, latest_token_put = process_data('put_data.csv')
        new_data_index, latest_token_index = process_data('index_data.csv')
        
        if new_data_call.empty or new_data_put.empty or new_data_index.empty:
            logging.warning("One or more data files are empty or could not be processed.")
            return
        
        self.fig = update_chart(self.fig, new_data_call, new_data_put, new_data_index)
        self.fig.update_xaxes(range=[pd.Timestamp.now() - datetime.timedelta(hours=1), pd.Timestamp.now()])
        self.fig.write_html("line_chart.html")
        logging.info("Updated line_chart.html with latest data.")
        
        combined_data = pd.concat([new_data_call, new_data_put, new_data_index], axis=0)
        combined_data.to_csv("combined_data.csv")
        logging.info("Updated combined_data.csv with latest data.")

        # Check for alarm condition
        if self.previous_call_price is not None and self.previous_put_price is not None:
            current_call_price = new_data_call['Price'].iloc[-1]
            current_put_price = new_data_put['Price'].iloc[-1]
            raise_alarm(self.previous_call_price, self.previous_put_price, current_call_price, current_put_price)

        # Update previous prices
        self.previous_call_price = new_data_call['Price'].iloc[-1]
        self.previous_put_price = new_data_put['Price'].iloc[-1]



# Create subplots with shared x-axis
fig = make_subplots(rows=2, cols=1, shared_xaxes=True)
fig = update_chart(fig, call_data, put_data, index_data)

fig.update_layout(title='Token Price Line Chart',
                  xaxis_title='Date',
                  height=800,  # Increased height
                  width=1200)  # Increased width

fig.update_xaxes(range=[pd.Timestamp.now() - datetime.timedelta(hours=1), pd.Timestamp.now()])

fig.write_html("line_chart.html")

# File Watcher Setup
observer = Observer()
event_handler = ChartUpdateHandler(['call_data.csv', 'put_data.csv', 'index_data.csv'], fig)
observer.schedule(event_handler, path='.', recursive=False)
observer.start()

# Infinite Loop to Keep Observer Running
try:
    while True:
        # Update data every minute
        call_data, _ = process_data('call_data.csv')
        put_data, _ = process_data('put_data.csv')
        index_data, _ = process_data('index_data.csv')

        if call_data.empty or put_data.empty or index_data.empty:
            logging.warning("One or more data files are empty or could not be processed.")
            time.sleep(60)
            continue

        # Update chart
        fig = update_chart(fig, call_data, put_data, index_data)
        fig.update_xaxes(range=[pd.Timestamp.now() - datetime.timedelta(hours=6), pd.Timestamp.now()])
        fig.write_html("line_chart.html")

        # Refresh the HTML file every minute
        with open("line_chart.html", "w") as file:
            file.write("<!DOCTYPE html>\n")
            file.write("<html>\n")
            file.write("<head>\n")
            file.write("<meta http-equiv=\"refresh\" content=\"60\">\n")  # Refresh every 60 seconds
            file.write("</head>\n")
            file.write("<body>\n")
            file.write(fig.to_html(include_plotlyjs='cdn'))
            file.write("</body>\n")
            file.write("</html>")

        # Wait for 1 minute
        time.sleep(60)
        
except KeyboardInterrupt:
    observer.stop()
observer.join()

