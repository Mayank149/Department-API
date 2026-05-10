from fastapi import FastAPI
from pydantic import BaseModel
import joblib
import time
import psycopg2
import time

app = FastAPI()
model = joblib.load("department_model_v1.pkl")

conn = None

for i in range(5):  # retry 5 times
    try:
        conn = psycopg2.connect(
            host="db",
            database="predictions_db",
            user="user",
            password="password"
        )
        print("Connected to PostgreSQL")
        break
    except Exception as e:
        print("DB not ready, retrying...", e)
        time.sleep(2)

if conn is None:
    raise Exception("Could not connect to database")

cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS predictions (
    id SERIAL PRIMARY KEY,
    text_input TEXT,
    prediction TEXT,
    latency FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
""")

conn.commit()
cursor.close()


class TextInput(BaseModel):
    text : str

@app.get("/")
def root():
    return {"message" : "API is working v2"}

@app.post("/predict")
def predict(data : TextInput):
    start_time = time.time()
    result = model.predict([data.text])[0]
    latency = round((time.time() - start_time)*1000, 2)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO predictions (text_input, prediction, latency) VALUES (%s, %s, %s)",
        (data.text, result, latency)
    )
    conn.commit()
    cursor.close()

    return {
        "result" : result,
        "latency" : latency
        }