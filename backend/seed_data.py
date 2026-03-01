from sqlmodel import Session, select
from database import engine, create_db_and_tables
from models import Signal
from datetime import datetime, timedelta

def seed_data():
    create_db_and_tables()
    with Session(engine) as session:
        # Check if data exists
        existing_signals = session.exec(select(Signal)).all()
        if existing_signals:
            print("Data already exists, skipping seed.")
            return

        print("Seeding demo signals...")
        
        signals = [
            Signal(
                symbol="BTCUSDT",
                side="BUY",
                entry_price=65000.0,
                stop_loss=64000.0,
                take_profit=67000.0,
                timestamp=datetime.utcnow() - timedelta(minutes=30),
                raw_message="Demo Signal 1"
            ),
            Signal(
                symbol="ETHUSDT",
                side="SELL",
                entry_price=3500.0,
                stop_loss=3600.0,
                take_profit=3300.0,
                timestamp=datetime.utcnow() - timedelta(hours=2),
                raw_message="Demo Signal 2"
            ),
             Signal(
                symbol="SOLUSDT",
                side="BUY",
                entry_price=145.50,
                stop_loss=140.0,
                take_profit=160.0,
                timestamp=datetime.utcnow() - timedelta(days=1),
                raw_message="Demo Signal 3"
            )
        ]
        
        for sig in signals:
            session.add(sig)
        
        session.commit()
        print("Demo signals added successfully!")

if __name__ == "__main__":
    seed_data()
