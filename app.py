from flask import Flask, render_template
import datetime 
import numpy as np
#import pandas as pd
#from charts.bar_chart import plot_chart
import json
import plotly
import plotly.express as px
from plotly.subplots import make_subplots


from sqlite3 import Error
import sqlite3

DATA_FILE = "/data/weather.db"

SQL_getLast = "SELECT * FROM weather ORDER BY column DESC LIMIT 1"
SQL_getTable = "SELECT * FROM weather"

def connectDB():
    DB_conn = None
    try:
        DB_conn = sqlite3.connect(DATA_FILE)
    except Error as e:
        print(e)
    return DB_conn

def getDBtable():
    '''get the result as a 2d array'''
    database = connectDB()
    try:
        cur = database.cursor()
        cur.row_factory = lambda cursor, row: list(row)
        # now add the actual data
        cur.execute(SQL_getTable)
        #database.commit()
    except Error as e:
        print(e)
    return cur.fetchall()


# FLASK APP
app = Flask(__name__)


@app.route('/')
def index():
    latest = getDBtable()[-1]
    time = datetime.datetime.fromtimestamp( latest[0] ).strftime('%c')
    inner = str(latest[1]) + u'\u00b0' + 'F, ' + str(latest[2]) + '%'
    outer = str(latest[3]) + u'\u00b0' + 'F, ' + str(latest[4]) + '%'
    return render_template('index.html', time=time, inner=inner, outer=outer)

@app.route('/graph')
def graph():
    obs = getDBtable()
    return render_template('chart.html', data=obs)




if __name__ == '__main__':
    #data  = np.array(getDBtable())
    app.run(debug=False, host='0.0.0.0')
