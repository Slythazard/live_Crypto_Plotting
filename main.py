import threading
from threading import Lock
from queue import Queue,Empty
from logging import Logger
from dotenv import load_dotenv
import os
import requests
from flask import Flask, render_template, request, url_for
from flask_socketio import SocketIO,disconnect
import datetime
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()
api_key =os.getenv("api_key")
app = Flask(__name__)
socket = SocketIO(app)
url = "https://api.coincap.io/v2/assets"
headers = {"Authorization":f"Bearer {api_key}"}

clients={}
dtque=Queue()
clients_lock= Lock()

@app.route('/')
def index():
    return render_template('index.html')

@socket.on('messageOnConnection')
def handle_msgOnConn(data):
    global clients,dtque
    sid = request.sid
    logger.info(f"New Client Connected:{sid}")
    try:
        latest_data = dtque.get(timeout=1.2)
        socket.emit('messageOnReceivingConnectionToClient', latest_data)
    except Empty:
        logger.warning(f"No data available for client {sid} at connection.")

@socket.on("msgOnRcvConnToClntRevert")
def msgOnRcvConnToClntRevert_handler():
    sid = request.sid
    with clients_lock:
        if sid not in clients:
            stop_event = threading.Event()
            thread=threading.Thread(target= emitter_cl,args=(sid,),daemon=True)
            thread.start()
            clients[sid]={"thread":thread,"stop_event":stop_event}
            logger.info(f"Started thread for client {sid}")

@socket.on('disconnect')
def handle_disconnect():
    global clients
    sid = request.sid
    with clients_lock:
        if sid in clients:
            clients[sid]['stop_event'].set()
            thread = clients[sid]["thread"]
            thread.join(timeout=2.0)
            logger.info(f"Client disconnected:{sid}{clients[sid]}")
            clients.pop(sid)
        else:
            logger.info(f"{clients[sid]} not in client session")

def formatTime(time_c):
    time_d= datetime.datetime.fromtimestamp(time_c/1000)
    time_e= time_d.timetuple()
    time_f= time.strftime('%H:%M:%S',time_e)

    return time_f

def emitter_cl(sid):
    global dtque,clients
    while True:
        with clients_lock:
            if sid in clients:
                while not clients[f"{sid}"]['stop_event'].is_set():
                    try:
                        if not dtque.empty():
                            data=dtque.get(timeout=0.1)
                            socket.emit('update_price',data)
                            time.sleep(0.1)
                    except Empty:
                        logger.info(f"Queue is empty for client {sid}")

def main_fetcher():
    while True:
        data = fetcher()
        if data:
            dtque.put(data)
        time.sleep(1)

def fetcher():
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            priceUsd = data['data'][0]['priceUsd']
            time_c = data['timestamp']
            time_g = formatTime(time_c)
            return {'price': priceUsd, 'time': time_g}
        else:
            logger.error(f"API request failed with status code {response.status_code}: {response.text}")
            return None
    except requests.RequestException as e:
        logger.error(f"Error fetching data from API: {e}")
        return None

if __name__=='__main__':
    socket.start_background_task(target=main_fetcher)
    logger.info("Fetcher Fetching........")
    socket.run(app=app, port=5500, debug=True,allow_unsafe_werkzeug=True)

