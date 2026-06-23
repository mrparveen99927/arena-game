import os
import random
import datetime
import pytz
import time
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient

app = Flask(__name__)
CORS(app)

#    
MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://arena_user:Arena999@cluster0.pluvfcd.mongodb.net/?appName=Cluster0")
client = MongoClient(MONGO_URI)
db = client['alpha_arena_db']
users_collection = db['users']

def get_ist_time():
    return datetime.datetime.now(pytz.timezone('Asia/Kolkata'))

@app.route('/')
def home():
    return jsonify({"status": "success", "message": "Alpha Arena Backend Engine is Running Live!"}), 200

#   1:      
@app.route('/api/register', methods=['POST'])
def register_user():
    try:
        data = request.get_json() or {}
        email = data.get('email')
        mobile = data.get('mobile')
        
        if not email or not mobile:
            return jsonify({"success": False, "message": "Email and Mobile are required"}), 400
            
        existing_user = users_collection.find_one({"$or": [{"email": email}, {"mobile": mobile}]})
        if existing_user:
            return jsonify({"success": False, "message": "User already exists"}), 400

        #        - 
        real_first_name = data.get('first_name') or data.get('name') or data.get('fullName') or 'Arena'
        real_last_name = data.get('last_name') or ''

        new_user = {
            "uid": str(random.randint(10000000, 99999999)),
            "first_name": real_first_name, #     
            "last_name": real_last_name,
            "mobile": mobile,
            "email": email,
            "password": data.get('password'),
            "balance": 50.0, # 50   
            "status": "ACTIVE",
            "created_at": datetime.datetime.utcnow()
        }
        users_collection.insert_one(new_user)
        return jsonify({"success": True, "message": "Registration successful!", "uid": new_user["uid"]}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login_user():
    data = request.json
    if not data:
        return jsonify({"success": False, "message": "No data received"}), 400

    username = data.get('username') or data.get('email')
    password = data.get('password')

    if not username or not password:
        return jsonify({"success": False, "message": "Username and password are required"}), 400

    user = db.users.find_one({
        "$or": [
            {"mobile": username},
            {"email": username}
        ]
    })

    if not user:
        return jsonify({"success": False, "message": "User not found"}), 401

    if user.get('password') != password:
        return jsonify({"success": False, "status": "error", "message": "Invalid password"}), 401

    update_data = {}
    if not user.get('name'):
        full_name = f"{user.get('firstName', '')} {user.get('lastName', '')}".strip()
        update_data['name'] = full_name if full_name else "Arena User"
        
    if user.get('status') != 'active':
        update_data['status'] = 'active'
        
    if user.get('balance') is None:
        update_data['balance'] = 0

    if update_data:
        db.users.update_one({"_id": user["_id"]}, {"$set": update_data})

    return jsonify({
        "success": True,
        "status": "success",
        "message": "Login successful",
        "user_mobile": user.get('mobile'),
        "user_name": user.get('name') or update_data.get('name', 'Arena User')
    }), 200
    
@app.route('/api/user/profile', methods=['GET'])
def get_user_profile():
    try:
        uid = request.args.get('uid')
        if not uid:
            return jsonify({"success": False, "message": "UID is required"}), 400
            
        user = users_collection.find_one({"uid": uid})
        if user:
            return jsonify({
                "uid": user.get('uid'),
                "first_name": user.get('first_name'),
                "last_name": user.get('last_name'),
                "balance": user.get('balance', 0),
                "status": user.get('status')
            }), 200
        return jsonify({"success": False, "message": "User not found"}), 404
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/place-bet', methods=['POST'])
def place_bet():
    try:
        data = request.get_json() or {}
        uid = data.get('uid')
        amount = float(data.get('amount', 0))
        selected_numbers = data.get('selected_numbers', [])
        amt_per_number = data.get('amt_per_number', 0)
        round_id = data.get('round_id', 'ROUND_01')
        
        user = users_collection.find_one({"uid": uid})
        if not user or user.get('balance', 0) < amount:
            return jsonify({"status": "error", "message": "Insufficient wallet balance"}), 400
            
        users_collection.update_one({"uid": uid}, {"$inc": {"balance": -amount}})
        
        bet_doc = {
            "uid": uid,
            "round_id": round_id,
            "prediction": "95X_MATRIX",
            "amount": amount,
            "amt_per_number": amt_per_number,
            "selected_numbers": selected_numbers,
            "timestamp": datetime.datetime.utcnow(),
            "status": "pending"
        }
        db.bets.insert_one(bet_doc)
        return jsonify({"status": "success", "new_balance": user.get('balance', 0) - amount}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/admin/all-users', methods=['POST'])
def admin_all_users():
    try:
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
        return jsonify({"success": True, "users": users_list}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/game-status', methods=['GET'])
def get_game_status():
    try:
        now = get_ist_time()
        time_5pm = now.replace(hour=17, minute=0, second=0, microsecond=0)
        time_440pm = now.replace(hour=16, minute=40, second=0, microsecond=0)
        round_id = f"FD_{now.strftime('%Y%m%d')}"
        
        if now < time_440pm:
            time_remaining = int((time_440pm - now).total_seconds())
            return jsonify({"status": "OPEN", "round_id": round_id, "message": "  !", "time_remaining": time_remaining}), 200
        elif time_440pm <= now < time_5pm:
            time_remaining = int((time_5pm - now).total_seconds())
            return jsonify({"status": "CLOSED", "round_id": round_id, "message": " !    ...", "time_remaining": time_remaining}), 200
        else:
            return jsonify({"status": "RESULT_DECLARED", "round_id": round_id, "message": "        "}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/admin/dashboard-sheet', methods=['GET'])
def get_admin_dashboard_sheet():
    try:
        now = get_ist_time()
        round_id = f"FD_{now.strftime('%Y%m%d')}"
        number_sheet = {str(i): 0.0 for i in range(1, 101)}
        
        bets = db.bets.find({"round_id": round_id})
        for bet in bets:
            for num in bet.get('selected_numbers', []):
                if str(num) in number_sheet:
                    number_sheet[str(num)] += bet.get('amt_per_number', 0)
                    
        zero_money_numbers = [num for num, amt in number_sheet.items() if amt == 0]
        funded_numbers = {num: amt for num, amt in number_sheet.items() if amt > 0}
        
        highest_num = max(funded_numbers, key=funded_numbers.get) if funded_numbers else " "
        lowest_num = min(funded_numbers, key=funded_numbers.get) if funded_numbers else " "
        
        return jsonify({
            "round_id": round_id,
            "all_numbers_pool": number_sheet,
            "zero_money_numbers": zero_money_numbers,
            "highest_betted_number": highest_num,
            "lowest_betted_number": lowest_num
        }), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/admin/declare-result', methods=['POST'])
def declare_result():
    try:
        data = request.get_json() or {}
        now = get_ist_time()
        round_id = data.get('round_id') or f"FD_{now.strftime('%Y%m%d')}"
        manual_winner = data.get('winner_number')
        
        number_sheet = {str(i): 0.0 for i in range(1, 101)}
        bets_list = list(db.bets.find({"round_id": round_id, "status": "pending"}))
        
        for bet in bets_list:
            for num in bet.get('selected_numbers', []):
                if str(num) in number_sheet:
                    number_sheet[str(num)] += bet.get('amt_per_number', 0)

        if manual_winner:
            final_winner = str(manual_winner)
        else:
            zero_money_numbers = [num for num, amt in number_sheet.items() if amt == 0]
            if zero_money_numbers:
                final_winner = random.choice(zero_money_numbers)
            else:
                final_winner = min(number_sheet, key=number_sheet.get)

        db.results.update_one(
            {"round_id": round_id},
            {"$set": {"winner": int(final_winner), "declared_at": datetime.datetime.utcnow()}},
            upsert=True
        )

                # ---         ---
        for bet in bets_list:
            if int(final_winner) in bet.get('selected_numbers', []):
                winning_amount = bet.get('amt_per_number', 0) * 95
                users_collection.update_one({"uid": bet['uid']}, {"$inc": {"balance": winning_amount}})
                db.bets.update_one({"_id": bet['_id']}, {"$set": {"status": "WIN", "payout": winning_amount}})
            else:
                db.bets.update_one({"_id": bet['_id']}, {"$set": {"status": "LOSE", "payout": 0}})

                return jsonify({"status": "success", "winner_declared": final_winner, "message": "Result successfully declared!"}), 200
                
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
        # ==========================================
# 🕒 STEP 1: GAME STATUS & TIMING ENDPOINT (यहाँ जोड़ें)
# ==========================================
from datetime import datetime
import pytz

IST = pytz.timezone('Asia/Kolkata')

@app.route('/api/game-status', methods=['GET'])
def get_game_status():
    try:
        now_ist = datetime.now(IST)
        current_time = now_ist.strftime("%H:%M")
        
        lock_time = "16:40"
        result_time = "17:00"
        
        if lock_time <= current_time < result_time:
            return jsonify({
                "status": "closed",
                "message": "Betting Closed. Waiting for Result...",
                "server_time": current_time
            })
        else:
            return jsonify({
                "status": "open",
                "message": "Betting is Live!",
                "server_time": current_time
            })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
        @app.route('/api/admin/dashboard-sheet', methods=['GET'])
def get_admin_dashboard_sheet():
    try:
        # 1 से 100 तक के सभी नंबरों के लिए ₹0 का शुरुआती पूल बनाएं
        sheet_data = {str(i): 0 for i in range(1, 101)}
        
        # डेटाबेस से सभी PENDING (एक्टिव) बेट्स निकालें
        active_bets = db.bets.find({"status": "PENDING"})
        
        for bet in active_bets:
            numbers = bet.get('numbers', [])
            amount_per_num = int(bet.get('amount_per_number', 0))
            for num in numbers:
                if str(num) in sheet_data:
                    sheet_data[str(num)] += amount_per_num

        sorted_sheet = sorted(sheet_data.items(), key=lambda x: x[1])
        highest_betted = sorted_sheet[-1][0] if sorted_sheet[-1][1] > 0 else "None"
        
        lowest_betted = "None"
        for num, amt in sorted_sheet:
            if amt > 0:
                lowest_betted = num
                break
                
        zero_money_numbers = [num for num, amt in sheet_data.items() if amt == 0]

        return jsonify({
            "status": "success",
            "sheet": sheet_data,
            "tags": {
                "highest": highest_betted,
                "lowest": lowest_betted,
                "zero_count": len(zero_money_numbers)
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
        
        

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
    