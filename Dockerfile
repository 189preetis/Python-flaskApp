FROM python:3.11-slim

WORKDIR /usr/src/app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run the create_table.py script to initialize the database
RUN python create_table.py

EXPOSE 8080

CMD ["python","flask", "run", "--host=0.0.0.0", "--port=8080"]

