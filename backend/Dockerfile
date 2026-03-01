FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Run the application
# Use 0.0.0.0 to allow external access (important for Docker networking)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
