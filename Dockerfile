FROM python:3.10-slim

# Set the working directory
WORKDIR /demomitra

# Copy all project files
COPY . .

# Install Python dependencies
RUN pip install -r requirements.txt

# Install os dependencies
RUN apk add --no-cache vim

# Expose the application port
EXPOSE 8000

CMD ["uvicorn", "backend:app", "--host", "0.0.0.0", "--port", "8000"]