from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
import os

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# "    ()          "
MONGO_URI = os.getenv("MONGO_URI")

try:
    client = MongoClient(MONGO_URI)
    db = client['arena_game_db']
    users_collection = db['users']
    deposits_collection = db['deposits']
    cashouts_collection = db['cashouts']
    print("MongoDB Connected Successfully! 🎉")
except Exception as e:
    print(f"Database Connection Error: {e}")

@app.route('/')
def home():
    return "N&N ALPHA ARENA API SERVER IS RUNNING!"

# 1. यूजर लॉगिन और रजिस्ट्रेशन API
@app.route('/api/auth', methods=['POST'])
def user_auth():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({"success": False, "message": "सभी फ़ील्ड ज़रूरी हैं।"}), 400
        
    user = users_collection.find_one({"username": username})
    
    if user:
        if user['password'] == password:
            return jsonify({"success": True, "type": "login", "username": username, "balance": user.get('balance', 0)})
        else:
            return jsonify({"success": False, "message": "गलत पासवर्ड!"})
    else:
        # नया यूजर ऑटोमैटिक रजिस्टर होगा ₹0 बैलेंस के साथ
        users_collection.insert_one({"username": username, "password": password, "balance": 0})
        return jsonify({"success": True, "type": "register", "username": username, "balance": 0})

# 2. cPanel के लिए: सभी यूज़र्स का डेटा देखने की API
@app.route('/api/admin/users', methods=['GET'])
def get_all_users():
    users = list(users_collection.find({}, {"_id": 0}))
    return jsonify({"success": True, "users": users})

# 3. cPanel के लिए: यूज़र बैलेंस अपडेट करने की API (डिपॉजिट/कैशआउट अप्रूवल)
@app.route('/api/admin/update-balance', methods=['POST'])
def update_balance():
    data = request.json
    username = data.get('username')
    amount = float(data.get('amount')) # अमाउंट प्लस या माइनस हो सकता है
    
    user = users_collection.find_one({"username": username})
    if not user:
        return jsonify({"success": False, "message": "यूज़र नहीं मिला।"}), 404
        
    new_balance = user.get('balance', 0) + amount
    users_collection.update_one({"username": username}, {"$set": {"balance": new_balance}})
    return jsonify({"success": True, "new_balance": new_balance})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
    