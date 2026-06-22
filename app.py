import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
# CORS पूरी तरह अनलॉक ताकि फ्रंटएंड से कनेक्शन में कोई ब्लॉक न आए
CORS(app, resources={r"/*": {"origins": "*"}})

# आपका लाइव MongoDB कनेक्शन लिंक
MONGO_URI = "mongodb+srv://arena_user:Arena999@cluster0.pluvfcd.mongodb.net/?appName=Cluster0"

try:
    client = MongoClient(MONGO_URI)
    db = client['alpha_arena_db'] # आपका सही डेटाबेस नाम
    users_collection = db['users'] 
    print("MongoDB Connected Successfully!")
except Exception as e:
    print(f"MongoDB Connection Error: {e}")

@app.route('/')
def home():
    return jsonify({"status": "running", "message": "N&N Alpha Arena Backend Server is Live!"})

# 📝 रजिस्ट्रेशन API
@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.json
        if not data:
            return jsonify({"success": False, "message": "डेटा नहीं मिला!"}), 400

        first_name = data.get('firstName')
        last_name = data.get('lastName')
        mobile = str(data.get('mobile')).strip() # मोबाइल नंबर को टेक्स्ट में बदलकर स्पेस हटाना
        email = str(data.get('email')).strip().lower() # ईमेल को छोटे अक्षरों में बदलना
        password = data.get('password')
        referral = data.get('referral', '')

        # डेटाबेस में पहले से मौजूद मोबाइल या ईमेल चेक करना
        if users_collection.find_one({"mobile": mobile}):
            return jsonify({"success": False, "message": "यह मोबाइल नंबर पहले से रजिस्टर्ड है!"}), 400
        if users_collection.find_one({"email": email}):
            return jsonify({"success": False, "message": "यह ईमेल आईडी पहले से रजिस्टर्ड है!"}), 400

        # पासवर्ड सुरक्षित करना
        hashed_password = generate_password_hash(password)
        
random_uid = str(random.randint(10000000, 99999999))

        new_user = {
           "uid": random_uid,
            "first_name": first_name,
            "last_name": last_name,
            "mobile": mobile,
            "email": email,
            "password": hashed_password,
            "referral_id": referral,
            "balance": 0,
            "role": "user"
        }

        users_collection.insert_one(new_user)
        return jsonify({"success": True, "message": "Registration Successful!"}), 201

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# 🔑 लॉगिन API
@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.json
        if not data:
            return jsonify({"success": False, "message": "डेटा नहीं मिला!"}), 400

        login_id = str(data.get('loginId')).strip() # इनपुट से स्पेस हटाना
        password = data.get('password')

        # मोबाइल नंबर या ईमेल आईडी दोनों फॉर्मेट में डेटाबेस में खोजना
        user = users_collection.find_one({
            "$or": [
                {"mobile": login_id},
                {"email": login_id.lower()}
            ]
        })

        if not user:
            return jsonify({"success": False, "message": "अकाउंट नहीं मिला! कृपया पहले सही रजिस्ट्रेशन करें।"}), 404

        # पासवर्ड मैच करना
        if check_password_hash(user['password'], password):
            return jsonify({
                "success": True, 
                "message": "Login Successful!",
              "user": {"uid": user.get('uid', '00000000'), "first_name": user['first_name'], "mobile": user['mobile']}
            }), 200
        else:
            return jsonify({"success": False, "message": "गलत पासवर्ड!"}), 401

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
    