from typing import Optional
from sqlmodel import Field, SQLModel
from datetime import datetime

class Signal(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    symbol: str
    side: str  # BUY or SELL
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    raw_message: str

class Trade(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    signal_id: Optional[int] = Field(default=None, foreign_key="signal.id")
    symbol: str
    side: str
    order_id: str
    price: float
    quantity: float
    status: str  # OPEN, CLOSED, FILLED
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    pnl: Optional[float] = None
