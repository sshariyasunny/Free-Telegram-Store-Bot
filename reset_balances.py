# reset_balances.py
from database import get_db_session
from database.models import User

def reset_all_balances():
    """Reset all user wallet balances to 0."""
    try:
        with get_db_session() as session:
            users = session.query(User).all()
            count = 0
            for user in users:
                if user.wallet_balance > 0:
                    user.wallet_balance = 0.0
                    count += 1
            session.commit()
            print(f"[OK] {count} user balances reset to 0!")
            print(f"[INFO] Total users: {len(users)}")
    except Exception as e:
        print(f"[ERROR] {e}")

if __name__ == "__main__":
    print("WARNING: All user wallet balances will be set to 0!")
    confirm = input("Are you sure? (yes/no): ")
    if confirm.lower() in ["yes", "y"]:
        reset_all_balances()
    else:
        print("Cancelled.")