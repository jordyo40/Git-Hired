import os
from flask import Flask, request, jsonify, send_file
from pymongo import MongoClient
from bson.objectid import ObjectId
from dotenv import load_dotenv
from flask_cors import CORS
import datetime
import base64
import gridfs
import io
import binascii

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
fs = gridfs.GridFS(db)

def make_serializable(doc):
    if doc is None:
        return None
    if "_id" in doc:
        doc["id"] = str(doc["_id"])
        del doc["_id"]
    if "createdAt" in doc and isinstance(doc["createdAt"], datetime.datetime):
        doc["createdAt"] = doc["createdAt"].isoformat()
    # Recursively check for nested objects, which is not strictly necessary for the current structure but good practice
    for key, value in doc.items():
        if isinstance(value, list):
            doc[key] = [make_serializable(v) if isinstance(v, dict) else v for v in value]
        elif isinstance(value, dict):
            doc[key] = make_serializable(value)
    return doc

#--------------------------------- API Routes ---------------------------------

@app.route("/api/candidates", methods=["POST"])
def create_candidate():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Invalid JSON"}), 400
        
        # The resume file is expected to be a base64 string
        if "resumeFile" not in data or "data" not in data["resumeFile"]:
            return jsonify({"error": "resumeFile data is missing"}), 400
            
        resume_file_data = data.pop("resumeFile")
        
        try:
            # Decode the base64 string to bytes
            file_bytes = base64.b64decode(resume_file_data["data"])
            # Store the file in GridFS and get its ID
            file_id = fs.put(
                file_bytes, 
                filename=data.get("filename", "untitled.dat"), 
                contentType=resume_file_data.get("type")
            )
            data["resumeFileId"] = str(file_id)
            data["resumeFileType"] = resume_file_data.get("type")
        except (ValueError, TypeError) as e:
            print(f"Base64 decode error: {e}")
            return jsonify({"error": "Invalid base64 data for resume file"}), 400

        data["createdAt"] = datetime.datetime.now(datetime.timezone.utc)
        
        result = candidates_collection.insert_one(data)
        
        # Fetch the inserted document to ensure we have the correct data from DB
        new_candidate = candidates_collection.find_one({"_id": result.inserted_id})
        
        return jsonify(make_serializable(new_candidate)), 201
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
        
        serializable_candidates = [make_serializable(c) for c in candidates]
            
        return jsonify(serializable_candidates), 200
    except Exception as e:
        print(f"Error fetching candidates: {e}")
        return jsonify({"error": "Unable to fetch candidates"}), 500

@app.route("/api/resumes/<candidate_id>", methods=["GET"])
def get_resume_file(candidate_id):
    try:
        candidate = candidates_collection.find_one({"_id": ObjectId(candidate_id)})
        if not candidate or "resumeFileId" not in candidate:
            return jsonify({"error": "Resume not found"}), 404
        
        file_id = ObjectId(candidate["resumeFileId"])
        grid_out = fs.get(file_id)

        return send_file(
            io.BytesIO(grid_out.read()),
            mimetype=grid_out.content_type,
            as_attachment=False, # Set to True to force download
            download_name=grid_out.filename
        )

    except Exception as e:
        print(f"Error fetching resume file: {e}")
        return jsonify({"error": "Unable to fetch resume file"}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5001) 