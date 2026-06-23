import os
from datetime import datetime
import pytz
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from bson.objectid import ObjectId

app = Flask(__name__)
CORS(app)  # CORS एरर रोकने के लिए

# 🔑 1. MASTER DATABASE CONNECTION
MONGO_URI = "mongodb+srv://arena_user:Arena999@cluster0.pluvfcd.mongodb.net/?appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client['alpha_arena_db']

# भारतीय समय क्षेत्र (IST) सेट करें
IST = pytz.timezone('Asia/Kolkata')

@app.route('/')
def home():
    return jsonify({"status": "running", "message": "Alpha Arena Backend is Live!"}), 200

# 🎯 2. NEW USER REGISTRATION WITH ₹50 BONUS
# 🎯 2. NEW USER REGISTRATION WITH ₹50 BONUS
@app.route('/api/register', methods=['POST'])
def register_user():
    try:
        data = request.json or {}
        first_name = data.get('firstName') or data.get('first_name') or ""
        last_name = data.get('lastName') or data.get('last_name') or ""
        name = data.get('name') or f"{first_name} {last_name}".strip()
        mobile = data.get('mobile')
        email = data.get('email')
        password = data.get('password')

        if not name or not mobile or not password:
            return jsonify({"success": False, "message": "Required fields are missing"}), 400

        # चेक करें कि यूजर पहले से है या नहीं
        existing_user = db.users.find_one({"mobile": mobile})
        if existing_user:
            return jsonify({"success": False, "message": "Mobile number already registered"}), 400

        # नया यूजर ढांचा (₹50 बोनस कॉइन्स के साथ)
        new_user = {
            "name": name,
            "mobile": mobile,
            "email": email,
            "password": password,
            "balance": 50,
            "status": "active",
            "created_at": datetime.now(IST)
        }
        db.users.insert_one(new_user)
        return jsonify({"success": True, "message": "Registration successful!"}), 201
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# 🔑 3. ERROR-FREE LOGIN & AUTO-FIX FOR OLD USERS
@app.route('/api/login', methods=['POST'])
def login_user():
    try:
        data = request.json or {}
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
            return jsonify({"success": False, "message": "Invalid password"}), 401

        # पुराने यूजर्स का डेटा लाइव सिंक (ऑटो-फिक्स)
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
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# 🕒 4. GAME TIMING & COUNTDOWN STATUS (4:40 PM LOCK)
@app.route('/api/game-status', methods=['GET'])
def get_game_status():
    try:
        mobile = request.args.get('mobile')
        user_balance = 0
        if mobile:
            user = db.users.find_one({"mobile": mobile})
            if user:
                user_balance = user.get('balance', 0)

        now_ist = datetime.now(IST)
        current_time = now_ist.strftime("%H:%M")
        lock_time = "16:40"
        result_time = "17:00"

        if lock_time <= current_time < result_time:
            return jsonify({
                "status": "closed",
                "message": "Betting Closed. Waiting for Result...",
                "server_time": current_time,
                "balance": user_balance
            }), 200
        else:
            return jsonify({
                "status": "open",
                "message": "Betting is Live!",
                "server_time": current_time,
                "balance": user_balance
            }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# 🎰 5. PLACE BET WITH WALLET DEDUCTION (₹5 - ₹100 LIMITS)
@app.route('/api/place-bet', methods=['POST'])
def place_bet():
    try:
        data = request.json or {}
        user_id = data.get('user_id')
        selected_numbers = data.get('numbers', [])
        amount_per_number = data.get('amount')
        round_id = data.get('round_id', 'DAILY_FARIDABAD')

        if not user_id or not selected_numbers or not amount_per_number:
            return jsonify({"status": "error", "message": "Incomplete bet data"}), 400

        try:
            amount_per_number = int(amount_per_number)
        except ValueError:
            return jsonify({"status": "error", "message": "Invalid amount format"}), 400

        if amount_per_number < 5 or amount_per_number > 100:
            return jsonify({"status": "error", "message": "Bet limit must be between ₹5 and ₹100 per number"}), 400

        total_bet_amount = len(selected_numbers) * amount_per_number

        user = db.users.find_one({"mobile": user_id})
        if not user:
            return jsonify({"status": "error", "message": "User not found"}), 404

        current_balance = int(user.get('balance', 0))
        if current_balance < total_bet_amount:
            return jsonify({"status": "error", "message": "Insufficient balance! Please recharge."}), 400

        # वॉलेट से पैसे काटें
        new_balance = current_balance - total_bet_amount
        db.users.update_one({"mobile": user_id}, {"$set": {"balance": new_balance}})

        # बेट लॉग सुरक्षित करें
        bet_log = {
            "user_id": user_id,
            "numbers": selected_numbers,
            "amount_per_number": amount_per_number,
            "total_amount": total_bet_amount,
            "round_id": round_id,
            "status": "PENDING",
            "created_at": datetime.now(IST)
        }
        db.bets.insert_one(bet_log)

        return jsonify({
            "status": "success",
            "message": "Bet placed successfully!",
            "new_balance": new_balance
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# 📊 6. CPANEL LIVE SATTA SHEET VIEW (RISK ANALYSIS)
@app.route('/api/admin/dashboard-sheet', methods=['GET'])
def get_admin_dashboard_sheet():
    try:
        sheet_data = {str(i): 0 for i in range(1, 101)}
        active_bets = list(db.bets.find({"status": "PENDING"}))

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
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# 🏆 7. ADMIN DECLARE RESULT & MIN-LOAD AUTOWINNER (95x PAYOUT)
@app.route('/api/admin/declare-result', methods=['POST'])
def declare_result():
    try:
        data = request.json or {}
        winning_number = data.get('winning_number')
        round_id = "DAILY_FARIDABAD"

        if not winning_number:
            sheet_data = {str(i): 0 for i in range(1, 101)}
            active_bets = list(db.bets.find({"status": "PENDING"}))
            
            for bet in active_bets:
                for num in bet.get('numbers', []):
                    if str(num) in sheet_data:
                        sheet_data[str(num)] += int(bet.get('amount_per_number', 0))

            zero_money_numbers = [num for num, amt in sheet_data.items() if amt == 0]
            if zero_money_numbers:
                winning_number = zero_money_numbers[0]
            else:
                winning_number = min(sheet_data, key=sheet_data.get)

        winning_number = int(winning_number)

        db.results.insert_one({
            "winning_number": winning_number,
            "round_id": round_id,
            "declared_at": datetime.now(IST)
        })

                # 🏆 7. ADMIN DECLARE RESULT (कंटिन्यूड...)
        active_bets = list(db.bets.find({"status": "PENDING", "round_id": round_id}))
        for bet in active_bets:
            user_id = bet.get('user_id')
            numbers = bet.get('numbers', [])
            amount_per_num = int(bet.get('amount_per_number', 0))

            if winning_number in numbers:
                payout = amount_per_num * 95
                db.users.update_one({"mobile": user_id}, {"$inc": {"balance": payout}})
                db.bets.update_one({"_id": bet["_id"]}, {"$set": {"status": "WIN", "payout": payout}})
            else:
                # ❌ लूज़र बेट्स का स्टेटस LOSE सेट करें
                db.bets.update_one({"_id": bet["_id"]}, {"$set": {"status": "LOSE", "payout": 0}})

        return jsonify({
            "status": "success",
            "message": f"Result {winning_number} successfully declared and 95x payouts distributed!"
        }), 200
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ⚙️ SERVER MAIN START COMMAND (RENDER DEPLOYMENT ENGINE)
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
    