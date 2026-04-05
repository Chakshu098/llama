# Use Python 3.13 as requested for the hackathon
FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Set environment variables
ENV API_BASE_URL="https://router.huggingface.co/v1"
ENV MODEL_NAME="Qwen/Qwen2.5-72B-Instruct"
ENV SERVER_URL="http://localhost:7860"
ENV HF_TOKEN=""

# Expose consolidated server port (Hugging Face requirement)
EXPOSE 7860

# Entry point: start the FastAPI server which also serves the React Dashboard
CMD ["python", "server/app.py"]
