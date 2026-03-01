from backend.binance_service import binance_service

# Mock exchange info for testing
binance_service.exchange_info = {
    "BTCUSDT": {
        "quantity_precision": 3,
        "price_precision": 2,
        "min_qty": 0.001,
        "step_size": 0.001,
        "tick_size": 0.01
    }
}

qty, price = binance_service._apply_precision("BTCUSDT", quantity=0.12345, price=50000.1234)
print(f"Original: 0.12345, 50000.1234")
print(f"Rounded:  {qty}, {price}")

assert qty == 0.123
assert price == 50000.12

print("Precision test passed!")
