"""
Payment Processing System - Phase 2
Comprehensive payment handling with multiple methods and validation
"""

from flask import Blueprint, request, jsonify, session
from models import db, Order, PaymentTransaction, get_thai_now
from datetime import datetime, timedelta
import uuid
import hashlib
import base64
from decimal import Decimal
import os

# Create payment blueprint
payment_bp = Blueprint('payment', __name__, url_prefix='/api/payment')

class PaymentManager:
    """Enhanced payment processing system"""
    
    PAYMENT_METHODS = {
        'cod': {
            'name': 'เก็บเงินปลายทาง',
            'requires_verification': False,
            'processing_fee': 0,
            'enabled': True
        },
        'bank_transfer': {
            'name': 'โอนเงิน',
            'requires_verification': True,
            'processing_fee': 0,
            'enabled': True
        },
        'promptpay': {
            'name': 'พร้อมเพย์',
            'requires_verification': True,
            'processing_fee': 0,
            'enabled': True
        },
        'credit_card': {
            'name': 'บัตรเครดิต',
            'requires_verification': True,
            'processing_fee': 2.95,  # 2.95% processing fee
            'enabled': False  # Disabled for now (requires payment gateway)
        },
        'digital_wallet': {
            'name': 'กระเป๋าเงินดิจิทัล',
            'requires_verification': True,
            'processing_fee': 1.5,
            'enabled': False  # Disabled for now
        }
    }
    
    TRANSACTION_STATUSES = {
        'pending': 'รอการชำระ',
        'processing': 'กำลังดำเนินการ',
        'completed': 'สำเร็จ',
        'failed': 'ล้มเหลว',
        'cancelled': 'ยกเลิก',
        'refunded': 'คืนเงินแล้ว'
    }
    
    # Bank account information for transfers
    BANK_ACCOUNTS = {
        'scb': {
            'name': 'ธนาคารไทยพาณิชย์',
            'account_number': '123-456-7890',
            'account_name': 'ร้านลานอิ่ม'
        },
        'kbank': {
            'name': 'ธนาคารกสิกรไทย',
            'account_number': '098-765-4321',
            'account_name': 'ร้านลานอิ่ม'
        }
    }
    
    PROMPTPAY_QR = "0020101021153037690000000000000004850117691234567890123456802TH5310THB5802TH6304"
    
    @staticmethod
    def generate_transaction_id():
        """Generate unique transaction ID"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        random_suffix = str(uuid.uuid4())[:8].upper()
        return f"TXN{timestamp}{random_suffix}"
    
    @staticmethod
    def calculate_processing_fee(amount, payment_method):
        """Calculate processing fee for payment method"""
        method_info = PaymentManager.PAYMENT_METHODS.get(payment_method, {})
        fee_rate = method_info.get('processing_fee', 0)
        
        if fee_rate == 0:
            return 0
        
        # Calculate percentage fee
        fee_amount = (amount * fee_rate) / 100
        
        # Minimum fee of 1 baht, maximum of 50 baht
        return min(max(fee_amount, 1), 50)
    
    @staticmethod
    def validate_payment_data(payment_data):
        """Validate payment request data"""
        required_fields = ['method', 'amount']
        
        for field in required_fields:
            if field not in payment_data:
                return f"Field '{field}' is required"
        
        method = payment_data['method']
        if method not in PaymentManager.PAYMENT_METHODS:
            return "Invalid payment method"
        
        if not PaymentManager.PAYMENT_METHODS[method]['enabled']:
            return "Payment method is currently disabled"
        
        try:
            amount = float(payment_data['amount'])
            if amount <= 0:
                return "Amount must be greater than zero"
            if amount > 50000:  # Maximum order amount
                return "Amount exceeds maximum limit"
        except (ValueError, TypeError):
            return "Invalid amount format"
        
        # Method-specific validations
        if method == 'bank_transfer':
            if 'transfer_slip' not in payment_data:
                return "Transfer slip image is required for bank transfer"
        
        if method == 'promptpay':
            if 'transaction_ref' not in payment_data:
                return "Transaction reference is required for PromptPay"
        
        return None
    
    @staticmethod
    def create_payment_transaction(order, payment_data):
        """Create payment transaction record"""
        transaction = PaymentTransaction(
            transaction_id=PaymentManager.generate_transaction_id(),
            order_id=order.id,
            payment_method=payment_data['method'],
            amount=float(payment_data['amount']),
            processing_fee=PaymentManager.calculate_processing_fee(
                float(payment_data['amount']), 
                payment_data['method']
            ),
            status='pending',
            payment_data=str(payment_data),  # Store as JSON string
            created_at=get_thai_now()
        )
        
        return transaction
    
    @staticmethod
    def generate_qr_code_data(amount, order_number):
        """Generate QR code data for PromptPay payments"""
        # This is a simplified QR code data generation
        # In real implementation, you'd use proper PromptPay QR generation
        base_qr = PaymentManager.PROMPTPAY_QR
        
        # Add amount and reference
        amount_str = f"{amount:.2f}"
        ref_str = order_number[-6:]  # Last 6 digits of order number
        
        # Simple QR data (in real app, use proper EMVCo standard)
        qr_data = f"{base_qr}54{len(amount_str):02d}{amount_str}62{len(ref_str):02d}{ref_str}"
        
        return qr_data

@payment_bp.route('/methods', methods=['GET'])
def get_payment_methods():
    """Get available payment methods"""
    try:
        available_methods = []
        
        for method_key, method_info in PaymentManager.PAYMENT_METHODS.items():
            if method_info['enabled']:
                available_methods.append({
                    'key': method_key,
                    'name': method_info['name'],
                    'requires_verification': method_info['requires_verification'],
                    'processing_fee': method_info['processing_fee']
                })
        
        return jsonify({
            'success': True,
            'methods': available_methods,
            'bank_accounts': PaymentManager.BANK_ACCOUNTS
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to get payment methods: {str(e)}'}), 500

@payment_bp.route('/initiate', methods=['POST'])
def initiate_payment():
    """Initiate payment process"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No payment data provided'}), 400
        
        # Validate payment data
        validation_error = PaymentManager.validate_payment_data(data)
        if validation_error:
            return jsonify({'error': validation_error}), 400
        
        # Get order
        order_id = data.get('order_id')
        if not order_id:
            return jsonify({'error': 'Order ID is required'}), 400
        
        order = db.session.get(Order, order_id)
        if not order:
            return jsonify({'error': 'Order not found'}), 404
        
        # Check if order is already paid
        if order.payment_status == 'completed':
            return jsonify({'error': 'Order is already paid'}), 400
        
        # Verify amount matches order total
        if abs(float(data['amount']) - float(order.total_amount)) > 0.01:
            return jsonify({'error': 'Payment amount does not match order total'}), 400
        
        # Create payment transaction
        transaction = PaymentManager.create_payment_transaction(order, data)
        
        db.session.add(transaction)
        
        # Update order payment status
        order.payment_status = 'processing'
        order.updated_at = get_thai_now()
        
        db.session.commit()
        
        # Prepare response based on payment method
        response_data = {
            'success': True,
            'transaction_id': transaction.transaction_id,
            'payment_method': transaction.payment_method,
            'amount': float(transaction.amount),
            'processing_fee': float(transaction.processing_fee),
            'status': transaction.status
        }
        
        # Add method-specific data
        if data['method'] == 'bank_transfer':
            response_data['bank_accounts'] = PaymentManager.BANK_ACCOUNTS
            response_data['instructions'] = [
                "โอนเงินเข้าบัญชีที่เลือก",
                "ถ่ายรูปสลิปการโอนเงิน",
                "อัพโหลดสลิปในขั้นตอนถัดไป",
                "รอการยืนยันจากร้าน"
            ]
        
        elif data['method'] == 'promptpay':
            qr_data = PaymentManager.generate_qr_code_data(transaction.amount, order.order_number)
            response_data['qr_code'] = qr_data
            response_data['promptpay_id'] = "0812345678"  # Restaurant's PromptPay ID
            response_data['instructions'] = [
                "สแกน QR Code ด้วยแอปธนาคาร",
                "ตรวจสอบจำนวนเงิน",
                "ยืนยันการชำระเงิน",
                "บันทึกหมายเลขอ้างอิง"
            ]
        
        elif data['method'] == 'cod':
            # COD is automatically approved
            transaction.status = 'completed'
            order.payment_status = 'completed'
            db.session.commit()
            
            response_data['status'] = 'completed'
            response_data['instructions'] = [
                "เตรียมเงินสดให้พร้อม",
                "ชำระเงินให้กับพนักงานส่งอาหาร",
                "รับใบเสร็จจากพนักงาน"
            ]
        
        return jsonify(response_data), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to initiate payment: {str(e)}'}), 500

