from flask import Flask
import pandas as pd

DATA_DIR = "/data/weather.csv"

weathData = pd.read_csv(DATA_DIR)

app = Flask(__name__)

@app.route('/')
def index():
    return weathData.to_string()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

