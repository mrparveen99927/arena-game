import os
import random
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
# CORS पूरी तरह अनलॉक ताकि फ्रंटएंड कनेक्शन में कोई रुकावट न आए
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

# 📝 1. रजिस्ट्रेशन API (UID जनरेशन लॉजिक के साथ)
@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.json
        if not data:
            return jsonify({"success": False, "message": "डेटा नहीं मिला!"}), 400

        first_name = data.get('firstName')
        last_name = data.get('lastName')
        mobile = str(data.get('mobile')).strip()
        email = str(data.get('email')).strip().lower()
        password = data.get('password')
        referral = data.get('referral', '')

        if users_collection.find_one({"mobile": mobile}):
            return jsonify({"success": False, "message": "यह मोबाइल नंबर पहले से रजिस्टर्ड है!"}), 400
        if users_collection.find_one({"email": email}):
            return jsonify({"success": False, "message": "यह ईमेल आईडी पहले से रजिस्टर्ड है!"}), 400

        hashed_password = generate_password_hash(password)

        # 🎯 रेंडर क्रैश एरर को यहाँ पूरी तरह फिक्स कर दिया गया है
        generated_uid = str(random.randint(10000000, 99999999))

        new_user = {
            "uid": generated_uid,
            "first_name": first_name,
            "last_name": last_name,
            "mobile": mobile,
            "email": email,
            "password": hashed_password,
            "referral_id": referral,
            "balance": 50,
            "bonus_claimed": False,
            "role": "user"
        }

        users_collection.insert_one(new_user)
        return jsonify({"success": True, "message": "Registration Successful!"}), 201

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# 🔑 2. लॉगिन API (UID रिस्पॉन्स लॉजिक के साथ)
@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.json
        if not data:
            return jsonify({"success": False, "message": "डेटा नहीं मिला!"}), 400

        login_id = str(data.get('loginId')).strip()
        password = data.get('password')

        user = users_collection.find_one({
            "$or": [
                {"mobile": login_id},
                {"email": login_id.lower()}
            ]
        })

        if not user:
            return jsonify({"success": False, "message": "अकाउंट नहीं मिला! कृपया पहले सही रजिस्ट्रेशन करें।"}), 404

        if check_password_hash(user['password'], password):
            current_balance = user.get('balance', 0)
            bonus_given = 0
            
            if not user.get('bonus_claimed', False):
                bonus_given = random.randint(1, 50)
                current_balance += bonus_given
                users_collection.update_one(
                    {"_id": user["_id"]},
                    {"$set": {"balance": current_balance, "bonus_claimed": True}}
                )

            return jsonify({
                "success": True, 
                "message": "Login Successful!",
                "user": {
                    "uid": user.get('uid', '00000000'),
                    "first_name": user['first_name'],
                    "mobile": user['mobile'],
                    "balance": current_balance
                }
            }), 200
        else:
            return jsonify({"success": False, "message": "गलत पासवर्ड!"}), 401

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
        # 📊 3. एडमिन ओवरव्यू के लिए सभी यूज़र्स का पूरा लाइव डेटा खींचने का API
@app.route('/api/admin/all-users', methods=['POST'])
def admin_all_users():
    try:
        # मोंगोडीबी के 'users' कलेक्शन से सारे यूज़र्स का पूरा डेटा उठाना
        all_users_cursor = users_collection.find()
        users_list = []
        
        for user in all_users_cursor:
            users_list.append({
                "uid": user.get('uid', '00000000'),
                "first_name": user.get('first_name', 'Arena Player'),
                "last_name": user.get('last_name', ''),
                "mobile": user.get('mobile', ''),
                "email": user.get('email', '--'),
                "balance": user.get('balance', 0),
                "status": user.get('status', 'ACTIVE')
            })
            
        # सीपैनल टेबल को सारा डेटा लाइव रिस्पॉन्स में भेज देना
        return jsonify({"success": True, "users": users_list}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
        

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
    