from flask import Flask, render_template, request, redirect
from pymongo import MongoClient
from dotenv import load_dotenv
import os
import random
import string
import datetime
import threading
import time

load_dotenv()
mongo = os.getenv('MONGO_URI')

client = MongoClient(mongo)
db = client['url_shortner']
collections = db['urls']

app = Flask(__name__)

def get_existing_code(url):
    now = datetime.datetime.utcnow()
    entry = collections.find_one({
        "url": url,
        "expiry": {"$gt": now}
    })
    return entry["short_code"] if entry else None

def generate_unique_code(length=6): 
    while True:
        code = ''.join(random.choices(string.ascii_letters + string.digits, k=length))
        if not collections.find_one({"short_code": code}):
            return code

def cleaner_job():
    def cleaner():
        while True:
            now = datetime.datetime.utcnow()
            del_count = collections.delete_many({"expiry": {"$lt": now}})
            if del_count.deleted_count:
                print(f"Cleaner removed {del_count.deleted_count} expired entires")
            time.sleep(30)
    threading.Thread(target=cleaner, daemon=True).start()

cleaner_job()

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        url = request.form['url']
        expiry_time = int(request.form['expiry'])
        short_code = get_existing_code(url)
        if not short_code:
            short_code = generate_unique_code()
            expiry = datetime.datetime.utcnow() + datetime.timedelta(minutes=expiry_time)
            collections.insert_one({
                "short_code": short_code,
                "url": url,
                "expiry": expiry
            })
        short_url = request.host_url + short_code
        return render_template('result.html', short_url=short_url, expiry=expiry_time)
    return render_template('index.html')

@app.route('/<short_code>')
def redirect_to_url(short_code):
    entry = collections.find_one({"short_code": short_code})
    if entry:
        if entry["expiry"] > datetime.datetime.utcnow():
            return redirect(entry["url"])
        else:
            collections.delete_one({"short_code": short_code})
            return "This Short Link has expired.", 410
    return "Short code not found", 404

if __name__ == "__main__":
    app.run(debug=True)
