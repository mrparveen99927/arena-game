import os
import sys
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
import pytz

app = Flask(__name__)
CORS(app)

#  1.   
MONGO_URI = "mongodb+srv://arena_user:Arena999@cluster0.pluvfcd.mongodb.net/?appName=Cluster0"

try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client['alpha_arena_db']
    client.server_info()
    print("SUCCESS: Connected to MongoDB Atlas smoothly!")
except Exception as e:
    print(f"DATABASE CONNECTION ERROR: {str(e)}")
    sys.exit(1)

IST = pytz.timezone('Asia/Kolkata')

@app.route('/')
def home():
    return jsonify({
        "status": "running",
        "message": "Alpha Arena New Backend is Live!"
    }), 200

#  2.   
@app.route('/api/register', methods=['POST'])
def register_user():
    try:
        data = request.json or {}
        first_name = data.get('firstName', '').strip()
        last_name = data.get('lastName', '').strip()
        name = f"{first_name} {last_name}".strip() or data.get('name', 'Arena Player').strip()
        mobile = data.get('mobile', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()
        referral = data.get('referral', '').strip()

        if not name or not mobile or not password:
            return jsonify({"success": False, "message": "   !"}), 400

        existing_user = db.users.find_one({"mobile": mobile})
        if existing_user:
            return jsonify({"success": False, "message": "    !"}), 400

        new_user = {
            "name": name, "mobile": mobile, "email": email, "password": password,
            "balance": 50.0, "status": "active", "referral_by": referral, "created_at": datetime.now(IST)
        }
        db.users.insert_one(new_user)
        return jsonify({"success": True, "message": " !"}), 201
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
        #  3.   
@app.route('/api/login', methods=['POST'])
def login_user():
    try:
        data = request.json or {}
        username = data.get('email', '').strip() or data.get('mobile', '').strip()
        password = data.get('password', '').strip()

        if not username or not password:
            return jsonify({"success": False, "message": "  !"}), 400

        user = db.users.find_one({"$or": [{"mobile": username}, {"email": username}]})
        if not user or user.get('password') != password:
            return jsonify({"success": False, "message": " !"}), 401
        if user.get('status') == 'BANNED':
            return jsonify({"success": False, "message": "   !"}), 403

        db_id = str(user.get('_id', ''))
        pure_uid = str(int(db_id[-6:], 16))[-6:].zfill(6) if db_id else "000000"

        return jsonify({
            "success": True, "userData": {
                "uid": pure_uid, "mobile": user.get('mobile'), "first_name": user.get('name'), "balance": float(user.get('balance', 0))
            }
        }), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

#  4.   
@app.route('/api/dashboard', methods=['POST'])
def get_dashboard_data():
    try:
        data = request.json or {}
        mobile = data.get('mobile')
        user = db.users.find_one({"mobile": mobile})
        if not user: return jsonify({"success": False, "message": " "}), 404
        return jsonify({"success": True, "balance": float(user.get('balance', 0))}), 200
    except Exception as e: return jsonify({"success": False}), 500

#  5.   (4:40 PM LOCK)
@app.route('/api/game-status', methods=['GET'])
def get_game_status():
    try:
        #        ( Gali, Disawer)
        market_name = request.args.get('market', 'Faridabad').strip()
        now_ist = datetime.now(IST)
        current_time = now_ist.strftime("%H:%M")
        
        #  8          
        market_timings = {
            "Faridabad": {"lock": "17:40", "result": "18:00"},
            "Ghaziabad": {"lock": "20:10", "result": "20:30"},
            "Gali":      {"lock": "23:10", "result": "23:30"},
            "Disawer":   {"lock": "04:40", "result": "05:00"},
            "Market05":  {"lock": "13:40", "result": "14:00"},
            "Market06":  {"lock": "15:40", "result": "16:00"},
            "Market07":  {"lock": "18:40", "result": "19:00"},
            "Market08":  {"lock": "21:40", "result": "22:00"}
        }
        
        timing = market_timings.get(market_name, {"lock": "17:40", "result": "18:00"})
        
        #       ,       
        if timing["lock"] <= current_time < timing["result"]:
            return jsonify({
                "status": "closed",
                "message": f"Betting Closed for {market_name}. Waiting for Result...",
                "server_time": current_time
            }), 200
        else:
            return jsonify({
                "status": "open",
                "message": f"Betting is Live for {market_name}!",
                "server_time": current_time
            }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
        

#  6.       
@app.route('/api/place-bet', methods=['POST'])
def place_bet():
    try:
        data = request.json or {}
        user_id, selected_numbers, amount_per_number = data.get('user_id'), data.get('numbers', []), int(data.get('amount', 0))
        round_id = data.get('round_id', 'DAILY_FARIDABAD')

        total_bet_amount = len(selected_numbers) * amount_per_number
        user = db.users.find_one({"mobile": user_id})
        if not user or float(user.get('balance', 0)) < total_bet_amount:
            return jsonify({"status": "error", "message": "  !"}), 400

        new_balance = float(user.get('balance', 0)) - total_bet_amount
        db.users.update_one({"mobile": user_id}, {"$set": {"balance": new_balance}})
        db.bets.insert_one({
            "user_id": user_id, "numbers": selected_numbers, "amount_per_number": amount_per_number,
            "total_amount": total_bet_amount, "round_id": round_id, "status": "PENDING", "created_at": datetime.now(IST)
        })
        return jsonify({"status": "success", "new_balance": new_balance}), 200
    except Exception as e: return jsonify({"status": "error", "message": str(e)}), 500
    #  7.      (   )
@app.route('/api/admin/dashboard-sheet', methods=['GET'])
def get_admin_dashboard_sheet():
    try:
        users_cursor = db.users.find({}, {"_id": 1, "mobile": 1, "name": 1, "balance": 1, "status": 1})
        users_list = []
        for u in users_cursor:
            db_id = str(u.get('_id', ''))
            pure_6digit_uid = str(int(db_id[-6:], 16))[-6:].zfill(6) if db_id else "000000"
            users_list.append({
                "uid": pure_6digit_uid, "name": u.get('name', 'User'), "mobile": u.get('mobile'),
                "balance": f" can_sym_0{float(u.get('balance', 0))}", "status": u.get('status', 'active')
            })

        sheet_data = {str(i): 0 for i in range(1, 101)}
        active_bets = list(db.bets.find({"status": "PENDING"}))
        total_active_bets_money = 0

        for bet in active_bets:
            amt_per_num = int(bet.get('amount_per_number', 0))
            for num in bet.get('numbers', []):
                if str(num) in sheet_data:
                    sheet_data[str(num)] += amt_per_num
                    total_active_bets_money += amt_per_num

        sorted_sheet = sorted(sheet_data.items(), key=lambda x: x)
        highest_num, highest_amt = sorted_sheet[-1]
        
        lowest_num = "0"
        for num, amt in sorted_sheet:
            if amt > 0: lowest_num = num; break

        zero_money_numbers = [num for num, amt in sheet_data.items() if amt == 0]

        return jsonify({
            "status": "success", "total_users": len(users_list), "total_active_bets_money": total_active_bets_money,
            "users": users_list, "sheet": sheet_data,
            "tags": {"highest": highest_num if highest_amt > 0 else "0", "lowest": lowest_num, "zero_count": len(zero_money_numbers)}
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

#  8.     - - 
@app.route('/api/admin/declare-result', methods=['POST'])
def declare_result():
    try:
        data = request.json or {}
        winning_number = data.get('winning_number')
        #         ( DAILY_GALI, DAILY_DISAWER, DAILY_FARIDABAD)
        round_id = data.get('round_id', 'DAILY_FARIDABAD').upper()

        #       ,      -   
        if not winning_number:
            sheet_data = {str(i): 0 for i in range(1, 101)}
            #      PENDING    
            active_bets = list(db.bets.find({"status": "PENDING", "round_id": round_id}))
            
            for bet in active_bets:
                amt = int(bet.get('amount_per_number', 0))
                for num in bet.get('numbers', []):
                    if str(num) in sheet_data:
                        sheet_data[str(num)] += amt

            #     0     (100%   )
            zero_money_numbers = [num for num, amt in sheet_data.items() if amt == 0]
            if zero_money_numbers:
                winning_number = int(zero_money_numbers[0])  #  0   
            else:
                #         (Absolute Lowest Pool)   
                winning_number = int(min(sheet_data, key=sheet_data.get))
        else:
            winning_number = int(winning_number)

        #   'results'     
        db.results.insert_one({
            "winning_number": winning_number,
            "round_id": round_id,
            "declared_at": datetime.now(IST)
        })

        #        95x   
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
                db.bets.update_one({"_id": bet["_id"]}, {"$set": {"status": "LOSE", "payout": 0}})

        return jsonify({
            "status": "success",
            "message": f"Result {winning_number} successfully declared for {round_id} and 95x payouts distributed!"
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
        
        # 📊 9. खिलाड़ी की लाइव बेट हिस्ट्री खींचने का एंडपॉइंट (100% फिक्स रूट)
@app.route('/api/user-bets', methods=['GET'])
def get_user_bets():
    try:
        # फ्रंटएंड से खिलाड़ी का मोबाइल नंबर पकड़ना
        user_mobile = request.args.get('mobile')
        if not user_mobile:
            return jsonify({"status": "error", "message": "Mobile number is required!"}), 400

        # MongoDB से केवल इस यूजर की सभी बेट्स निकालना (नई बेट्स सबसे ऊपर)
        user_bets = list(db.bets.find({"user_id": str(user_mobile)}).sort("_id", -1))
        
        # MongoDB की ID ऑब्जेक्ट को सादा टेक्स्ट (String) में बदलना ताकि एरर न आए
        for bet in user_bets:
            bet['_id'] = str(bet['_id'])
            if 'declared_at' in bet and bet['declared_at']:
                bet['declared_at'] = bet['declared_at'].strftime("%Y-%m-%d %H:%M:%S")

        return jsonify({
            "status": "success",
            "bets": user_bets
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
        
        

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
    