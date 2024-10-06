

# -*- coding: utf-8 -*-
"""
Created on Fri Mar 29 01:49:27 2024

@author: SaurabhGaur
"""
import pandas as pd
import json
import logging
import yaml
from api_helper import ShoonyaApiPy
import os
import math
import pyotp
from datetime import datetime
import datetime
import requests
import zipfile
import threading
import time
from tkinter import messagebox
import logging
import queue
import oracledb

# Configure logging
logging.basicConfig(filename='monitor_stop_loss.log', level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')







class TradingSession2:
    def __init__(self, update_gui_callback=None,update_ltp_callback=None, config_path1='cred1.yml'):
        self.BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        self.config_path1 = os.path.join(self.BASE_DIR, config_path1)
        #self.config_path2 = os.path.join(self.BASE_DIR, config_path2)
        self.update_gui_callback = update_gui_callback
        self.api = ShoonyaApiPy()
        self.cumulative_pnl = 0
        self.total_orders = 0
        self.feed_opened = False
        self.is_logged_in = False
        self.connection = None
        self.cursor = None
        self.atm_strike = 0
        self.BN_indexLtp = 0
        self.expiry_date = None
        self.masters_file = 'NFO_symbols.txt'
        self.live_data = {}
        self.atm_call_token = None
        self.atm_put_token = None
        self.atm_call_ltp = 0
        self.atm_put_ltp = 0
        self.update_ltp_callback = update_ltp_callback
        self.expiry_date = None
        self.masters_file = 'NFO_symbols.txt'  # Assuming this file is in the same directory
        self.index_symbol="BANKNIFTY"
        self.is_logged_in = False
        self.banknifty_token = "26009"
        self.live_data = {}  # Initialize live_data
        self.atm_call_token = None
        self.atm_put_token = None
        self.strike_price=None
        self.update_gui_callback = update_gui_callback
        self.feed_opened = False
        self.__websocket_connected = False  # Initialize the attribute
        self.usersession_file = "user_session1.txt"
        #self.usersession_file2 = "user_session2.txt"
        self.CE_Ltp=0
        self.PE_Ltp=0
        self.option_tokens={}
        self.ce_token = None  # Example call option token
        self.pe_token = None # Example put option token
        self.pe_ltp=0
        self.ce_ltp=0
        self.ce_symbol=None
        self.pe_symbol=None
        self.current_stop_loss = 0
        self.ltp_dict = {}
        self.ltp_dict1 = {} # Dictionary to hold LTP for each token
        self.positions = {}
        self.stop_loss_value=0
        self.stop_loss_type=None
        self.stop_loss_price = 0.00
        self.stop_loss_enabled = False
        self.is_trailing=False
        self.lock = threading.Lock()  # Create a lock
        self.file_paths = {
           'index': 'index_ltp.csv',
           'call': 'call_ltp.csv',
           'put': 'put_ltp.csv'
       }
        self.data_queue = queue.Queue()
        self.running = True
        self.buysymbol=None
        self.position={}
        self.is_trailing = False
        self.trailing_trigger = 0.00
        self.trailing_move_type = 'percentage'
        self.trailing_move = 0.00
        self.trailing_enabled = False
        self.trailing_trigger_price=0.00
        self.trailing_move_price=0.00
        self.position_file = 'positions.json'
        self.trade_responses_file='trade_responses.json'
        self.stop_monitoring = False
        self.global_sma_call = None
        self.global_sma_put = None
        self.callorput=None
        self.variable=False
        self.setup_db_connection()
    def update_variable(self, value):
        """Update the variable value based on the checkbox state."""
        self.variable = value
        print('varia')
        print(self.variable)

    def setup_worker_threads(self):
        for _ in range(3):  # Example: three worker threads
            thread = threading.Thread(target=self.process_data_queue)
            thread.daemon = True
            thread.start()
    def generate_otp(self, totp_secret):
          totp = pyotp.TOTP(totp_secret)
          print(totp)
          return totp.now()
    def process_data_queue(self):
        while self.running:
            
            try:
                data_item = self.data_queue.get(timeout=3)  # Adjust as necessary
                if data_item is None:  # Shutdown signal
                    break
                self.write_data_to_file(data_item)
                self.data_queue.task_done()
            except queue.Empty:
                continue
    def write_positions_to_excel(self):
        df = pd.DataFrame(self.positions.values())

   # If file exists, read existing data and append new data
        if os.path.exists(self.position_file):
          existing_df = pd.read_excel(self.position_file)
          combined_df = pd.concat([existing_df, df], ignore_index=True)
          combined_df.to_excel(self.position_file, index=False)
        else:
         df.to_excel(self.position_file, index=False)
    def write_data_to_file(self, data_item):
     """
     Writes a single data item to the corresponding file based on its type.
     This method appends data to the end of the file without overwriting existing data.
     """
     token = data_item['token']
     ltp = data_item['ltp']
     timestamp = data_item['time']
     data_type = data_item['type']  # This could be 'index', 'call', or 'put'
    
     file_path = f"{data_type}_data.csv"
    
    # Using locking to ensure thread safety when multiple threads write to files
     with self.lock:
         try:
            # Open file in append mode, 'a' mode ensures that the file is created if it doesn't exist
            with open(file_path, 'a') as file:
                file.write(f"{token},{ltp},{timestamp}\n")
            
         except IOError as e:
            logging.error(f"Failed to write to file {file_path}: {e}")

    
# =============================================================================
#     def send_user_session_via_email(self, usersession):
#      """Sends the user session token via email."""
#      try:
#         sender_email = "your_email@gmail.com"
#         receiver_email = "receiver_email@gmail.com"
#         password = "your_email_password"
# 
#         message = MIMEMultipart()
#         message["From"] = sender_email
#         message["To"] = receiver_email
#         message["Subject"] = "User Session Token"
# 
#         body = f"User session token: {usersession}"
#         message.attach(MIMEText(body, "plain"))
# 
#         server = smtplib.SMTP("smtp.gmail.com", 587)
#         server.starttls()
#         server.login(sender_email, password)
#         text = message.as_string()
#         server.sendmail(sender_email, receiver_email, text)
#         server.quit()
# 
#         logging.info("User session sent via email successfully.")
#      except Exception as e:
#         logging.error(f"Failed to send user session via email: {e}")
# =============================================================================
    def is_websocket_connected(self):
        return self.__websocket_connected
    def check_and_initiate_connection(self):
    # First, check if the session is already active
     if self.is_session_active():
        print("Session is already active.")
        return True
     else:
        # If the session is not active, attempt to establish a new connection
        try:
            self.load_and_login()
            print("Logged in successfully.")
            
            # Optionally, you could double-check if the session is now active after login
            if self.is_session_active():
                print("Session is active after login.")
                return True
            else:
                print("Failed to activate session after login.")
                return False
        except Exception as e:
            print(f"Failed to log in: {e}")
            return False
     
       
    def get_time_price_series(self, exchange, token, starttime, endtime, interval):
    
    # Setting up basic configuration for logging
         logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
     
         try:
             response = self.api.get_time_price_series(exchange, token, starttime, endtime, interval)
             
             logging.debug("API nse)Response: %s", response)  # Logging the response for debugging
             response_str_corrected = response.replace("} {", "}, {")
             # The response is a string representation of a list of dictionaries, but without commas between dicts.
             data_list_str = f"[{response_str_corrected}]"
             from ast import literal_eval

             try:
                 data_list = literal_eval(data_list_str)
             except SyntaxError as e:
                 raise ValueError(f"Response string could not be parsed into a list of dictionaries: {e}")

             # Process each dictionary and correct the keys
             data_processed = []
             for item in data_list:
                 if item.get('stat') == 'Ok':
                     data_processed.append({
                         'time': item.get('time'),
                         'open': item.get('into'),  # Using the original keys from the provided response
                         'high': item.get('inth'),
                         'low': item.get('intl'),
                         'close': item.get('intc'),
                         'volume': item.get('intv'),
                         'vwap': item.get('intvwap')
                     })

             # Now we write the processed data to a file
             file_path = r'C:\Users\SaurabhGaur\processed_data.txt'

             with open(file_path, 'w') as file:
                 for entry in data_processed:
                     file.write(str(entry) + '\n')

             file_path  # Return the path to the written file for the user to download

         except Exception as e:
          print(f"Failed to log in: {e}")
    
    def handle_price_update(self, token, new_price):
     """
     Handle new price updates for tokens and check stop loss conditions.
    
    Args:
    token (str): The token identifier for which the price update has occurred.
    new_price (float): The new trading price of the token.
    """
    # Update the latest price in the dictionary
     self.ltp_dict[token] = new_price

     # Check and execute stop loss if active
     if token in self.positions and self.positions[token]['stop_loss_active']:
        self.check_and_execute_stop_loss(token, new_price)
        
    def is_session_active(self):
        
     
          try:
              
              if self.is_logged_in==True:
               print("Session is active.")
               print(self.is_logged_in)
               return True
              else:
                print("Session check failed. Session is not active.")
                print(self.is_logged_in)
                return False
          except Exception as e:
            print(f"Error checking session status: {e}")
            return False   
    def save_user_session(self, usersession):
        """Saves the user session token to a file."""
        try:
           with open("user_session1.txt", "w") as file:
              file.write(usersession)
              
           logging.info("User session saved successfully.")
        except Exception as e:
           logging.error(f"Failed to save user session: {e}")
    
    def place_buy_call_order(self, buy_or_sell, product_type, exchange, tradingsymbol, quantity, discloseqty, price_type, price, trigger_price, retention, remarks):
    # Assuming 'CANBK-EQ' is replaced with your call option symbol
       # This should be dynamically determined, perhaps stored in self.trading_session.ce_token
       
       try:
           ret = self.api.place_order(
            buy_or_sell='B',
            product_type='I',  # Assuming 'C' for calls, but check your API. Might need to be 'OPT' or similar.
            exchange='NFO',
            tradingsymbol=self.call_symbol,
            quantity=4*quantity,  # Or more, depending on your strategy
            discloseqty=0,
            price_type='MKT',  # For a market order
            price=0,  # For market orders, price might be set to 0 or not set depending on the API
            trigger_price=None,  # Not applicable for market orders
            retention='DAY',
            remarks='buy_call_market_order'
            )
           if ret['stat'] == 'Ok':   
              order_no = ret['norenordno']
              
              time.sleep(1)
              self.store_order_details(order_no)
              print('store')
              # and ret.get('fillshares')==quantity==ret.get('qty')
           else:
             print(f"Failed to place buy order for {tradingsymbol}: {ret.get('emsg', 'No error message available')}")
             
       except Exception as e:
          print(f"Failed to place order: {e}") 
           # Log or handle the response appropriately
    def store_order_details(self, order_no):

     try:
         
         trade_responses = self.api.get_trade_book()
         
         i=0
         for trade_response in trade_responses:
            
            logging.info('Processing order')
            try:
                # Directly accessing dictionary keys
                tradeorder = trade_response['norenordno']
                print(tradeorder)
                logging.info(f"Order number: {tradeorder}")
                
# =============================================================================
#                 mode = 'a' if os.path.exists(self.trade_responses_file) else 'w'
#                 with open(self.trade_responses_file, mode) as f:
#                  json.dump(trade_responses, f)
# =============================================================================
                #print(trade_response)
                if tradeorder == order_no and (trade_response['qty']==trade_response['fillshares']) and trade_response['trantype']=='B':
                    symbol = trade_response['tsym']
                    print('summ')
                    print(trade_response['tsym'])
                    
                    fill_price = trade_response['avgprc']
                    filled_quantity = trade_response['fillshares']
                    SL=0
                    self.current_stop_loss
                    # Store or update the trade details
                    current_price=float(self.fetch_current_price(symbol))
                                        
                    self.positions[order_no] = {
                           'symbol': symbol,
                           'filled_price': fill_price,
                           'quantity': filled_quantity,
                           'stop_loss_active': self.stop_loss_enabled,
                           'stop_loss_price': SL,
                           'Entry/Exit': 'Entry',
                           'Orderno': order_no,
                           'stop_loss_type': self.stop_loss_type,
                           'stop_loss_value': self.stop_loss_value,
                           'is_trailing': self.is_trailing,
                           'trailing_trigger': self.trailing_trigger,
                           'trailing_move_type': self.trailing_move_type,
                           'trailing_move': self.trailing_move,
                           'trailing_enabled': self.trailing_enabled,
                           'stop_loss_enabled': self.stop_loss_enabled,
                           'trailing_trigger_price': self.trailing_trigger_price,
                           'trailing_move_price': self.trailing_move_price,
                           'variable': self.variable  # Add this line
                       }
                    #self.write_positions_to_excel()
                  
                    # Open positions file in append mode if it exists, otherwise in write mode
                   
                    
                    
                    print(self.positions[order_no])
                    if self.set_stop_loss(order_no) :
                       self.set_trailing_stop_loss(order_no)
                       print('stoploss')
                       print( self.positions)
                       self.start_monitoring_stop_loss(order_no)
                    else:
                        print('stop_loss not enabled')
                  

                        
                else:
                    print('condition not met so showing trade book')
                    print('order is not availabe in trade book')
                   
                    
                  
            except KeyError as e:
                print(f"Key {e} missing in response for order number {order_no}, cannot process this order response.")

     except Exception as e:
        print(f"Error processing order details: {e}")
   



    def setup_db_connection(self):
        """
        Establishes a connection to the Oracle database.
        """
        try:
            self.connection = oracledb.connect(
                user="MAI1",
                password="calypso",
                dsn="localhost:1521/CALYPSO"
            )
            self.cursor = self.connection.cursor()
            logging.info("Successfully connected to the Oracle database")
            return self.connection
        except oracledb.Error as e:
            logging.error(f"Error connecting to the database: {e}")
            raise

    def close_db_connection(self):
        """
        Closes the database connection.
        """
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
            logging.info("Database connection closed")
    
    def read_sma_values(self):
   
     try:
        # Check if connection is established
        if not self.connection:
            raise ValueError("Database connection is not initialized")

        # Use a single cursor to execute both queries
        with self.connection.cursor() as cursor:
            
            # Fetch SMA value for call
            call_query = """
            SELECT SMA_VALUE, TIME_STAMP
            FROM sma_call
            ORDER BY TIME_STAMP DESC
            FETCH FIRST 1 ROWS ONLY
            """
            cursor.execute(call_query)
            call_result = cursor.fetchone()

            if call_result:
                self.sma_call = call_result[0]  # SMA_VALUE
                logging.info(f"Loaded SMA Call value: {self.sma_call} at {call_result[1]}")
            else:
                self.sma_call = None  # Consider using None if no data is available
                logging.warning("No SMA Call data found in the database.")

            # Fetch SMA value for put
            put_query = """
            SELECT SMA_VALUE, TIME_STAMP
            FROM sma_put
            ORDER BY TIME_STAMP DESC
            FETCH FIRST 1 ROWS ONLY
            """
            cursor.execute(put_query)
            put_result = cursor.fetchone()

            if put_result:
                self.sma_put = put_result[0]  # SMA_VALUE
                logging.info(f"Loaded SMA Put value: {self.sma_put} at {put_result[1]}")
            else:
                self.sma_put = None  # Consider using None if no data is available
                logging.warning("No SMA Put data found in the database.")

     except oracledb.Error as e:
        logging.error(f"Error reading SMA values from the database: {e}")
        self.sma_call = None
        self.sma_put = None

     except ValueError as ve:
        logging.error(f"ValueError: {ve}")
        self.sma_call = None
        self.sma_put = None


    def monitor_stop_loss(self, order_no):
       try:
           while True:
               position = self.positions.get(order_no)
               timestamp = pd.Timestamp.now()
               logging.info(f"Timestamp: {timestamp} - Monitoring stop loss for order {order_no}")

               if not position or not position['stop_loss_active']:
                   logging.info(f"Monitoring stopped for {order_no}. Position not found or stop loss not active.")
                   break

               current_price = float(self.fetch_current_price(position['symbol']))
               self.read_sma_values()

               if '24C' in position['symbol']:
                   logging.info('Handling Call Option')
                   sma_value = float(self.sma_call)
               elif '24P' in position['symbol']:
                   logging.info(f"Handling Put Option {position['symbol']}" )
                   sma_value = float(self.sma_put)
                   
               else:
                   logging.error(f"Invalid symbol in position: {position['symbol']}")
                   break
               print(sma_value)
               if position['variable']:
                  effective_stop_loss = float(max(position.get('stop_loss_price', float('inf')), sma_value))
               else:
                  effective_stop_loss = float(min(position.get('stop_loss_price', float('inf')), sma_value))
               logging.info(f"Effective stop loss for order {order_no}: {effective_stop_loss}")
               logging.info(f"Current price for {position['symbol']}: {current_price}")
               logging.debug(f"Type of current_price: {type(current_price)}, Value: {current_price}")
               logging.debug(f"Type of effective_stop_loss: {type(effective_stop_loss)}, Value: {effective_stop_loss}")

               if self.should_execute_stop_loss(position, current_price, effective_stop_loss):
                   logging.warning(f"Executing stop loss for {order_no}. Current price {current_price} is below stop loss price {effective_stop_loss}.")
                   self.execute_sell_order(position['symbol'], position['quantity'])
                   position['stop_loss_enabled'] = False
                   position['trailing_enabled'] = False
                   position['Entry/Exit'] = 'Exit'
                   logging.info(f"Both regular stop loss and trailing stop loss disabled for {order_no} after execution.")
                   break
               else:
                   print('price above stop loss')
                   logging.warning(f"price above stop loss for {order_no}. Current price {current_price} is above stop loss price {effective_stop_loss}.")
                   self.handle_trailing_stop_loss(position, current_price, effective_stop_loss, order_no)

       except Exception as e:
           logging.error(f"Error monitoring stop loss for order {order_no}: {e}")

    def should_execute_stop_loss(self, position, current_price, effective_stop_loss):
       if position['stop_loss_enabled'] and not position['trailing_enabled'] and position['Entry/Exit'] == 'Entry':
           if not position['variable'] and current_price <  position.get('stop_loss_price', float('inf')):
               return True
           if position['variable'] and current_price < position.get('stop_loss_price', float('inf')):
               return True
       elif position['stop_loss_enabled'] and  position['trailing_enabled'] and position['Entry/Exit'] == 'Entry':
            if  current_price < effective_stop_loss:
                return True
            
            
       else:
           return False

    def handle_trailing_stop_loss(self, position, current_price, effective_stop_loss, order_no):
       if position['trailing_enabled'] and position['stop_loss_enabled'] and position['Entry/Exit'] == 'Entry':
           if current_price < effective_stop_loss:
               logging.warning(f"Executing stop loss for {order_no}. Current price {current_price} is below stop loss price {effective_stop_loss}.")
               self.execute_sell_order(position['symbol'], position['quantity'])
               position['stop_loss_enabled'] = False
               position['trailing_enabled'] = False
               position['Entry/Exit'] = 'Exit'
               logging.info(f"Both regular stop loss and trailing stop loss disabled for {order_no} after execution.")
           elif current_price > effective_stop_loss:
               logging.warning(f"Price above stop loss for {order_no}. Current price {current_price} is above stop loss price {effective_stop_loss}.")
               if current_price < position.get('trailing_trigger_price', float('inf')):
                   logging.warning(f"Price above stop loss but not triggered yet for {order_no}. Current price {current_price} is above stop loss price {effective_stop_loss}.")
               elif current_price > position.get('trailing_trigger_price', float('inf')):
                   # Initialize new stop loss and trailing trigger prices
                   new_stop_loss_price = position.get('stop_loss_price', float('inf'))
                   new_trailing_trigger_price = position.get('trailing_trigger_price', float('inf'))

                   # Check if the trailing move type is "percentage"
                   if position['trailing_move_type'].lower() == "percentage":
                       # Calculate new stop loss price based on the current price and stop loss value percentage
                       new_stop_loss_price = current_price * (1 - (position.get('stop_loss_value', float('inf')) / 100))
                       # Calculate new trailing trigger price based on the current trailing trigger price and trailing move percentage
                       new_trailing_trigger_price = position.get('trailing_trigger_price', float('inf')) * (1 + position.get('trailing_move', float('inf')) / 100)

                   # Update stop loss price if the new stop loss price is greater than the current stop loss price
                   if new_stop_loss_price > position['stop_loss_price']:
                       logging.debug(f"Before updating: stop_loss_price = {position['stop_loss_price']}, new_stop_loss_price = {new_stop_loss_price}")
                       position['stop_loss_price'] = new_stop_loss_price

                   # Update trailing trigger price if the new trailing trigger price is greater than the current trailing trigger price
                   if new_trailing_trigger_price > position['trailing_trigger_price']:
                       logging.debug(f"Before updating: trailing_trigger_price = {position['trailing_trigger_price']}, new_trailing_trigger_price = {new_trailing_trigger_price}")
                       position['trailing_trigger_price'] = new_trailing_trigger_price
                       logging.info(f"Updated trailing stop loss for {order_no} to {new_stop_loss_price}")
                       logging.debug(f"After updating: stop_loss_price = {position['stop_loss_price']}")



   


    def start_monitoring_stop_loss(self, order_no):
        print('inside start stop')
        print(order_no)
                 
        thread = threading.Thread(target=self.monitor_stop_loss, args=(order_no,))
        thread.start()
        
        logging.info(f"Started monitoring stop loss for order {order_no}.")
        mode = 'a' if os.path.exists(self.position_file) else 'w'
        with open(self.position_file, mode) as f:
         json.dump(self.positions, f)
     
    def fetch_current_price(self, symbol):
        logging.info(f"Fetching current price for symbol: {symbol}")
        if symbol == self.call_symbol:
            logging.info(f"Current price for {symbol} (CALL): {self.ce_ltp}")
            return self.ce_ltp
        elif symbol == self.put_symbol:
            logging.info(f"Current price for {symbol} (PUT): {self.pe_ltp}")
            return self.pe_ltp
        else:
            logging.error("No matching symbol found for current price fetch.")
            return 0


    

    

    def set_stop_loss(self, order_no):
     logging.debug('Inside stop loss')
     try:
        trade = self.positions.get(order_no)
        if trade is None:
            raise KeyError(f"No trade found with order number: {order_no}")

        filled_price = float(trade['filled_price'])
        
        # Check if stop loss is enabled
        if self.stop_loss_enabled:
            if self.stop_loss_type.lower() == "absolute":
                computed_stop_loss = filled_price - self.stop_loss_value
            elif self.stop_loss_type.lower() == "percentage":
                
                computed_stop_loss = filled_price * (1 - self.stop_loss_value / 100)
            else:
                raise ValueError("Unsupported stop loss type. Use 'absolute' or 'percentage'.")

            trade['stop_loss_price'] = computed_stop_loss
            trade['stop_loss_type'] = self.stop_loss_type
            trade['stop_loss_value'] = self.stop_loss_value

            logging.info(f"Stop loss set for order {order_no}: {computed_stop_loss}")
            return True
        else:
            # Stop loss is not enabled, return without setting it
            return False

     except KeyError as e:
        logging.error(f"Error: {e}")
        return False
     except ValueError as e:
        logging.error(f"Error: {e}")
        return False
     except Exception as e:
        logging.error(f"An unexpected error occurred: {str(e)}")
        return False

    def set_trailing_stop_loss(self, order_no):
     try:
        trade = self.positions.get(order_no)
        
        if trade is None:
            raise KeyError(f"No trade found with order number: {order_no}")
            print(trade)
        current_price = float(self.fetch_current_price(trade['symbol']))
        print('current')
        print(current_price)
        filled_price = float(trade['filled_price'])

        if self.trailing_enabled and self.stop_loss_enabled and self.trailing_trigger and self.trailing_move:
            if self.trailing_move_type.lower() == "absolute":
                # Calculate trailing trigger price based on absolute value
                trailing_trigger_price = current_price + self.trailing_trigger
                
            elif self.trailing_move_type.lower() == "percentage":
                print('inside percentage trigger')
                # Calculate trailing trigger price based on percentage
                trailing_trigger_price = current_price * (1 + self.trailing_trigger / 100)
                print(trailing_trigger_price) 
            else:
                raise ValueError("Unsupported trailing move type. Use 'absolute' or 'percentage'.")
                
            # Calculate trailing move price from the trailing trigger price
            if self.trailing_move_type.lower() == "percentage":
                trailing_move_price = trade['stop_loss_price'] * (1 + self.trailing_move / 100)
                
            elif self.trailing_move_type.lower() == "absolute":
                trailing_move_price = trade['stop_loss_price'] + self.trailing_move
                
            # Update trade dictionary with trailing trigger price and trailing move price
            trade['trailing_trigger_price'] = trailing_trigger_price
            trade['trailing_move_price'] = trailing_move_price

            logging.info(f"Trailing stop loss set for order {order_no}: Trigger = {trailing_trigger_price}, Move = {trailing_move_price}")
            return True
        else:
            logging.info(f"Trailing stop loss not set for order {order_no}: is_trailing={self.is_trailing}, trailing_trigger={self.trailing_trigger}, trailing_move={self.trailing_move}.")
            return False

     except KeyError as e:
        logging.error(f"Error: {e}")
        return False
     except ValueError as e:
        logging.error(f"Error: {e}")
        return False
     except Exception as e:
        logging.error(f"An unexpected error occurred: {str(e)}")
        return False



   

    


   
    def execute_sell_order(self, symbol, quantity):
        try:
          
          print(symbol)
          print(quantity)
          ret = self.api.place_order(
              buy_or_sell='S',
              product_type='I',
              exchange='NFO',
              tradingsymbol=symbol,
              quantity=quantity,
              discloseqty=0,
              price_type='MKT',
              price=0,
              retention='DAY',
              remarks='executing_stop_loss'
          )
          print(ret['stat'])
          
        except Exception as e:
          print(f"Failed to place order: {e}")
          # Log or handle the response appropriately

          """Executes a sell order for the given quantity."""
    # Placeholder for sell order logic
          print(f"Executing market sell for {quantity} unit.")
    # Implement the actual selling logic with the trading API here

    def place_sell_call_order(self, buy_or_sell, product_type, exchange, tradingsymbol, quantity, discloseqty, price_type, price, trigger_price, retention, remarks):
  # Assuming 'CANBK-EQ' is replaced with your call option symbol
     # This should be dynamically determined, perhaps stored in self.trading_session.ce_token
       print('sell;')
       try:
         ret = self.api.place_order(
          buy_or_sell='S',
          product_type='I',  # Assuming 'C' for calls, but check your API. Might need to be 'OPT' or similar.
          exchange='NFO',
          tradingsymbol=self.call_symbol,
          quantity=4*quantity,  # Or more, depending on your strategy
          discloseqty=0,
          price_type='MKT',  # For a market order
          price=0,  # For market orders, price might be set to 0 or not set depending on the API
          trigger_price=None,  # Not applicable for market orders
          retention='DAY',
          remarks='put_call_market_order'      
          )
         if ret.get('stat') == 'Ok':
              self.store_trade_details(tradingsymbol, ret)
              print(f"Buy order successfully placed for {tradingsymbol}")
         else:
              print(f"Failed to place buy order for {tradingsymbol}: {ret.get('emsg', 'No error message available')}")
              print("Order response:", ret)  # Log or handle the response appropriately
       except Exception as e:
        print(f"Failed to place order: {e}")  # Exception handling for API call failure
    def place_buy_put_order(self, buy_or_sell, product_type, exchange, tradingsymbol, quantity, discloseqty, price_type, price, trigger_price, retention, remarks):
     # Assuming 'CANBK-EQ' is replaced with your call option symbol
        # This should be dynamically determined, perhaps stored in self.trading_session.ce_token
        
        try:
            ret = self.api.place_order(
             buy_or_sell='B',
             product_type='I',  # Assuming 'C' for calls, but check your API. Might need to be 'OPT' or similar.
             exchange='NFO',
             tradingsymbol=self.put_symbol,
             quantity=4*quantity,  # Or more, depending on your strategy
             discloseqty=0,
             price_type='MKT',  # For a market order
             price=0,  # For market orders, price might be set to 0 or not set depending on the API
             trigger_price=None,  # Not applicable for market orders
             retention='DAY',
             remarks='buy_put_market_order'
             )
            if ret['stat'] == 'Ok':   
               order_no = ret['norenordno']
               time.sleep(1)
               self.store_order_details(order_no)
               # and ret.get('fillshares')==quantity==ret.get('qty')
            else:
              print(f"Failed to place buy order for {tradingsymbol}: {ret.get('emsg', 'No error message available')}")
              
        except Exception as e:
           print(f"Failed to place order: {e}") 
            # Log or handle the response appropriately
     
    def place_sell_put_order(self, buy_or_sell, product_type, exchange, tradingsymbol, quantity, discloseqty, price_type, price, trigger_price, retention, remarks):
         # Assuming 'CANBK-EQ' is replaced with your call option symbol
           # This should be dynamically determined, perhaps stored in self.trading_session.ce_token
          
           try:
               ret = self.api.place_order(
                buy_or_sell='S',
                product_type='I',  # Assuming 'C' for calls, but check your API. Might need to be 'OPT' or similar.
                exchange='NFO',
                tradingsymbol=self.put_symbol,
                quantity=4*quantity,  # Or more, depending on your strategy
                discloseqty=0,
                price_type='MKT',  # For a market order
                price=0,  # For market orders, price might be set to 0 or not set depending on the API
                trigger_price=None,  # Not applicable for market orders
                retention='DAY',
                remarks='put_call_market_order'
            )
               if ret.get('stat') == 'Ok':
                    order_no = ret.get('norenordno')
            # Fetch trade details after a small delay to ensure the trade is booked
               trade_details = self.api.get_trade_book()  # Assuming no parameters needed
               self.process_trade_details(tradingsymbol, order_no, trade_details)
           except Exception as e:
            print(f"Failed to place order: {e}")
    
    
        
    def standard_login(self):
        """
        Attempts to load credentials and log into the trading session.
        print('standard login)"""
        try:
            with open(self.config_path1, 'r') as f:
                cred = yaml.safe_load(f)
            print("Credentials loaded.")
            otp = self.generate_otp(cred['factor2'])
            print(otp)
            # Attempt to log in with the loaded credentials
            ret = self.api.login(userid=cred['user'], password=cred['pwd'], twoFA=otp,
                                 vendor_code=cred['vc'], api_secret=cred['apikey'], imei=cred['imei'])
            print(ret)
            if ret is not None:
                self.is_logged_in = True
                print("Connected to the API successfully!")
                # Perform any additional setup here
                self.usersession = ret["susertoken"]
                
                print(self.usersession)

                with open("user_session1.txt", "w") as file:
                  file.write(self.usersession)
                username = ret["uname"]
                #self.send_user_session_via_email(self.usersession)
                self.write_user_session_to_google_sheet(self.usersession)
                #log(f"Sucessfully Login to the account {username}")

                print("Welcome!")
                print("doenloadin")

            else:
                print("Connection to the API failed.")
                return False
        except Exception as e:
               print(f"Failed to load credentials and login: {e}")
               return False    
    
     
    # Assuming subscription to "NSE|26009" is elsewhere or handled before this call

    # Wait for the BANKNIFTY LTP update
     
    def read_user_session(self):
    
      
        """Reads the user session token from a file, if it exists."""
        try:
            with open(self.usersession_file, 'r') as f:
                usersession = f.read().strip()
            if usersession:
                logging.info("User session loaded successfully.")
                return usersession
            
        except FileNotFoundError:
            logging.info("No existing user session file found.")
        except Exception as e:
            logging.error(f"Error reading user session file: {e}")
        return None
           
    def login_with_session(self):
     """Sets the session with the API using the loaded user session token."""
     usersession = self.read_user_session()
     if usersession is not None:
        try:
            # Assuming you have an API client instance ready as `self.api`
            # The `set_session` method and parameters like 'userid', 'password' 
            # should be aligned with your API client's requirements.
            #ret = self.api.set_session(userid="FA294786", password="@Irtel10g", usertoken=usersession)
            ret = self.api.set_session(userid="FA171822", password="@Irtel14g", usertoken=usersession)
            #ret = self.api.set_session(userid="FA294786", password="@Irtel10g", usertoken=usersession)
            if ret:
                logging.info("API session set successfully with the user session token.")
                return True  # Assuming successful `set_session` returns a truthy value
            else:
                logging.error("Failed to set API session with the user session token.")
                return False
        except Exception as e:
            logging.error(f"Error setting API session: {e}")
            return False
     else:
        logging.error("No user session token available to set the API session.")
        return False
    def load_and_login(self):
        print('load and login)')
        """Attempts to log into the trading session, preferring to use an existing session token if available."""
        usersession = self.read_user_session()
        if usersession and self.login_with_session():
            logging.info("Logged in successfully using existing session token.")
            self.is_logged_in = True
        else:
            logging.info("Attempting standard login with credentials.")
            self.is_logged_in = self.standard_login()

    
    def get_weekly_expiry_date(self):
     try:
        symboldf = pd.read_csv(self.masters_file)
         # Debugging print statement
        symboldf['Expiry'] = symboldf['Expiry'].astype(str)
        symboldf.loc[:, 'Expiry'] = pd.to_datetime(symboldf['Expiry'], format='%d-%b-%Y', errors='coerce').dt.date
        
        symboldf['Expiry'] = pd.to_datetime(symboldf['Expiry']).dt.date
        banknifty_df = symboldf[(symboldf['Exchange'] == 'NFO') & (symboldf['Symbol'] == 'BANKNIFTY')]
        
        today = datetime.datetime.now().date()
        future_expiries = banknifty_df[banknifty_df['Expiry'] > today]['Expiry'].unique().tolist()
        
        future_expiries.sort()
        next_expiry = future_expiries[0]   
        self.expiry_date = next_expiry
        
        return self.expiry_date    
            
            
           
            
      
     except Exception as e:
        print(f"Exception in get_weekly_expiry_date: {e}")
        return None

    def get_option_tokens(self, expiry_date, strike_price):
        if strike_price == 0:
          print("Invalid strike price.")
          return {'call_token': None, 'put_token': None}
        # Convert expiry_date to match the file format 'dd-MMM-yyyy'
        formatted_expiry_date = expiry_date.strftime("%d%b%y").upper()
        
        # Construct option symbols
        call_symbol = f"BANKNIFTY{formatted_expiry_date}C{strike_price}"
        
        put_symbol = f"BANKNIFTY{formatted_expiry_date}P{strike_price}"
        self.call_symbol=call_symbol
        self.put_symbol=put_symbol
        print('call su')
        print(self.call_symbol)

        # Load the NFO symbols file
        symbols_df = pd.read_csv(os.path.join(self.BASE_DIR, self.masters_file))
        
        
        # Ensure the 'TradingSymbol' column matches our constructed symbols
        call_token_row = symbols_df[symbols_df['TradingSymbol'] == call_symbol]
        put_token_row = symbols_df[symbols_df['TradingSymbol'] == put_symbol]

        # Extract tokens if found
        call_token = call_token_row['Token'].iloc[0] if not call_token_row.empty else None
        put_token = put_token_row['Token'].iloc[0] if not put_token_row.empty else None
        
        formatted_expiry_date = expiry_date.strftime("%d%b%y").upper()
        json_file_path = 'options_data.json'
        if os.path.exists(json_file_path):
       #          # If JSON file exists, read data from the file
         with open(json_file_path, 'r') as json_file:
                     data = json.load(json_file)
                     if 'call_token' in data and 'put_token' in data:
       #                   # Set call and put symbols from JSON
       #                   print('readfromjson')
                           self.call_symbol = data['call_symbol']
                           self.put_symbol = data['put_symbol']
                           print('read token form fil')
                           return {"call_token": call_token, "put_token": put_token, "call_symbol":call_symbol, "put_symbol":put_symbol}
            # Construct option symbols
                     else:
                         self.call_symbol = f"BANKNIFTY{formatted_expiry_date}C{strike_price-100}"
                         print(self.call_symbol)
                         self.put_symbol = f"BANKNIFTY{formatted_expiry_date}P{strike_price-100}"
                         print(self.put_symbol)
                         return {"call_token": call_token, "put_token": put_token, "call_symbol":call_symbol, "put_symbol":put_symbol}
        


    def start_session_and_subscribe(self):
     if self.check_and_initiate_connection():
        logging.info("Connection initiated successfully.")
        self.start_websocket()
        
        self.subscribe_to_banknifty()
        
        if self.banknifty_subscribed:
            logging.info("Successfully subscribed to Bank Nifty.")
            expiry_date = self.get_weekly_expiry_date()
            if expiry_date is None:
                logging.error("Failed to fetch expiry date. Cannot proceed with options subscription.")
                return
            
            strike_price = self.fetch_ATM()
            if strike_price is None:
                logging.error("Failed to fetch ATM strike price. Cannot proceed with options subscription.")
                return
            
            logging.info(f"Fetched strike price: {strike_price}, expiry date: {expiry_date}")
            self.update_tokens(expiry_date, strike_price)
            # Proceed with options subscription
            self.subscribe_to_options(expiry_date, strike_price)
            
        else:
             logging.error("Failed to subscribe to Bank Nifty. Check if the WebSocket connection is active and try again.")
     else:
         logging.error("Failed to initiate connection. Check credentials and internet connectivity.")

      
    
    def subscribe_to_options(self, expiry_date, strike_price):
     if strike_price == 0:
        logging.error("Invalid strike price. Cannot proceed with subscription.")
        return

    # Get option tokens and symbols
     option_tokens = self.get_option_tokens(expiry_date, strike_price)

     if option_tokens is None:
        logging.error("Failed to retrieve option tokens. Cannot proceed.")
        return

    # Extract call and put tokens and symbols
     call_token = option_tokens.get('call_token')
     put_token = option_tokens.get('put_token')

    # Ensure tokens are valid
     if not call_token or not put_token:
        logging.error("Missing call or put token. Cannot proceed with subscription.")
        return

    # Update instance variables
     self.call_symbol = str(option_tokens.get('call_symbol'))
     self.put_symbol = str(option_tokens.get('put_symbol'))
     self.ce_token = str(call_token)
     self.pe_token = str(put_token)

    # Prepare data to write into JSON file
     data = {
        'call_token': self.ce_token,
        'put_token': self.pe_token,
        'call_symbol': self.call_symbol,
        'put_symbol': self.put_symbol
    }

    # Define JSON file path
     json_file_path = 'options_data.json'

    # Step 1: Check if the file exists and back it up with a timestamp if it does
     if os.path.exists(json_file_path):
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')  # Format: YYYYMMDD_HHMMSS
        backup_file_path = f'options_data_backup_{timestamp}.json'
        os.rename(json_file_path, backup_file_path)
        logging.info(f"Existing options_data.json backed up as {backup_file_path}")

    # Step 2: Write the new token data to options_data.json
     with open(json_file_path, 'w') as json_file:
        json.dump(data, json_file, indent=4)
        logging.info("New token data written to options_data.json")

    # Step 3: Proceed with subscription using the tokens
     self.api.subscribe([f"NFO|{self.ce_token}", f"NFO|{self.pe_token}"])

    # Set up worker threads (assuming this method manages real-time updates)
     self.setup_worker_threads()

    # Set up a handler for LTP (Last Traded Price) updates
     self.api.on_quote_update = self.event_handler_quote_update
     logging.info(f"Successfully subscribed to options with Call Token: {self.ce_token}, Put Token: {self.pe_token}")
      

     

   
        
        # Implement connection check and login if disconnected
        # This method should update self.is_logged_in accordingly
        # Example: self.is_logged_in = self.load_and_login()

    def fetch_ATM(self):
     
     
        # Assuming a strike price interval of 100
     
     
     ltp_numeric = float(self.BN_indexLtp)
     
    
     mod = ltp_numeric % 100
     
     
     if mod < 50:
            self.atm_strike = int(ltp_numeric // 100) * 100
     else:
            self.atm_strike = int((ltp_numeric // 100) + 1) * 100
         
     
     return self.atm_strike
     
    
     def handle_option_ltp_update(self, tick_data):
        # Assuming tick_data is a dictionary containing the 'token' and 'ltp' among other data
        if 'token' in tick_data and 'ltp' in tick_data:
           
            token = tick_data['token']
           
            ltp = tick_data['ltp']
            
            # Check if the token matches the Call or Put option token and process accordingly
            if token == self.call_token:
                
                # Update Call option LTP in your GUI or internal data structure
                # Optionally, invoke the GUI update callback if you have one
                if self.update_ltp_callback:
                    self.update_ltp_callback(ltp, 'call')

            elif token == self.put_token:
                
                # Update Put option LTP in your GUI or internal data structure
                # Optionally, invoke the GUI update callback if you have one
                if self.update_ltp_callback:
                    self.update_ltp_callback(ltp, 'put')

        else:
            print("Received tick_data does not contain required information")      
        
   

    def download_instruments_csv(self):
        print("doenloadin")
        """
        Downloads the NFO instruments file. Adjusts the URL based on specific requirements.
        """
        url = 'https://api.shoonya.com/NFO_symbols.txt.zip'
        local_file_path = os.path.join(self.BASE_DIR, 'NFO_symbols.txt.zip')
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            with open(local_file_path, "wb") as file:
                for chunk in response.iter_content(chunk_size=128):
                    file.write(chunk)
            logging.info(f"Downloaded {local_file_path} successfully.")
            with zipfile.ZipFile(local_file_path, 'r') as zip_ref:
                zip_ref.extractall(self.BASE_DIR)
            logging.info(f"Extracted: {local_file_path}")
        except requests.RequestException as e:
            logging.error(f"Failed to download instruments file: {e}")

    # Implement other methods as needed...
    
    def calculate_atm_strike(self, BN_indexLtp):
        """Calculate ATM strike based on LTP."""
        strike_price_interval = 100  # Assuming strike price interval for BANKNIFTY is 100
        atm_strike = round(BN_indexLtp / strike_price_interval) * strike_price_interval
        return atm_strike
       


    """
    Sets up the websocket connection for real-time data updates in a non-blocking manner.
    """
    def open_callback(self):
        """Callback function to execute when WebSocket connection is opened."""
        self.feed_opened = True
        
        logging.info("WebSocket connection opened.")
        
    def close_callback(self):
        self.feed_opened= False
        logging.info("WebSocket connection closed.")
        print("WebSocket connection closed. Attempting to reconnect...")
          # Simple fixed delay; consider exponential backoff in production
        self.start_websocket()  # Your method to initialize the WebSocket connection
    #def start_websocket(self):
        """Starts the WebSocket connection."""
        
     #   print ('websocket')
        # Example setup for starting WebSocket connection
        # 'api' needs to be initialized as your WebSocket client
     #   self.api.start_websocket(
      #      order_update_callback=self.event_handler_order_update,
      #      subscribe_callback=self.event_handler_quote_update,
    #        socket_open_callback=self.open_callback  # Register the open callback here
   #    )
    def start_websocket(self):
     """Starts the WebSocket connection."""
    
    # Check if WebSocket is already opened
     if self.is_websocket_connected():
        print("WebSocket is already opened.")
        return  # Exit the function if the connection is already open
    
    # Attempt to start the WebSocket connection if not already opened
     try:
        self.api.start_websocket(            
            subscribe_callback=self.event_handler_quote_update,
            socket_open_callback=self.open_callback
        )
        print("WebSocket connection initiated successfully.")
        self.__websocket_connected=True
     except Exception as e:
        print(f"Failed to start WebSocket: {e}")
        self.__websocket_connected=False

     
    def subscribe_to_banknifty(self):
     print('banknifty')
     
     if self.api:  # Check if API is initialized
        try:
            self.api.subscribe([f"NSE|{self.banknifty_token}",'NFO|46324'])
            print()
            logging.info("Subscribed to BankNIFTY updates.")
            self.api.on_quote_update = self.event_handler_quote_update

            # Indicate successful subscription
            self.banknifty_subscribed = True
        except Exception as e:
            logging.error(f"Failed to subscribe to BankNIFTY: {e}")
            self.banknifty_subscribed = False
     else:
        logging.error("API connection is not initialized.")
        self.banknifty_subscribed = False

    import os

    



    def update_gui_with_ltp(self, ltp_value, ltp_type):
     if ltp_type == "index":
        self.ltp_label_index.config(text=f"Index LTP: {ltp_value}")
     elif ltp_type == "call":
        self.ltp_label_call.config(text=f"Call LTP: {ltp_value}")
     elif ltp_type == "put":
         self.ltp_label_put.config(text=f"Put LTP: {ltp_value}")

    def update_tokens(self, expiry_date, strike_price):
        tokens = self.get_option_tokens(expiry_date, strike_price)
        self.ce_token = str(tokens.get('call_token'))
        self.pe_token = str(tokens.get('put_token'))
        print(f"Tokens updated: ce_token={self.ce_token}, pe_token={self.pe_token}")
    def event_handler_quote_update(self, tick_data):
    # Check if 'tk' (token) and 'lp' (last price) are present in tick_data
     if 'tk' in tick_data and 'lp' in tick_data:
        token = tick_data['tk']
        ltp = tick_data['lp']
        self.ltp_dict[token] = ltp
       
    
        
        
      
        
        
        
       
        if token == self.banknifty_token:
            
            self.BN_indexLtp=tick_data['lp']
            if self.update_gui_callback:
                self.update_gui_callback(ltp, 'index')
            
        elif str(token) == str(self.ce_token):
           
            self.ce_ltp=tick_data['lp']
            
            if self.update_gui_callback:
                self.update_gui_callback(ltp, 'call')
        elif str(token) == str(self.pe_token):
         
            self.pe_ltp=tick_data['lp']
           
            if self.update_gui_callback:
                self.update_gui_callback(ltp, 'put')
        current_time = datetime.datetime.now().isoformat()
        if tick_data['tk'] == self.banknifty_token:
         
         token_type='index'
         
         self.data_queue.put({
             'token': token,
             'ltp': ltp,
             'time': current_time,
             'type': token_type
         })
         data_item=self.data_queue.get_nowait()
         self.data_queue.put(data_item)
         
        if tick_data['tk'] == self.ce_token:
         
         token_type='call'
         
            
         self.data_queue.put({
             'token': token,
             'ltp': ltp,
             'time': current_time,
             'type': token_type
         })
         data_item=self.data_queue.get_nowait()
         self.data_queue.put(data_item)
         
    # Update GUI for call option
        elif str(tick_data['tk']) == self.pe_token:
         
         token_type='put'
         
         self.data_queue.put({
             'token': token,
             'ltp': ltp,
             'time': current_time,
             'type': token_type
         })
         if token_type=='put':
            
            data_item=self.data_queue.get_nowait()
            self.data_queue.put(data_item)
            
    def shutdown(self):
        self.running = False
        for _ in range(3):  # Ensure all threads stop
            self.data_queue.put(None)

def update_gui_ltp(self, ltp, type):
    if self.update_gui_callback:
        self.update_gui_callback(ltp, type)
        
        
     # Exception handling for API call failure


# Running the profiler
     
    
     # Ex
    #def event_handler_quote_update(self, tick_data):
     #   # Check for BankNIFTY updates and update LTP
    #    if 'tk' in tick_data and tick_data['tk'] == self.banknifty_token and 'lp' in tick_data:
    #        self.BN_indexLtp = tick_data['lp']
    #        # Here you can add any additional logic to act on the new LTP, such as updating GUI, logging, etc.
      #      logging.info(f"Updated BankNIFTY LTP: {self.BN_indexLtp}")
    ##        # Invoke the GUI update callback if it's set
    #        if self.update_gui_callback:
     #         self.update_gui_callback(self.BN_indexLtp)
     #         print('event call handler after bn subsc')
     #         print(self.BN_indexLtp)   

def main():
    logging.basicConfig(level=logging.INFO)
    session = TradingSession2(config_path1='cred1.yml')
    #call_sma_data = session.process_call_data('call_data.csv')
    #put_sma_data = session.process_put_data('put_data.csv')

    
    # Presuming this is a console application and you want to keep it running:
    
    try:
        while True:
            pass  # Your main loop logic
    except KeyboardInterrupt:
          session.shutdown()

   
    
    
    
    
   
        
        # Now the session is ready for trading activities
        # Additional trading session setup...
   

if __name__ == "__main__":
    main()
    
    def set_pnl_callback(self, callback):
        self.pnl_callback = callback

    def calculate_pnl(self, current_price, traded_price, quantity):
        pnl = (current_price - traded_price) * quantity
        if self.pnl_callback:
            self.pnl_callback(pnl)

    # Add the logic to handle buy actions and trigger PnL calculation
    #def handle_buy_call(self, current_price, traded_price, quantity):
        #self.calculate_pnl(current_price, traded_price, quantity)
        # Other buy call logic
    #def handle_buy_put(self, current_price, traded_price, quantity):
        #self.calculate_pnl(current_price, traded_price, quantity)
        # Other buy put logic