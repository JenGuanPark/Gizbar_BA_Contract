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

class SignalPayload(BaseModel):
    symbol: str
    side: str
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    quantity: Optional[float] = None
    usdt_amount: Optional[float] = None # New: specify quantity by USDT amount
    leverage: Optional[int] = 10

@app.post("/webhook")
def receive_signal(payload: SignalPayload, session: Session = Depends(get_session)):
    # Log signal to DB
    signal = Signal(
        symbol=payload.symbol,
        side=payload.side,
        entry_price=payload.entry_price,
        stop_loss=payload.stop_loss,
        take_profit=payload.take_profit,
        raw_message=str(payload.dict())
    )
    session.add(signal)
    session.commit()
    session.refresh(signal)

    # Execute trade logic
    # Priority: 1. quantity from signal, 2. calculated from usdt_amount, 3. default small amount
    quantity = payload.quantity
    if not quantity and payload.usdt_amount:
        quantity = binance_service.calculate_quantity_by_usdt(
            payload.symbol, 
            payload.usdt_amount, 
            payload.leverage
        )
    
    if not quantity:
        quantity = 0.001 # Default small amount for safety

    try:
        if payload.side.upper() == "CLOSE":
             order = binance_service.close_position(symbol=payload.symbol)
        else:
             order = binance_service.place_order(
                symbol=payload.symbol,
                side=payload.side,
                quantity=quantity,
                leverage=payload.leverage,
                stop_loss=payload.stop_loss,
                take_profit=payload.take_profit
             )
        
        # Log trade to DB
        if "orderId" in order:
             trade = Trade(
                signal_id=signal.id,
                symbol=payload.symbol,
                side=payload.side,
                order_id=str(order["orderId"]),
                price=float(order["avgPrice"]) if "avgPrice" in order else 0.0,
                quantity=quantity,
                status="FILLED"
             )
             session.add(trade)
             session.commit()
             return {"status": "success", "order": order}
        else:
             return {"status": "error", "message": str(order)}

    except Exception as e:
        return {"status": "error", "message": str(e)}

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

@app.get("/positions")
def get_positions():
    return binance_service.get_positions()

@app.get("/balance")
def get_balance():
    return binance_service.get_account_summary()

@app.get("/signals", response_model=List[Signal])
def get_signals(session: Session = Depends(get_session)):
    signals = session.exec(select(Signal)).all()
    return signals

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
