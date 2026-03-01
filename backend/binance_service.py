import os
import logging
from binance.client import Client
from binance.enums import *
from binance.exceptions import BinanceAPIException
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")
# Default to True for safety if not set
TESTNET = os.getenv("BINANCE_TESTNET", "True").lower() == "true"

class BinanceService:
    def __init__(self):
        self.client = None
        self.exchange_info = {}
        if API_KEY and API_SECRET:
            try:
                self.client = Client(API_KEY, API_SECRET, testnet=TESTNET)
                logger.info(f"Binance Client initialized (Testnet: {TESTNET})")
                self._load_exchange_info()
            except Exception as e:
                logger.error(f"Failed to initialize Binance Client: {e}")
        else:
            logger.warning("BINANCE_API_KEY or BINANCE_API_SECRET not set.")

    def _load_exchange_info(self):
        try:
            info = self.client.futures_exchange_info()
            for symbol_info in info['symbols']:
                symbol = symbol_info['symbol']
                self.exchange_info[symbol] = {
                    'quantity_precision': symbol_info['quantityPrecision'],
                    'price_precision': symbol_info['pricePrecision'],
                    'min_qty': float(next(f['minQty'] for f in symbol_info['filters'] if f['filterType'] == 'LOT_SIZE')),
                    'step_size': float(next(f['stepSize'] for f in symbol_info['filters'] if f['filterType'] == 'LOT_SIZE')),
                    'tick_size': float(next(f['tickSize'] for f in symbol_info['filters'] if f['filterType'] == 'PRICE_FILTER'))
                }
            logger.info("Exchange info loaded.")
        except Exception as e:
            logger.error(f"Failed to load exchange info: {e}")

    def _round_step_size(self, quantity, step_size, precision):
        quantity = float(quantity)
        step_size = float(step_size)
        precision = int(precision)
        return round(int(quantity / step_size) * step_size, precision)

    def _round_tick_size(self, price, tick_size, precision):
        price = float(price)
        tick_size = float(tick_size)
        precision = int(precision)
        return round(int(price / tick_size) * tick_size, precision)

    def get_total_history_pnl(self):
        if not self.client:
            return 0.0
        try:
            # Fetch income history (limit to last 1000 entries)
            # Income types: TRANSFER, WELCOME_BONUS, REALIZED_PNL, FUNDING_FEE, COMMISSION, INSURANCE_CLEAR
            income_history = self.client.futures_income_history(limit=1000)
            
            total_pnl = 0.0
            for income in income_history:
                # Sum up PnL, Commission, and Funding Fees
                if income['incomeType'] in ['REALIZED_PNL', 'COMMISSION', 'FUNDING_FEE']:
                    total_pnl += float(income['income'])
            
            return total_pnl
        except BinanceAPIException as e:
            logger.error(f"Error fetching income history: {e}")
            return 0.0

    def get_account_summary(self):
        # Demo data for fallback
        demo_data = {
            "totalWalletBalance": 10000.0,
            "totalUnrealizedProfit": 150.5,
            "totalMarginBalance": 10150.5,
            "availableBalance": 9500.0,
            "totalHistoryPnl": 1250.80, # Demo history PnL
            "is_demo": True
        }

        if not self.client:
            return demo_data
            
        try:
            account = self.client.futures_account()
            usdt_available = 0.0
            for asset in account['assets']:
                if asset['asset'] == 'USDT':
                    usdt_available = float(asset['availableBalance'])
                    break
            
            # Fetch historical PnL
            history_pnl = self.get_total_history_pnl()
            
            return {
                "totalWalletBalance": float(account.get('totalWalletBalance', 0.0)),
                "totalUnrealizedProfit": float(account.get('totalUnrealizedProfit', 0.0)),
                "totalMarginBalance": float(account.get('totalMarginBalance', 0.0)),
                "availableBalance": usdt_available,
                "totalHistoryPnl": history_pnl,
                "is_demo": False
            }
        except BinanceAPIException as e:
            logger.error(f"Error fetching account summary: {e}")
            # Return demo data on error so UI looks good
            return demo_data

    def get_positions(self):
        # Demo positions for fallback
        demo_positions = [
            {
                "symbol": "BTCUSDT",
                "positionAmt": 0.5,
                "entryPrice": 65000.0,
                "unRealizedProfit": 120.5,
                "leverage": 10,
                "marginType": "isolated"
            },
            {
                "symbol": "ETHUSDT",
                "positionAmt": -5.0,
                "entryPrice": 3500.0,
                "unRealizedProfit": -30.0,
                "leverage": 20,
                "marginType": "cross"
            }
        ]

        if not self.client:
            return demo_positions
            
        try:
            account = self.client.futures_account()
            positions = [
                {
                    "symbol": p['symbol'],
                    "positionAmt": float(p['positionAmt']),
                    "entryPrice": float(p['entryPrice']),
                    "unRealizedProfit": float(p['unRealizedProfit']),
                    "leverage": p['leverage'],
                    "marginType": p['marginType']
                }
                for p in account['positions'] 
                if float(p['positionAmt']) != 0
            ]
            return positions
        except BinanceAPIException as e:
            logger.error(f"Error fetching positions: {e}")
            return demo_positions

    def get_balance(self, asset='USDT'):
        if not self.client:
            return 0.0
        try:
            account = self.client.futures_account()
            for balance in account['assets']:
                if balance['asset'] == asset:
                    return float(balance['availableBalance'])
            return 0.0
        except BinanceAPIException as e:
            logger.error(f"Error fetching balance: {e}")
            return 0.0

    def close_position(self, symbol: str):
        if not self.client:
            return {"error": "API keys not configured"}
        try:
            # Get current position size
            positions = self.get_positions()
            position = next((p for p in positions if p['symbol'] == symbol), None)
            
            if not position:
                return {"message": "No open position for this symbol"}
            
            amt = position['positionAmt']
            side = SIDE_SELL if amt > 0 else SIDE_BUY
            
            # Place Market Order to Close
            order = self.client.futures_create_order(
                symbol=symbol,
                side=side,
                type=ORDER_TYPE_MARKET,
                quantity=abs(amt),
                reduceOnly=True
            )
            
            logger.info(f"Closed position for {symbol}: {order['orderId']}")
            return order
            
        except BinanceAPIException as e:
            logger.error(f"Error closing position: {e}")
            return {"error": str(e)}

    def _apply_precision(self, symbol, quantity=None, price=None):
        if symbol not in self.exchange_info:
            return quantity, price
        
        info = self.exchange_info[symbol]
        
        if quantity is not None:
            quantity = self._round_step_size(quantity, info['step_size'], info['quantity_precision'])
            
        if price is not None:
            price = self._round_tick_size(price, info['tick_size'], info['price_precision'])
            
        return quantity, price

    def get_ticker_price(self, symbol):
        if not self.client:
            return None
        try:
            ticker = self.client.futures_symbol_ticker(symbol=symbol)
            return float(ticker['price'])
        except Exception as e:
            logger.error(f"Error fetching ticker price: {e}")
            return None

    def calculate_quantity_by_usdt(self, symbol, usdt_amount, leverage=1):
        price = self.get_ticker_price(symbol)
        if not price:
            return 0.0
        
        # Quantity = (USDT Amount * Leverage) / Price
        # However, usually we want to invest X USDT as margin.
        # Margin = (Quantity * Price) / Leverage
        # So Quantity = (Margin * Leverage) / Price
        
        raw_quantity = (usdt_amount * leverage) / price
        quantity, _ = self._apply_precision(symbol, quantity=raw_quantity)
        return quantity

    def place_order(self, symbol: str, side: str, quantity: float, leverage: int = 10, stop_loss: float = None, take_profit: float = None):
        if not self.client:
            return {"error": "API keys not configured"}

        try:
            # 1. Set leverage
            try:
                self.client.futures_change_leverage(symbol=symbol, leverage=leverage)
                logger.info(f"Leverage set to {leverage} for {symbol}")
            except BinanceAPIException as e:
                logger.warning(f"Error setting leverage: {e}")

            # Apply Precision
            quantity, _ = self._apply_precision(symbol, quantity=quantity)
            if stop_loss:
                _, stop_loss = self._apply_precision(symbol, price=stop_loss)
            if take_profit:
                _, take_profit = self._apply_precision(symbol, price=take_profit)

            # 2. Place Main Order (Market)
            order_side = SIDE_BUY if side.upper() in ["BUY", "LONG"] else SIDE_SELL
            
            logger.info(f"Placing {order_side} order for {symbol} quantity {quantity}")
            
            order = self.client.futures_create_order(
                symbol=symbol,
                side=order_side,
                type=ORDER_TYPE_MARKET,
                quantity=quantity
            )
            
            logger.info(f"Order placed: {order['orderId']}")

            # 3. Set SL/TP (Conditional Orders)
            # Note: For simplicity, we use STOP_MARKET and TAKE_PROFIT_MARKET
            # These reduce position only if closePosition=True is set or reduceOnly=True
            
            if stop_loss:
                sl_side = SIDE_SELL if order_side == SIDE_BUY else SIDE_BUY
                logger.info(f"Setting Stop Loss at {stop_loss}")
                self.client.futures_create_order(
                    symbol=symbol,
                    side=sl_side,
                    type=FUTURE_ORDER_TYPE_STOP_MARKET,
                    stopPrice=stop_loss,
                    closePosition=True
                )
            
            if take_profit:
                tp_side = SIDE_SELL if order_side == SIDE_BUY else SIDE_BUY
                logger.info(f"Setting Take Profit at {take_profit}")
                self.client.futures_create_order(
                    symbol=symbol,
                    side=tp_side,
                    type=FUTURE_ORDER_TYPE_TAKE_PROFIT_MARKET,
                    stopPrice=take_profit,
                    closePosition=True
                )

            return order

        except BinanceAPIException as e:
            logger.error(f"Binance API Exception: {e}")
            return {"error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return {"error": str(e)}

# Singleton instance
binance_service = BinanceService()
