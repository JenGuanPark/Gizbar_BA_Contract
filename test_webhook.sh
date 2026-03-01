#!/bin/bash
# 这是一个测试脚本，用于验证你的 Webhook 是否配置正确
# 可以在阿里云服务器上直接运行

echo "正在发送测试信号 (Test Signal)..."

curl -X POST "http://127.0.0.1:8000/webhook?token=my_secure_webhook_secret" \
     -H "Content-Type: application/json" \
     -d '{
           "symbol": "ETHUSDT", 
           "price": 2000, 
           "action": "OPEN_LONG", 
           "timestamp": 1700000000, 
           "raw_signal": "✅ 这是一个测试信号\n🛑 止损(SL): 1900\n✅ 止盈(TP): 2200"
         }'

echo -e "\n\n如果看到 status: success，说明接口正常！"
