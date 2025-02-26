from pymongo import MongoClient

try:
    client = MongoClient("mongodb://localhost:27017/")
    db = client["stock_db"]
    reg_info = db["reg_info"]
    inward_info = db["inward_info"]

    print("✅ MongoDB Connected Successfully!")
except Exception as e:
    print("❌ MongoDB Connection Error:", str(e))
