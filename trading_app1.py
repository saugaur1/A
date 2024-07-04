import tkinter as tk
from threading import Thread
from Tradingsession1 import TradingSession2  # Ensure this import path is correct
import logging
import queue
from tkinter import messagebox
import datetime

class TradingApp1:
    def __init__(self, root, trading_session):
        self.master = root
        self.master.configure(bg='#FFFFFF')
        self.call_data = []
        self.put_data = []
        self.index_data = []
        self.trading_session = trading_session
        self.update_queue = queue.Queue()
        self.trading_session.update_gui_callback = self.update_gui_with_ltp
        self.call_symbol = ""
        self.put_symbol = ""

        # Initialize the GUI components
        self.setup_gui_components()
        self.process_queue_updates()

        # Checkbox for controlling a variable
        self.checkbox_var = tk.BooleanVar(value=False)
        self.checkbox = tk.Checkbutton(self.master, text="Toggle Variable", variable=self.checkbox_var, command=self.toggle_variable)
        self.checkbox.grid(row=5, column=0, padx=10, pady=10)

    def setup_gui_components(self):
        # PnL Labels for multiple positions
        button_style = {'bg': '#4e5f70', 'fg': '#ffffff', 'padx': 10, 'pady': 5}
        label_style = {'bg': '#1e1e2d', 'fg': '#ffffff'}
        entry_style = {'bg': '#333333', 'fg': '#ffffff', 'insertbackground': '#ffffff'}

        self.pnl_labels = []
        for i in range(3):
            pnl_label = tk.Label(self.master, text=f"PnL {i+1}: -", **label_style)
            pnl_label.grid(row=6+i, column=0, columnspan=2, padx=10, pady=10, sticky="ew")
            pnl_label.grid_remove()  # Initially hide the label
            self.pnl_labels.append(pnl_label)

        self.price_difference_label = tk.Label(self.master, text="Price Difference: 0", **label_style)
        self.price_difference_label.grid(row=8, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        self.download_button = tk.Button(self.master, text="Download Tim Data", command=self.download_tim, **button_style)
        self.download_button.grid(row=4, column=1, padx=10, pady=10, sticky="ew")

        for i in range(4):
            self.master.grid_columnconfigure(i, weight=1)

        self.start_session_button = tk.Button(self.master, text="Start Trading Session", command=self.start_trading_session, **button_style)
        self.start_session_button.grid(row=2, column=0, padx=10, pady=10)

        self.setup_trailing_stop_loss_controls(row=1)
        self.setup_trading_controls(row=2, label_style=label_style, entry_style=entry_style)

        self.set_stop_loss_button = tk.Button(self.master, text="Set Stop Loss", command=self.set_stop_loss, **button_style)
        self.set_stop_loss_button.grid(row=3, column=3, padx=10, pady=10, sticky="ew")

        self.setup_trading_ui(row=3, label_style=label_style, button_style=button_style)

    def toggle_variable(self):
        variable_value = self.checkbox_var.get()
        self.trading_session.update_variable(variable_value)

    def setup_trailing_stop_loss_controls(self, row):
        self.trailing_enabled_var = tk.BooleanVar(value=False)
        self.trailing_checkbox = tk.Checkbutton(self.master, text="Enable Trailing Stop Loss", variable=self.trailing_enabled_var, command=self.toggle_trailing_fields)
        self.trailing_checkbox.grid(row=row, column=4)

        tk.Label(self.master, text="Trailing Trigger:", bg='#1e1e2d', fg='#ffffff').grid(row=row+1, column=2)
        self.trailing_trigger_entry = tk.Entry(self.master)
        self.trailing_trigger_entry.grid(row=row+1, column=3)
        self.trailing_trigger_entry.grid_remove()

        tk.Label(self.master, text="Move Type:", bg='#1e1e2d', fg='#ffffff').grid(row=row+2, column=2)
        self.trailing_move_type_var = tk.StringVar(value="percentage")
        self.trailing_move_type_options = tk.OptionMenu(self.master, self.trailing_move_type_var, "absolute", "percentage")
        self.trailing_move_type_options.grid(row=row+2, column=3)
        self.trailing_move_type_options.grid_remove()

        tk.Label(self.master, text="Trailing Move:", bg='#1e1e2d', fg='#ffffff').grid(row=row+3, column=2)
        self.trailing_move_entry = tk.Entry(self.master)
        self.trailing_move_entry.grid(row=row+3, column=3)
        self.trailing_move_entry.grid_remove()

    def toggle_trailing_fields(self):
        if self.trailing_enabled_var.get():
            self.trailing_trigger_entry.grid()
            self.trailing_move_entry.grid()
            self.trailing_move_type_options.grid()
        else:
            self.trailing_trigger_entry.grid_remove()
            self.trailing_move_entry.grid_remove()
            self.trailing_move_type_options.grid_remove()

    def setup_trading_controls(self, row, label_style, entry_style):
        self.stop_loss_enabled_var = tk.BooleanVar(value=False)
        self.stop_loss_checkbox = tk.Checkbutton(self.master, text="Enable Stop Loss", variable=self.stop_loss_enabled_var, command=self.toggle_stop_loss_fields)
        self.stop_loss_checkbox.grid(row=row, column=4)

        tk.Label(self.master, text="Stop Loss Value:", bg='#1e1e2d', fg='#ffffff').grid(row=row-1, column=2)
        self.stop_loss_value_entry = tk.Entry(self.master)
        self.stop_loss_value_entry.grid(row=row-1, column=3)
        self.stop_loss_value_entry.grid_remove()

        tk.Label(self.master, text="Stop Loss Type:", bg='#1e1e2d', fg='#ffffff').grid(row=row+2, column=2)
        self.stop_loss_type_var = tk.StringVar(value="percentage")
        self.stop_loss_type_options = tk.OptionMenu(self.master, self.stop_loss_type_var, "absolute", "percentage")
        self.stop_loss_type_options.grid(row=row-2, column=3)
        self.stop_loss_type_options.grid_remove()

        tk.Label(self.master, text="Quantity:", bg='#1e1e2d', fg='#ffffff').grid(row=row+3, column=1)
        self.quantity_entry = tk.Entry(self.master)
        self.quantity_entry.grid(row=row+4, column=1)

    def toggle_stop_loss_fields(self):
        if self.stop_loss_enabled_var.get():
            self.stop_loss_value_entry.grid()
            self.stop_loss_type_options.grid()
        else:
            self.stop_loss_value_entry.grid_remove()
            self.stop_loss_type_options.grid_remove()

    def setup_trading_ui(self, row, label_style, button_style):
        self.ltp_label_index = tk.Label(self.master, text="Index LTP: -", **label_style)
        self.ltp_label_index.grid(row=row, column=0, sticky='ew', padx=10, pady=10)
        self.ltp_label_call = tk.Label(self.master, text="Call LTP: -", **label_style)
        self.ltp_label_call.grid(row=row-2, column=1, sticky='ew', padx=10, pady=10)
        self.ltp_label_put = tk.Label(self.master, text="Put LTP: -", **label_style)
        self.ltp_label_put.grid(row=row-1, column=1, sticky='ew', padx=10, pady=10)

        self.setup_option_frame(row, 1, "call", label_style, button_style)
        self.setup_option_frame(row, 2, "put", label_style, button_style)

    def setup_option_frame(self, row, column, option_type, label_style, button_style):
        frame = tk.Frame(self.master, bg='#1e1e2d')
        frame.grid(row=row, column=column, padx=10, pady=10, sticky='ew')

        ltp_label = tk.Label(frame, text=f"{option_type.capitalize()} LTP: -", **label_style)
        ltp_label.pack(side=tk.LEFT)

        if option_type == "call":
            buy_button = tk.Button(frame, text="Buy Call", command=self.buy_call, **button_style)
            sell_button = tk.Button(frame, text="Sell Call", command=self.sell_call, **button_style)
        elif option_type == "put":
            buy_button = tk.Button(frame, text="Buy Put", command=self.buy_put, **button_style)
            sell_button = tk.Button(frame, text="Sell Put", command=self.sell_put, **button_style)
        else:
            raise ValueError("Option type must be 'call' or 'put'")

        buy_button.pack(side=tk.LEFT, padx=5)
        sell_button.pack(side=tk.RIGHT)

    def set_stop_loss(self):
        try:
            if self.trading_session is not None:
                self.trading_session.stop_loss_enabled = self.stop_loss_enabled_var.get()
                self.trading_session.stop_loss_type = self.stop_loss_type_var.get().lower()
                self.trading_session.stop_loss_value = float(self.stop_loss_value_entry.get())

                if self.trailing_enabled_var.get():
                    self.trading_session.is_trailing = True
                    self.trading_session.trailing_trigger = float(self.trailing_trigger_entry.get())
                    self.trading_session.trailing_move_type = self.trailing_move_type_var.get().lower()
                    self.trading_session.trailing_move = float(self.trailing_move_entry.get())
                    self.trading_session.trailing_enabled = True
                else:
                    self.trading_session.trailing_enabled = False

                print('Trailing Stop Loss Settings:')
                print(f"Trigger: {self.trailing_trigger_entry.get()}")
                print(f"Move Type: {self.trailing_move_type_var.get()}")
                print(f"Move Value: {self.trailing_move_entry.get()}")

                messagebox.showinfo("Success", "Stop loss set successfully.")
            else:
                messagebox.showerror("Error", "Trading session is not initialized.")
        except ValueError:
            messagebox.showerror("Error", "Invalid input. Please enter valid numeric values.")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")

    def buy_call(self):
        tradingsymbol = self.call_symbol
        quantity = int(self.quantity_entry.get())

        self.traded_price = self.current_call_price

        self.trading_session.place_buy_call_order(
            buy_or_sell='B', product_type='I', exchange='NFO',
            tradingsymbol=self.call_symbol, quantity=quantity,
            discloseqty=0, price_type='MKT', price=0, trigger_price=None,
            retention='DAY', remarks='Buy Call Order'
        )

        #self.update_price_difference()

    def buy_put(self):
        tradingsymbol = self.put_symbol
        quantity = int(self.quantity_entry.get())

        self.traded_price = self.current_call_price

        self.trading_session.place_buy_put_order(
            buy_or_sell='B', product_type='I', exchange='NFO',
            tradingsymbol=self.put_symbol, quantity=quantity,
            discloseqty=0, price_type='MKT', price=0, trigger_price=None,
            retention='DAY', remarks='Buy Put Order'
        )

        #self.update_price_difference()

    def update_price_difference(self):
        if hasattr(self, 'traded_price'):
            price_difference = self.current_call_price - self.traded_price
        else:
            price_difference = 0
        self.price_difference_label.config(text=f"Price Difference: {price_difference}")

    def download_tim(self):
        starttime = datetime.datetime(2024, 4, 22)
        endtime = datetime.datetime(2024, 4, 27)
        print('calling timeseries')
        self.trading_session.get_time_price_series('NFO', '49531', starttime, endtime, 5)

    def sell_put(self):
        tradingsymbol = self.put_symbol
        quantity = int(self.quantity_entry.get())

        self.trading_session.place_sell_put_order(
            buy_or_sell='S', product_type='P', exchange='NSE',
            tradingsymbol=self.put_symbol, quantity=quantity,
            discloseqty=0, price_type='MKT', price=0, trigger_price=None,
            retention='DAY', remarks='Sell Put Order'
        )

# =============================================================================
#     def update_pnls(self):
#         try:
#             current_price = self.index_data[-1] if self.index_data else 0
#             pnls = self.calculate_pnls(current_price)
#             for i, pnl in enumerate(pnls):
#                 self.queue_gui_update(self._update_pnl_label, (i, pnl))
#         except Exception as e:
#             logging.error(f"Error updating PnL: {e}")
# 
# =============================================================================
    def calculate_pnls(self, current_price):
        pnls = []
        for position in list(self.trading_session.positions.values())[:3]:
            fill_price = position['filled_price']
            quantity = position['quantity']
            pnl = (current_price - fill_price) * quantity
            pnls.append(pnl)
        return pnls

    def _update_pnl_label(self, index, pnl):
        if index < len(self.pnl_labels):
            self.pnl_labels[index].config(text=f"PnL {index+1}: {pnl:.2f} points")
            self.pnl_labels[index].grid()

        for i in range(len(self.pnl_labels)):
            if i >= len(self.trading_session.positions):
                self.pnl_labels[i].grid_remove()

    def sell_call(self):
        tradingsymbol = self.call_symbol
        quantity = int(self.quantity_entry.get())

        self.trading_session.place_sell_call_order(
            buy_or_sell='S', product_type='C', exchange='NSE',
            tradingsymbol=self.call_symbol, quantity=quantity,
            discloseqty=0, price_type='MKT', price=0, trigger_price=None,
            retention='DAY', remarks='Sell Call Order'
        )

    def update_gui_with_ltp(self, ltp_value, ltp_type):
        if ltp_type == "index":
            self.index_data.append(ltp_value)
            self.queue_gui_update(self._update_ltp_label_index, (ltp_value,))
        elif ltp_type == "call":
            self.call_data.append(ltp_value)
            self.current_call_price = ltp_value
            self.queue_gui_update(self._update_ltp_label_call, (ltp_value,))
        elif ltp_type == "put":
            self.put_data.append(ltp_value)
            self.queue_gui_update(self._update_ltp_label_put, (ltp_value,))
            self.current_put_price = ltp_value
        #self.update_pnls()
        #self.update_price_difference()

    def _update_ltp_label_index(self, ltp_value):
        self.ltp_label_index.config(text=f"Index LTP: {ltp_value}")

    def _update_ltp_label_call(self, ltp_value):
        self.ltp_label_call.config(text=f"Call LTP: {ltp_value}")

    def _update_ltp_label_put(self, ltp_value):
        self.ltp_label_put.config(text=f"Put LTP: {ltp_value}")

    def queue_gui_update(self, func, args=()):
        self.update_queue.put((func, args))

    def process_queue_updates(self):
        try:
            while not self.update_queue.empty():
                update_func, args = self.update_queue.get_nowait()
                update_func(*args)
        except queue.Empty:
            pass
        finally:
            self.master.after(5, self.process_queue_updates)

    def start_trading_session(self):
        Thread(target=self.trading_session.start_session_and_subscribe).start()

def main():
    logging.basicConfig(level=logging.INFO)

    root = tk.Tk()
    root.title("Trading Bot")

    session = TradingSession2()
    app = TradingApp1(root, session)

    root.mainloop()

if __name__ == "__main__":
    main()
