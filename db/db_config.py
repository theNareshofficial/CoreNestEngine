from pymongo import MongoClient

try:
    client = MongoClient("mongodb://localhost:27017/")
    db = client["stock_db"]
    
    reg_info = db["reg_info"]             # User Registration Info
    inward_info = db["inward_info"]       # Inward Stock Info
    bill_collection_data = db["bill_collection_data"]  # Individual Bill Items
    sales_history = db["sales_history"]  # Track daily sales

    
    print("✅ MongoDB Connected Successfully!")
except Exception as e:
    print("❌ MongoDB Connection Error:", str(e))
