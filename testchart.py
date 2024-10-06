import pandas as pd
import plotly.graph_objs as go
from plotly.subplots import make_subplots
import time
import datetime
import oracledb
import logging
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler("trading_app.log"), logging.StreamHandler()])

# Dash app setup
app = dash.Dash(__name__)

def connect_to_db(username, password, dsn):
    try:
        connection = oracledb.connect(user=username, password=password, dsn=dsn)
        logging.info("Connected to the database.")
        return connection
    except oracledb.Error as e:
        logging.error(f"Error connecting to the database: {e}")
        return None

def create_db_pool(username, password, dsn, min_connections=1, max_connections=5):
    try:
        pool = oracledb.create_pool(
            user=username,
            password=password,
            dsn=dsn,
            min=min_connections,  # Minimum number of connections in the pool
            max=max_connections,   # Maximum number of connections in the pool
            increment=1            # Number of connections to add to the pool as needed
        )
        logging.info("Database connection pool created.")
        return pool
    except oracledb.Error as e:
        logging.error(f"Error creating database connection pool: {e}")
        return None

def close_db_pool(pool):
    if pool:
        try:
            pool.close()
            logging.info("Database connection pool closed.")
        except oracledb.Error as e:
            logging.error(f"Error closing connection pool: {e}")

def detect_crossover(df, min_duration=6):
    crossovers = []
    above_sma = False
    start_time = None

    for time_stamp, row in df.iterrows():
        price = row['PRICE']
        sma = row['SMA_10_MIN']

        if not above_sma and price > sma:
            above_sma = True
            start_time = time_stamp
        elif above_sma and price < sma:
            above_sma = False
            start_time = None
        
        if above_sma and start_time:
            time_diff = (time_stamp - start_time).total_seconds() / 60
            if time_diff >= min_duration:
                crossovers.append(start_time)
                above_sma = False
                start_time = None

    return crossovers

def fetch_last_available_record(cursor, table_name):
    query = f"""
    SELECT token, time_stamp
    FROM {table_name}
    ORDER BY time_stamp DESC
    FETCH FIRST 1 ROWS ONLY
    """
    cursor.execute(query)
    row = cursor.fetchone()
    if not row:
        logging.info(f"No data available in table {table_name}.")
        return None, None
    token, time_stamp = row
    return token, time_stamp
def create_table_if_not_exists(cursor, table_name):
    try:
        # Check if the table exists by querying Oracle's user_tables
        cursor.execute(f"""
        SELECT table_name 
        FROM user_tables 
        WHERE table_name = UPPER(:table_name)
        """, {'table_name': table_name.upper()})
        table = cursor.fetchone()
        
        if not table:
            # Create the table if it doesn't exist
            cursor.execute(f"""
            CREATE TABLE {table_name} (
                time_stamp TIMESTAMP PRIMARY KEY,
                sma_value NUMBER
            )
            """)
            logging.info(f"Table {table_name} created successfully.")
        else:
            logging.info(f"Table {table_name} already exists.")
    except oracledb.Error as e:
        logging.error(f"Error creating table {table_name}: {e}")

def insert_sma_value(cursor, table_name, time_stamp, sma_value):
    try:
        # Check if the time_stamp already exists
        cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE time_stamp = :time_stamp", {'time_stamp': time_stamp})
        count = cursor.fetchone()[0]
        
        if count == 0:
            # If no existing row, insert the new row
            insert_query = f"""
            INSERT INTO {table_name} (time_stamp, sma_value)
            VALUES (:time_stamp, :sma_value)
            """
            cursor.execute(insert_query, {'time_stamp': time_stamp, 'sma_value': sma_value})
            logging.info(f"Inserted SMA value into {table_name}: {sma_value} at {time_stamp}")
        else:
            logging.info(f"Skipped insert for {table_name}, record already exists for time_stamp {time_stamp}")
    except oracledb.Error as e:
        logging.error(f"Error inserting SMA data into {table_name}: {e}")


def fetch_data_for_token_and_date(cursor, table_name, token, time_stamp):
    query = f"""
    SELECT token, price, time_stamp, oi,
           AVG(price) OVER (
               PARTITION BY token
               ORDER BY time_stamp
               RANGE BETWEEN INTERVAL '22' MINUTE PRECEDING AND CURRENT ROW
           ) AS sma_10_min
    FROM {table_name}
    WHERE token = :token
    AND time_stamp >= TRUNC(:time_stamp)
    AND time_stamp < TRUNC(:time_stamp) + INTERVAL '1' DAY
    ORDER BY time_stamp ASC
    """
    cursor.execute(query, {'token': token, 'time_stamp': time_stamp})
    rows = cursor.fetchall()
    if not rows:
        logging.info(f"No data available for token {token} on the same date as {time_stamp}.")
        return pd.DataFrame()
    df = pd.DataFrame(rows, columns=['TOKEN', 'PRICE', 'TIME_STAMP', 'OI', 'SMA_10_MIN'])
    df['TIME_STAMP'] = pd.to_datetime(df['TIME_STAMP'])
    df.set_index('TIME_STAMP', inplace=True)
    return df