@payment_bp.route('/verify', methods=['POST'])
def verify_payment():
    """Verify payment (for transfer slips, etc.)"""
    try:
        data = request.get_json()
        
        if not data or 'transaction_id' not in data:
            return jsonify({'error': 'Transaction ID is required'}), 400
        
        transaction_id = data['transaction_id']
        
        # Get transaction
        transaction = PaymentTransaction.query.filter_by(transaction_id=transaction_id).first()
        
        if not transaction:
            return jsonify({'error': 'Transaction not found'}), 404
        
        if transaction.status != 'pending':
            return jsonify({'error': 'Transaction is not pending verification'}), 400
        
        # For bank transfer, require slip upload
        if transaction.payment_method == 'bank_transfer':
            transfer_slip = data.get('transfer_slip')
            if not transfer_slip:
                return jsonify({'error': 'Transfer slip is required'}), 400
            
            # In real implementation, you'd save the slip image
            # For now, just mark as pending verification
            transaction.status = 'processing'
            transaction.verification_data = str(data)
            transaction.updated_at = get_thai_now()
        
        # For PromptPay, require transaction reference
        elif transaction.payment_method == 'promptpay':
            transaction_ref = data.get('transaction_ref')
            if not transaction_ref:
                return jsonify({'error': 'Transaction reference is required'}), 400
            
            # In real implementation, you'd verify with PromptPay API
            # For now, auto-approve if reference looks valid
            if len(transaction_ref) >= 6:
                transaction.status = 'completed'
                transaction.verification_data = str(data)
                transaction.completed_at = get_thai_now()
                
                # Update order
                order = db.session.get(Order, transaction.order_id)
                if order:
                    order.payment_status = 'completed'
                    order.updated_at = get_thai_now()
            else:
                return jsonify({'error': 'Invalid transaction reference'}), 400
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Payment verification submitted',
            'transaction': {
                'transaction_id': transaction.transaction_id,
                'status': transaction.status,
                'status_text': PaymentManager.TRANSACTION_STATUSES.get(transaction.status)
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to verify payment: {str(e)}'}), 500

@payment_bp.route('/status/<transaction_id>', methods=['GET'])
def get_payment_status(transaction_id):
    """Get payment transaction status"""
    try:
        transaction = PaymentTransaction.query.filter_by(transaction_id=transaction_id).first()
        
        if not transaction:
            return jsonify({'error': 'Transaction not found'}), 404
        
        # Get order details
        order = db.session.get(Order, transaction.order_id)
        
        return jsonify({
            'success': True,
            'transaction': {
                'transaction_id': transaction.transaction_id,
                'payment_method': transaction.payment_method,
                'amount': float(transaction.amount),
                'processing_fee': float(transaction.processing_fee),
                'status': transaction.status,
                'status_text': PaymentManager.TRANSACTION_STATUSES.get(transaction.status),
                'created_at': transaction.created_at.isoformat(),
                'completed_at': transaction.completed_at.isoformat() if transaction.completed_at else None
            },
            'order': {
                'order_number': order.order_number,
                'payment_status': order.payment_status,
                'total_amount': float(order.total_amount)
            } if order else None
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to get payment status: {str(e)}'}), 500

@payment_bp.route('/refund', methods=['POST'])
def process_refund():
    """Process payment refund (admin only)"""
    try:
        # This would typically require admin authentication
        data = request.get_json()
        
        if not data or 'transaction_id' not in data:
            return jsonify({'error': 'Transaction ID is required'}), 400
        
        transaction_id = data['transaction_id']
        reason = data.get('reason', 'Refund requested')
        
        # Get transaction
        transaction = PaymentTransaction.query.filter_by(transaction_id=transaction_id).first()
        
        if not transaction:
            return jsonify({'error': 'Transaction not found'}), 404
        
        if transaction.status != 'completed':
            return jsonify({'error': 'Can only refund completed transactions'}), 400
        
        # Create refund transaction
        refund_transaction = PaymentTransaction(
            transaction_id=PaymentManager.generate_transaction_id(),
            order_id=transaction.order_id,
            payment_method=transaction.payment_method,
            amount=-transaction.amount,  # Negative amount for refund
            processing_fee=0,
            status='completed',
            payment_data=f"Refund for {transaction_id}: {reason}",
            created_at=get_thai_now(),
            completed_at=get_thai_now()
        )
        
        # Update original transaction
        transaction.status = 'refunded'
        transaction.updated_at = get_thai_now()
        
        # Update order
        order = db.session.get(Order, transaction.order_id)
        if order:
            order.payment_status = 'refunded'
            order.status = 'cancelled'
            order.updated_at = get_thai_now()
        
        db.session.add(refund_transaction)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Refund processed successfully',
            'refund_transaction_id': refund_transaction.transaction_id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to process refund: {str(e)}'}), 500
