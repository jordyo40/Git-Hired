import os
from flask import Flask, request, jsonify
from pymongo import MongoClient
from bson.objectid import ObjectId
from dotenv import load_dotenv
from flask_cors import CORS
import datetime
import base64

load_dotenv()

app = Flask(__name__)
CORS(app)

# Create MongoDB connection
mongo_uri = os.getenv("MONGODB_URI")
if not mongo_uri:
    raise Exception("MONGODB_URI environment variable not set")

client = MongoClient(mongo_uri)


db = client.get_database("git-hired")
candidates_collection = db.get_collection("candidates")

#--------------------------------- API Routes ---------------------------------

@app.route("/api/candidates", methods=["POST"])
def create_candidate():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Invalid JSON"}), 400
        
        # The resume file is expected to be a base64 string
        # No special handling needed here as it's just a string in the JSON
        data["createdAt"] = datetime.datetime.now(datetime.timezone.utc)
        
        result = candidates_collection.insert_one(data)
        data["_id"] = str(result.inserted_id)
        
        return jsonify(data), 201
    except Exception as e:
        print(f"Error creating candidate: {e}")
        return jsonify({"error": "Unable to create candidate"}), 500

@app.route("/api/candidates", methods=["GET"])
def get_candidates():
    try:
        job_id = request.args.get("jobId")
        if not job_id:
            return jsonify({"error": "jobId is required"}), 400

        candidates = list(candidates_collection.find({"jobId": job_id}).sort("score", -1))
        
        for candidate in candidates:
            candidate["_id"] = str(candidate["_id"])
            
        return jsonify(candidates), 200
    except Exception as e:
        print(f"Error fetching candidates: {e}")
        return jsonify({"error": "Unable to fetch candidates"}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5001) 