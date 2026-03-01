# Gizbar Auto Trading Bot

This is a cryptocurrency trading bot that automatically executes trades on Binance Futures based on signals received via a webhook.

## Features

- **Signal Receiver**: Accepts trade signals via HTTP POST requests.
- **Auto Trading**: Opens and closes positions on Binance Futures.
- **Risk Management**: Supports Stop Loss (SL) and Take Profit (TP).
- **Dashboard**: A web-based dashboard to view active positions and signal history.

## Prerequisites

- Python 3.9+
- Node.js 18+
- Binance Futures Account (API Key & Secret)

## Installation

1.  **Clone the repository** (if not already done).

2.  **Backend Setup**:
    ```bash
    cd backend
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

3.  **Frontend Setup**:
    ```bash
    cd frontend
    npm install
    ```

4.  **Configuration**:
    Create a `.env` file in the root directory (or update the existing one) with your Binance API credentials:
    ```env
    BINANCE_API_KEY=your_api_key_here
    BINANCE_API_SECRET=your_api_secret_here
    BINANCE_TESTNET=True  # Set to False for real trading
    ```

## Running the Application

1.  **Start Backend**:
    ```bash
    cd backend
    source venv/bin/activate
    uvicorn main:app --reload
    ```
    The backend will run at `http://localhost:8000`.

2.  **Start Frontend**:
    ```bash
    cd frontend
    npm run dev
    ```
    The frontend will run at `http://localhost:5173`.

## Signal Format (Webhook)

Your friend (or the signal provider) should send a POST request to `http://YOUR_SERVER_IP:8000/webhook` with the following JSON body:

### Open Position (Buy/Long or Sell/Short)

```json
{
  "symbol": "BTCUSDT",
  "side": "BUY",        // or "SELL"
  "entry_price": 50000, // Optional, for reference
  "stop_loss": 49000,   // Optional
  "take_profit": 52000, // Optional
  "quantity": 0.001,    // Quantity to trade
  "leverage": 10        // Optional, default is 10
}
```

### Close Position

```json
{
  "symbol": "BTCUSDT",
  "side": "CLOSE"
}
```

## Security Note

- **API Keys**: Keep your `.env` file secure. Do not share your API Secret.
- **Network**: If running on a public server, ensure the port 8000 is secured or use a reverse proxy (Nginx) with SSL.
- **Testnet**: Always test on Binance Testnet first before using real funds.

## Disclaimer

Use this bot at your own risk. Cryptocurrency trading involves significant risk. The developers are not responsible for any financial losses.
