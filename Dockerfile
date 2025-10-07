FROM python:3.13-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application
COPY . .

# Expose the port NiceGUI runs on
EXPOSE 7860

# Run the application
CMD ["python", "main.py"]
