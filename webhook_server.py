"""
Webhook server for CryptoBot and Mini App API.
Handles real-time payment notifications and mini app data requests.
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import hmac
import hashlib
import json
from datetime import datetime
import os
import sys

# পাইথন পাথ সেট করুন
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db_session
from database.models import Transaction, TransactionStatus, User, Product, Order, PaymentMethod
from config.settings import settings

app = Flask(__name__, static_folder='../mini_app', static_url_path='/app')
CORS(app)  # CORS সক্ষম করুন


# ==================== ক্রিপ্টোবট ওয়েবহুক ====================

def verify_signature(body: bytes, signature: str) -> bool:
    """Verify CryptoBot webhook signature."""
    try:
        secret_key = hashlib.sha256(settings.CRYPTO_BOT_API_KEY.encode()).digest()
        calculated_signature = hmac.new(secret_key, body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(calculated_signature, signature)
    except:
        return False


def process_invoice_paid(invoice_data: dict):
    """Process a paid invoice notification."""
    try:
        invoice_id = invoice_data.get('invoice_id')
        status = invoice_data.get('status')

        if status != 'paid':
            return

        with get_db_session() as session:
            # Find transaction by invoice_id
            transactions = session.query(Transaction).filter(
                Transaction.payment_method == PaymentMethod.CRYPTO_WALLET,
                Transaction.status == TransactionStatus.PENDING
            ).all()

            transaction = None
            for txn in transactions:
                if txn.crypto_address and txn.crypto_address.startswith(f"{invoice_id}|"):
                    transaction = txn
                    break

            if not transaction:
                return

            user = session.query(User).filter_by(id=transaction.user_id).first()
            if not user:
                return

            # Mark as completed and add funds
            transaction.status = TransactionStatus.COMPLETED
            transaction.completed_at = datetime.utcnow()
            user.wallet_balance += transaction.amount
            session.commit()

            print(f"✅ Webhook: Transaction #{transaction.id} completed! +${transaction.amount:.2f}")

    except Exception as e:
        print(f"❌ Webhook error: {e}")


@app.route('/webhook/cryptobot', methods=['POST'])
def cryptobot_webhook():
    """CryptoBot webhook endpoint."""
    try:
        signature = request.headers.get('crypto-pay-api-signature')
        if not signature:
            return jsonify({'error': 'No signature'}), 401

        body = request.get_data()
        if not verify_signature(body, signature):
            return jsonify({'error': 'Invalid signature'}), 401

        data = request.get_json()
        if data.get('update_type') == 'invoice_paid':
            process_invoice_paid(data.get('payload'))

        return jsonify({'ok': True}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== মিনি অ্যাপ API ====================

@app.route('/api/dashboard', methods=['POST'])
def get_dashboard():
    """Get user dashboard data for mini app."""
    try:
        data = request.json
        user_id = data.get('user_id')

        with get_db_session() as session:
            user = session.query(User).filter_by(telegram_id=user_id).first()
            if not user:
                return jsonify({'error': 'User not found'}), 404

            orders = session.query(Order).filter_by(user_id=user.id).all()
            products = session.query(Product).filter_by(is_active=True).all()

            return jsonify({
                'balance': user.wallet_balance,
                'orders': [{
                    'id': o.id,
                    'total': o.total_amount,
                    'status': o.status.value,
                    'created_at': o.created_at.isoformat()
                } for o in orders],
                'products': [{
                    'id': p.id,
                    'name': p.name,
                    'price': p.price,
                    'stock': p.stock_count
                } for p in products]
            })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/products', methods=['POST'])
def get_products():
    """Get all products for mini app."""
    try:
        data = request.json
        category_id = data.get('category')

        with get_db_session() as session:
            query = session.query(Product).filter_by(is_active=True)
            if category_id:
                query = query.filter_by(category_id=category_id)

            products = query.all()
            categories = session.query(Category).all()

            return jsonify({
                'products': [{
                    'id': p.id,
                    'name': p.name,
                    'price': p.price,
                    'stock': p.stock_count,
                    'category_id': p.category_id
                } for p in products],
                'categories': [{
                    'id': c.id,
                    'name': c.name
                } for c in categories]
            })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/orders', methods=['POST'])
def get_orders():
    """Get user orders for mini app."""
    try:
        data = request.json
        user_id = data.get('user_id')

        with get_db_session() as session:
            user = session.query(User).filter_by(telegram_id=user_id).first()
            if not user:
                return jsonify({'error': 'User not found'}), 404

            orders = session.query(Order).filter_by(user_id=user.id).all()

            return jsonify({
                'orders': [{
                    'id': o.id,
                    'total': o.total_amount,
                    'status': o.status.value,
                    'created_at': o.created_at.isoformat()
                } for o in orders]
            })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/topup', methods=['POST'])
def create_topup():
    """Create a top-up request from mini app."""
    try:
        data = request.json
        user_id = data.get('user_id')
        amount = data.get('amount')
        method = data.get('method')
        txid = data.get('txid')

        if not all([user_id, amount, method, txid]):
            return jsonify({'error': 'Missing required fields'}), 400

        with get_db_session() as session:
            user = session.query(User).filter_by(telegram_id=user_id).first()
            if not user:
                return jsonify({'error': 'User not found'}), 404

            # Create transaction
            transaction = Transaction(
                user_id=user.id,
                amount=amount,
                payment_method=PaymentMethod.MANUAL,
                status=TransactionStatus.PENDING,
                txid=txid,
                crypto_address=txid,
                expires_at=datetime.utcnow()  # Will be set by calculate_expiry_time
            )
            session.add(transaction)
            session.commit()

            return jsonify({
                'success': True,
                'transaction_id': transaction.id,
                'message': 'Payment request submitted successfully'
            })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/verify', methods=['POST'])
def verify_user():
    """Verify user from Telegram WebApp data."""
    try:
        data = request.json
        init_data = data.get('initData')

        # You can implement proper Telegram WebApp data verification here
        # For now, we'll trust the data from the mini app

        # Extract user info from initData if needed
        # For simplicity, we'll use the user_id from the request

        return jsonify({'verified': True})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== মিনি অ্যাপ ফাইল সার্ভ ====================

@app.route('/')
@app.route('/app')
def serve_app():
    """Serve the mini app."""
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/app/<path:path>')
def serve_app_files(path):
    """Serve mini app static files."""
    return send_from_directory(app.static_folder, path)


# ==================== হেলথ চেক ====================

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'ok',
        'service': 'DARK HUB API & Webhook Server',
        'timestamp': datetime.utcnow().isoformat()
    }), 200


# ==================== মেইন ====================

if __name__ == '__main__':
    print("=" * 60)
    print("🖤 DARK HUB API & Webhook Server")
    print("=" * 60)
    print(f"📍 Server: http://localhost:5000")
    print(f"📱 Mini App: http://localhost:5000/app")
    print(f"🔗 API Endpoints:")
    print(f"   POST /api/dashboard")
    print(f"   POST /api/products")
    print(f"   POST /api/orders")
    print(f"   POST /api/topup")
    print(f"   POST /api/verify")
    print(f"🔔 Webhook: POST /webhook/cryptobot")
    print("=" * 60)
    print("⏳ Waiting for requests...")
    print("=" * 60)

    app.run(host='0.0.0.0', port=5000, debug=True)