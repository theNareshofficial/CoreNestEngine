from pymongo import MongoClient

try:
    client = MongoClient("mongodb://localhost:27017/")
    db = client["stock_db"]
    
    reg_info = db["reg_info"]             # User Registration Info
    inward_info = db["inward_info"]       # Inward Stock Info
    bills_info = db["bills_info"]         # Bills Info
    bill_collection = db["bill_collection"]  # Individual Bill Items
    
    print("✅ MongoDB Connected Successfully!")
except Exception as e:
    print("❌ MongoDB Connection Error:", str(e))