def update_chart_with_sma(call_data, put_data):
    fig = make_subplots(rows=1, cols=1)
    
    # Plot Call Data
    if not call_data.empty:
        fig.add_trace(go.Scatter(x=call_data.index, y=call_data['PRICE'], mode='lines', name='Call Price', line=dict(color='blue')))
        if 'SMA_10_MIN' in call_data.columns:
            fig.add_trace(go.Scatter(x=call_data.index, y=call_data['SMA_10_MIN'], mode='lines', name='Call SMA 10 Min'))

        # Detect and mark crossovers on the chart
        call_crossovers = detect_crossover(call_data)
        for crossover_time in call_crossovers:
            # Plot an upward arrow at the crossover
            crossover_price = call_data.loc[crossover_time, 'PRICE']
            fig.add_trace(go.Scatter(
                x=[crossover_time], 
                y=[crossover_price],
                mode='markers',
                marker=dict(size=15, color='green', symbol='triangle-up'),
                name='Call Crossover'
            ))

    # Plot Put Data
    if not put_data.empty:
        fig.add_trace(go.Scatter(x=put_data.index, y=put_data['PRICE'], mode='lines', name='Put Price', line=dict(color='red')))
        if 'SMA_10_MIN' in put_data.columns:
            fig.add_trace(go.Scatter(x=put_data.index, y=put_data['SMA_10_MIN'], mode='lines', name='Put SMA 10 Min'))

        # Detect and mark crossovers on the chart
        put_crossovers = detect_crossover(put_data)
        for crossover_time in put_crossovers:
            # Plot a downward arrow at the crossover
            crossover_price = put_data.loc[crossover_time, 'PRICE']
            fig.add_trace(go.Scatter(
                x=[crossover_time], 
                y=[crossover_price],
                mode='markers',
                marker=dict(size=15, color='orange', symbol='triangle-down'),
                name='Put Crossover'
            ))

    # Update the chart layout
    fig.update_layout(
        title='Token Price Line Chart (Call and Put)', 
        xaxis_title='Date', 
        height=600, 
        width=1000
    )
    
    return fig

def fetch_and_update_data(pool):
    connection = None  # Initialize the connection variable to None
    try:
        # Try to acquire a connection from the pool
        connection = pool.acquire()
        cursor = connection.cursor()

        # Check and create sma_call and sma_put tables if they don't exist
        create_table_if_not_exists(cursor, 'sma_call')
        create_table_if_not_exists(cursor, 'sma_put')
        
        # Fetch the last available records for both call and put
        call_token, call_time_stamp = fetch_last_available_record(cursor, 'call_data')
        put_token, put_time_stamp = fetch_last_available_record(cursor, 'put_data')
        
        # Check if we have valid tokens and timestamps
        if not call_token or not call_time_stamp:
            logging.error("No last available data for call token.")
            return pd.DataFrame(), pd.DataFrame()

        if not put_token or not put_time_stamp:
            logging.error("No last available data for put token.")
            return pd.DataFrame(), pd.DataFrame()

        # Fetch the data for the given token and timestamp
        call_data = fetch_data_for_token_and_date(cursor, 'call_data', call_token, call_time_stamp)
        put_data = fetch_data_for_token_and_date(cursor, 'put_data', put_token, put_time_stamp)

        # Insert the most recent SMA values into the sma_call and sma_put tables
        if not call_data.empty:
            latest_sma_call = call_data.iloc[-1]['SMA_10_MIN']
            latest_call_time = call_data.index[-1]
            insert_sma_value(cursor, 'sma_call', latest_call_time, latest_sma_call)

        if not put_data.empty:
            latest_sma_put = put_data.iloc[-1]['SMA_10_MIN']
            latest_put_time = put_data.index[-1]
            insert_sma_value(cursor, 'sma_put', latest_put_time, latest_sma_put)

        connection.commit()  # Commit the transaction
        return call_data, put_data

    except oracledb.Error as e:
        logging.error(f"Database error: {e}")
        return pd.DataFrame(), pd.DataFrame()

    finally:
        # Only release the connection if it was successfully acquired
        if connection is not None:
            try:
                pool.release(connection)
            except oracledb.Error as release_error:
                logging.error(f"Error releasing the connection: {release_error}")



# Database credentials
username = "MAI1"
password = "calypso"
dsn = "localhost:1521/CALYPSO"

# Initialize the connection pool
pool = create_db_pool(username, password, dsn)

if pool:
    logging.info("Connection pool initialized and ready to use.")
else:
    logging.error("Failed to initialize the connection pool.")

# Set up the layout for the Dash app, with an interval for updates
app.layout = html.Div([
    dcc.Graph(id='line-chart'),
    dcc.Interval(id='interval-component', interval=30*1000, n_intervals=0),  # 30 seconds
    html.Div(id='output-div')
])

# Callback to update the chart every 30 seconds
@app.callback(
    [Output('line-chart', 'figure'),
     Output('output-div', 'children')],  # Output div for notifications
    [Input('interval-component', 'n_intervals')]
)
def update_graph(n):
    # Fetch the latest data and update the chart
    call_data, put_data = fetch_and_update_data(pool)

    # Detect crossovers for notifications
    call_crossovers = detect_crossover(call_data)
    put_crossovers = detect_crossover(put_data)
    
    # Generate a notification message if there are crossovers
    notification = []
    if call_crossovers:
        for crossover_time in call_crossovers:
            notification.append(f"Call crossover detected at {crossover_time}.")
    if put_crossovers:
        for crossover_time in put_crossovers:
            notification.append(f"Put crossover detected at {crossover_time}.")
    
    if not notification:
        notification = ["No crossovers detected."]

    # Update the chart
    fig = update_chart_with_sma(call_data, put_data)
    return fig, html.Div(notification)

if __name__ == '__main__':
    try:
        app.run_server(debug=True)
    finally:
        close_db_pool(pool)  # Ensure the pool is closed when the server is stopped