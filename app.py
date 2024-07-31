import yaml
from pymongo import MongoClient, errors
from flask import Flask, request, jsonify
import urllib.parse
from datetime import datetime
from bson import ObjectId
import json
from werkzeug.utils import secure_filename
import os

print("Starting script...")

# MongoDB Atlas Credentials
username = ""
password = ""

# URL encode the username and password
encoded_username = urllib.parse.quote_plus(username)
encoded_password = urllib.parse.quote_plus(password)

# MongoDB Atlas Connection String
CONNECTION_STRING = f"mongodb+srv://{encoded_username}:{encoded_password}@finalproject.meoloox.mongodb.net/?retryWrites=true&w=majority&tls=true&tlsAllowInvalidCertificates=true&appName=finalProject"

print("Connecting to MongoDB Atlas...")

try:
    # Initialize MongoDB Client
    client = MongoClient(CONNECTION_STRING)
    # Trigger a server request to check the connection
    client.server_info()
    db = client['geospatial_db']
    geospatial_collection = db['geospatial_images']
    image_collection = db['images']
    print("Connected to MongoDB Atlas.")
except errors.ServerSelectionTimeoutError as err:
    print("Failed to connect to MongoDB Atlas:", err)
    exit(1)

print("Loading YAML file...")

# Load the YAML file
yaml_file_path = 'C:/Users/tibir/Documents/final-project-uoft/coordinates_1.yaml'
try:
    with open(yaml_file_path, 'r') as file:
        coordinates_data = yaml.safe_load(file)
    print("YAML file loaded.")
except Exception as e:
    print(f"Error loading YAML file: {e}")
    exit(1)

# Get the current date and time
current_datetime = datetime.now()

print("Inserting data into MongoDB...")

# Insert YAML Data into MongoDB
try:
    for idx, record in enumerate(coordinates_data):
        geospatial_record = {
            "image_id": idx,  # Generate a simple ID
            "CRS": record.get('CRS'),
            "coordinates": record.get('coords'),
            "metadata": {
                "date": record.get('date'),
                "added_date": current_datetime,
                "updated_date": current_datetime
            }
        }
        geospatial_collection.update_one(
            {"image_id": idx},
            {"$set": geospatial_record, "$setOnInsert": {"added_date": current_datetime}},
            upsert=True
        )
    print("Data insertion complete.")
except Exception as e:
    print(f"Error inserting data into MongoDB: {e}")
    exit(1)

# Custom JSON Encoder for Flask to handle ObjectId
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        return super().default(obj)

print("Setting up Flask application...")

# Initialize Flask App
app = Flask(__name__)
app.json_encoder = CustomJSONEncoder

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def convert_objectid_to_string(data):
    """Helper function to convert ObjectId to string in the returned data"""
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                for key, value in item.items():
                    if isinstance(value, ObjectId):
                        item[key] = str(value)
    elif isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, ObjectId):
                data[key] = str(value)
    return data

@app.route('/geospatial', methods=['GET'])
def get_geospatial_data():
    print("Received request to /geospatial")
    date = request.args.get('date')
    CRS = request.args.get('CRS')

    query = {}
    if date:
        query['metadata.date'] = date
    if CRS:
        query['CRS'] = CRS

    print(f"Query: {query}")

    try:
        results = geospatial_collection.find(query)
        data = list(results)
        data = convert_objectid_to_string(data)
        print(f"Retrieved data: {data}")
        return jsonify(data)
    except Exception as e:
        print(f"Error retrieving data: {e}")
        return jsonify({"error": f"Failed to retrieve data: {e}"}), 500

@app.route('/upload_image', methods=['POST'])
def upload_image():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    if file:
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        # Save file to MongoDB
        with open(os.path.join(app.config['UPLOAD_FOLDER'], filename), "rb") as image_file:
            image_data = image_file.read()
            image_record = {
                "filename": filename,
                "data": image_data,
                "upload_date": datetime.now()
            }
            image_collection.insert_one(image_record)
        
        return jsonify({"message": "File uploaded successfully"}), 201

# Add the new endpoint to list images
@app.route('/list_images', methods=['GET'])
def list_images():
    try:
        images = image_collection.find()
        image_list = []
        for image in images:
            image_list.append({
                "filename": image.get("filename"),
                "upload_date": image.get("upload_date").strftime("%Y-%m-%d %H:%M:%S"),
                "id": str(image.get("_id"))
            })
        return jsonify(image_list), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("Starting Flask server...")
    app.run(debug=True)
