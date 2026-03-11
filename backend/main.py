from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from sqlmodel import Session, select
from contextlib import asynccontextmanager
from database import create_db_and_tables, get_session, engine
from models import Signal, Trade
from binance_service import binance_service
import uvicorn

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan)

# Allow Vercel frontend to access backend
origins = [
    "http://localhost:5173", # Local development
    "http://localhost:3000",
    "https://gizbar-ba-contract.vercel.app", # Vercel production domain
    # Add any other domains if needed
    "*" # Temporarily allow all for easier setup
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import requests

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Gizbar Trading Bot Backend is running"}

@app.get("/system-info")
def get_system_info():
    """
    Returns system information including the public IP address of the server.
    Useful for whitelisting the IP in Binance.
    """
    try:
        ip = requests.get("https://api.ipify.org").text
        return {"public_ip": ip}
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/debug")
def debug_binance():
    """
    Debug endpoint to check Binance connection status and configuration.
    """
    import os
    
    api_key = os.getenv("BINANCE_API_KEY")
    api_secret = os.getenv("BINANCE_API_SECRET")
    testnet = os.getenv("BINANCE_TESTNET", "False").lower() == "true"
    
    status = {
        "env_vars": {
            "BINANCE_API_KEY_SET": bool(api_key),
            "BINANCE_API_SECRET_SET": bool(api_secret),
            "BINANCE_TESTNET": testnet
        },
        "connection": "Unknown",
        "error": None
    }
    
    if not api_key or not api_secret:
        status["connection"] = "Failed"
        status["error"] = "API Key or Secret missing in environment variables"
        return status
        
    try:
        # Try to use the service's client
        if binance_service.client:
            # Check futures account specifically
            account = binance_service.client.futures_account()
            status["connection"] = "Success"
            status["account_status"] = {"status": "Normal", "canTrade": account.get("canTrade", False)}
        else:
            status["connection"] = "Failed"
            status["error"] = "Binance client not initialized in service (check server logs)"
    except Exception as e:
        status["connection"] = "Failed"
        status["error"] = str(e)
        
    return status

@app.get("/api/debug_positions")
def debug_positions():
    """
    Debug endpoint to see raw position data from Binance.
    """
    if not binance_service.client:
        return {"error": "Client not initialized"}
    
    try:
        raw_info = binance_service.client.futures_position_information()
        # Filter for non-zero positions to keep response small
        active = [p for p in raw_info if float(p['positionAmt']) != 0]
        
        # Also run the parsing logic to see if it fails
        parsed_results = []
        for p in active:
            try:
                # Safe parsing logic simulation
                def safe_float(val, default=0.0):
                    try: return float(val) if val is not None else default
                    except: return default

                def safe_int(val, default=1):
                    try: return int(float(val)) if val is not None else default
                    except: return default

                parsed = {
                    "symbol": p.get('symbol', 'UNKNOWN'),
                    "amt": float(p.get('positionAmt', 0)),
                    "leverage": safe_int(p.get('leverage'), 1),
                    "entryPrice": safe_float(p.get('entryPrice')),
                    "unRealizedProfit": safe_float(p.get('unRealizedProfit')),
                    "status": "OK"
                }
                parsed_results.append(parsed)
            except Exception as e:
                parsed_results.append({"symbol": p.get('symbol'), "error": str(e), "status": "ERROR"})

        return {
            "count_raw": len(raw_info),
            "count_active": len(active),
            "active_positions_raw": active,
            "parsing_check": parsed_results,
            "sample_raw": raw_info[:3] if raw_info else []
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/debug/positions_raw")
def debug_positions_raw():
    """
    Direct pass-through of raw position data from Binance
    """
    return binance_service.get_raw_positions()

import time

import re

class WebhookPayload(BaseModel):
    symbol: str
    price: float
    action: str  # OPEN_LONG, OPEN_SHORT, CLOSE
    reason: Optional[str] = None
    timestamp: int
    raw_signal: Optional[str] = None

class SignalPayload(BaseModel):
    symbol: str
    side: str
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    quantity: Optional[float] = None
    usdt_amount: Optional[float] = None 
    leverage: Optional[int] = 10

@app.post("/webhook")
def receive_webhook(
    payload: dict, 
    token: str, 
    session: Session = Depends(get_session)
):
    # 1. Authentication
    expected_token = "my_secure_webhook_secret" # TODO: Move to env var
    if token != expected_token:
        raise HTTPException(status_code=403, detail="Invalid webhook token")

    # Manually parse payload to WebhookPayload to handle potential extra fields or type coercion better
    try:
        # Check if it's the new format (action/price) or old format (side/entry_price)
        if "action" in payload:
            webhook_data = WebhookPayload(**payload)
        else:
            # Fallback for old format
            # Require explicit side or action, do not default to OPEN_LONG anymore
            if "side" not in payload and "action" not in payload:
                raise HTTPException(status_code=422, detail="Missing 'action' or 'side' in payload")
            
            side = payload.get("side")
            webhook_data = WebhookPayload(
                symbol=payload.get("symbol", "ETHUSDT"),
                price=float(payload.get("entry_price", payload.get("price", 0))),
                action=side,
                timestamp=int(time.time()*1000),
                raw_signal=str(payload)
            )
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid payload format: {str(e)}")

    # 2. Parse SL/TP from raw_signal
    stop_loss = None
    take_profit = None
    
    if webhook_data.raw_signal:
        # Example: 🛑 止损(SL): 74.40
        sl_match = re.search(r"止损\(SL\):\s*([\d\.]+)", webhook_data.raw_signal)
        if sl_match:
            try:
                stop_loss = float(sl_match.group(1))
            except:
                pass
        
        # Example assumption: ✅ 止盈(TP): 80.00 (Standard format often used)
        tp_match = re.search(r"止盈\(TP\):\s*([\d\.]+)", webhook_data.raw_signal)
        if tp_match:
            try:
                take_profit = float(tp_match.group(1))
            except:
                pass

    # 3. Log signal to DB
    signal = Signal(
        symbol=webhook_data.symbol,
        side=webhook_data.action,
        entry_price=webhook_data.price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        raw_message=webhook_data.raw_signal or "",
        reason=webhook_data.reason
    )
    session.add(signal)
    session.commit()
    session.refresh(signal)

    # 4. Execute Trade Logic
    try:
        if webhook_data.action == "CLOSE":
            # Close all positions for this symbol
            order = binance_service.close_position(symbol=webhook_data.symbol)
            if "orderId" in order:
                trade = Trade(
                    signal_id=signal.id,
                    symbol=webhook_data.symbol,
                    side="CLOSE",
                    order_id=str(order["orderId"]),
                    price=float(order.get("avgPrice", 0.0)),
                    quantity=float(order.get("executedQty", 0.0)),
                    status="FILLED"
                )
                session.add(trade)
                session.commit()
                return {"status": "success", "action": "CLOSE", "order": order}
            else:
                return {"status": "error", "message": str(order)}

        elif webhook_data.action in ["OPEN_LONG", "OPEN_SHORT"]:
            # Determine side
            side = "BUY" if webhook_data.action == "OPEN_LONG" else "SELL"
            
            # Default trade settings (TODO: Make configurable)
            usdt_amount = 50.0  # Default trade size in USDT
            leverage = 10       # Default leverage
            
            # Calculate quantity
            quantity = binance_service.calculate_quantity_by_usdt(
                webhook_data.symbol, 
                usdt_amount, 
                leverage
            )
            
            if quantity <= 0:
                return {"status": "error", "message": "Calculated quantity is 0"}

            # Place Order
            order = binance_service.place_order(
                symbol=webhook_data.symbol,
                side=side,
                quantity=quantity,
                leverage=leverage,
                stop_loss=stop_loss,
                take_profit=take_profit
            )
            
            if "orderId" in order:
                 trade = Trade(
                    signal_id=signal.id,
                    symbol=webhook_data.symbol,
                    side=side,
                    order_id=str(order["orderId"]),
                    price=float(order.get("avgPrice", 0.0)),
                    quantity=quantity,
                    status="FILLED"
                 )
                 session.add(trade)
                 session.commit()
                 return {"status": "success", "action": webhook_data.action, "order": order}
            else:
                 return {"status": "error", "message": str(order)}
        
        else:
            return {"status": "error", "message": f"Unknown action: {webhook_data.action}"}

    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/manual_signal")
def manual_signal(payload: SignalPayload, session: Session = Depends(get_session)):
    # Kept for manual testing or frontend manual signals if needed
    # ... (Logic similar to old webhook)
    pass

@app.post("/close-position")
def close_position(payload: SignalPayload, session: Session = Depends(get_session)):
    # Explicit endpoint for closing positions from frontend
    try:
        order = binance_service.close_position(symbol=payload.symbol)
        if "orderId" in order:
             # Log close action as a trade
             trade = Trade(
                symbol=payload.symbol,
                side="CLOSE",
                order_id=str(order["orderId"]),
                price=float(order["avgPrice"]) if "avgPrice" in order else 0.0,
                quantity=float(order["executedQty"]) if "executedQty" in order else 0.0,
                status="FILLED"
             )
             session.add(trade)
             session.commit()
             return {"status": "success", "order": order}
        else:
             return {"status": "error", "message": str(order)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/daily_pnl")
def get_daily_pnl():
    """
    返回最近 90 天每日盈亏数据，用于前端图表展示。
    返回格式: [{date, daily_pnl, cumulative_pnl}]
    """
    if not binance_service.client:
        return []
    try:
        import time as _time
        from collections import defaultdict

        end_time = int(_time.time() * 1000)
        start_time = end_time - (90 * 24 * 60 * 60 * 1000)

        all_income = []
        current_start = start_time
        while current_start < end_time:
            batch = binance_service.client.futures_income_history(
                startTime=current_start,
                endTime=end_time,
                limit=1000
            )
            if not batch:
                break
            all_income.extend(batch)
            if len(batch) < 1000:
                break
            current_start = int(batch[-1]['time']) + 1

        daily = defaultdict(float)
        for item in all_income:
            if item['incomeType'] in ['REALIZED_PNL', 'COMMISSION', 'FUNDING_FEE']:
                ts = int(item['time'])
                from datetime import datetime, timezone
                date_str = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).strftime('%Y-%m-%d')
                daily[date_str] += float(item['income'])

        sorted_days = sorted(daily.keys())
        result = []
        cumulative = 0.0
        for d in sorted_days:
            cumulative += daily[d]
            result.append({
                "date": d,
                "daily_pnl": round(daily[d], 4),
                "cumulative_pnl": round(cumulative, 4)
            })
        return result
    except Exception as e:
        logger.error(f"Error fetching daily pnl: {e}", exc_info=True)
        return []

@app.get("/api/debug/income_history")
def debug_income_history():
    """查看 income history 原始数据，用于排查 Realized PnL 计算问题"""
    if not binance_service.client:
        return {"error": "Client not initialized"}
    try:
        import time as _time
        end_time = int(_time.time() * 1000)
        start_time = end_time - (90 * 24 * 60 * 60 * 1000)

        records = binance_service.client.futures_income_history(
            startTime=start_time,
            endTime=end_time,
            limit=100
        )

        pnl_sum = sum(float(r['income']) for r in records
                       if r['incomeType'] in ['REALIZED_PNL', 'COMMISSION', 'FUNDING_FEE'])

        type_counts = {}
        for r in records:
            t = r['incomeType']
            type_counts[t] = type_counts.get(t, 0) + 1

        return {
            "total_records": len(records),
            "type_counts": type_counts,
            "pnl_sum_sample": round(pnl_sum, 4),
            "calculated_total": binance_service.get_total_history_pnl(),
            "first_5": records[:5] if records else [],
            "last_5": records[-5:] if records else []
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/positions")
def get_positions():
    return binance_service.get_positions()

@app.get("/balance")
def get_balance():
    return binance_service.get_account_summary()

@app.get("/signals", response_model=List[Signal])
def get_signals(session: Session = Depends(get_session)):
    # Temporarily return empty list to hide old test data as requested
    # signals = session.exec(select(Signal)).all()
    return []

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
