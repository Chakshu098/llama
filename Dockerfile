# --- Stage 1: Build Frontend ---
FROM node:20-slim AS frontend-builder
WORKDIR /app/dashboard-v3
COPY dashboard-v3/package*.json ./
RUN npm install
COPY dashboard-v3/ ./
RUN npm run build

# --- Stage 2: Final Image ---
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

# Copy built frontend from Stage 1
COPY --from=frontend-builder /app/dashboard-v3/dist ./dashboard-v3/dist

# Set environment variables
ENV API_BASE_URL="https://router.huggingface.co/v1"
ENV MODEL_NAME="Qwen/Qwen2.5-72B-Instruct"
ENV SERVER_URL="http://localhost:7860"
ENV HF_TOKEN=""
ENV PORT=7860

# Expose consolidated server port (Hugging Face Space requirement)
EXPOSE 7860

# Entry point: start the FastAPI server
CMD ["python", "server/app.py"]
