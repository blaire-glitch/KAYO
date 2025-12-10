from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from app import db
from app.models.delegate import Delegate
from app.models.payment import Payment
from app.forms import PaymentForm
from app.services.mpesa import MpesaAPI

payments_bp = Blueprint('payments', __name__, url_prefix='/payments')


@payments_bp.route('/')
@login_required
def payment_page():
    """Show payment page with unpaid delegates"""
    # Get unpaid delegates
    unpaid_delegates = Delegate.query.filter_by(
        registered_by=current_user.id,
        is_paid=False
    ).all()
    
    if not unpaid_delegates:
        flash('No unpaid delegates to process.', 'info')
        return redirect(url_for('main.dashboard'))
    
    # Calculate total
    delegate_fee = current_app.config['DELEGATE_FEE']
    total_amount = len(unpaid_delegates) * delegate_fee
    
    form = PaymentForm()
    if current_user.phone:
        form.phone_number.data = current_user.phone
    
    # Get recent payment attempts
    recent_payments = Payment.query.filter_by(
        user_id=current_user.id
    ).order_by(Payment.created_at.desc()).limit(5).all()
    
    return render_template('payments/payment.html',
        form=form,
        unpaid_delegates=unpaid_delegates,
        total_amount=total_amount,
        delegate_fee=delegate_fee,
        recent_payments=recent_payments
    )


@payments_bp.route('/initiate', methods=['POST'])
@login_required
def initiate_payment():
    """Initiate M-Pesa STK Push payment"""
    form = PaymentForm()
    
    if not form.validate_on_submit():
        flash('Please provide a valid phone number.', 'danger')
        return redirect(url_for('payments.payment_page'))
    
    # Get unpaid delegates
    unpaid_delegates = Delegate.query.filter_by(
        registered_by=current_user.id,
        is_paid=False
    ).all()
    
    if not unpaid_delegates:
        flash('No unpaid delegates to process.', 'info')
        return redirect(url_for('main.dashboard'))
    
    # Calculate total
    delegate_fee = current_app.config['DELEGATE_FEE']
    total_amount = len(unpaid_delegates) * delegate_fee
    
    # Create payment record
    payment = Payment(
        user_id=current_user.id,
        amount=total_amount,
        phone_number=form.phone_number.data,
        delegates_count=len(unpaid_delegates),
        status='pending'
    )
    db.session.add(payment)
    db.session.commit()
    
    # Link delegates to this payment
    for delegate in unpaid_delegates:
        delegate.payment_id = payment.id
    db.session.commit()
    
    # Initiate M-Pesa STK Push
    mpesa = MpesaAPI()
    response = mpesa.stk_push(
        phone_number=form.phone_number.data,
        amount=total_amount,
        account_reference=f"KAYO-{payment.id}",
        transaction_desc=f"Payment for {len(unpaid_delegates)} delegates"
    )
    
    if 'error' in response:
        payment.mark_failed('0', response['error'])
        db.session.commit()
        flash(f'Payment initiation failed: {response["error"]}', 'danger')
        return redirect(url_for('payments.payment_page'))
    
    # Update payment with M-Pesa response
    payment.checkout_request_id = response.get('CheckoutRequestID')
    payment.merchant_request_id = response.get('MerchantRequestID')
    db.session.commit()
    
    flash('Payment request sent! Check your phone to complete the payment.', 'success')
    return redirect(url_for('payments.payment_status', payment_id=payment.id))


@payments_bp.route('/status/<int:payment_id>')
@login_required
def payment_status(payment_id):
    """Show payment status page"""
    payment = Payment.query.get_or_404(payment_id)
    
    # Only allow viewing own payments (unless admin)
    if payment.user_id != current_user.id and not current_user.is_admin():
        flash('You do not have permission to view this payment.', 'danger')
        return redirect(url_for('payments.payment_page'))
    
    return render_template('payments/status.html', payment=payment)


@payments_bp.route('/check-status/<int:payment_id>')
@login_required
def check_payment_status(payment_id):
    """API endpoint to check payment status"""
    payment = Payment.query.get_or_404(payment_id)
    
    # Only allow checking own payments (unless admin)
    if payment.user_id != current_user.id and not current_user.is_admin():
        return jsonify({'error': 'Unauthorized'}), 403
    
    if payment.status != 'pending':
        return jsonify({
            'status': payment.status,
            'receipt': payment.mpesa_receipt_number
        })
    
    # Query M-Pesa for status
    if payment.checkout_request_id:
        mpesa = MpesaAPI()
        response = mpesa.query_stk_status(payment.checkout_request_id)
        
        result_code = response.get('ResultCode')
        if result_code is not None:
            if str(result_code) == '0':
                # Success
                payment.mark_completed(
                    mpesa_receipt=response.get('MpesaReceiptNumber', 'N/A')
                )
                db.session.commit()
            elif str(result_code) != '':
                # Failed
                payment.mark_failed(
                    result_code=str(result_code),
                    result_desc=response.get('ResultDesc', 'Payment failed')
                )
                # Unlink delegates from failed payment
                for delegate in payment.delegates:
                    delegate.payment_id = None
                db.session.commit()
    
    return jsonify({
        'status': payment.status,
        'receipt': payment.mpesa_receipt_number
    })


@payments_bp.route('/callback', methods=['POST'])
def mpesa_callback():
    """M-Pesa callback endpoint"""
    data = request.get_json()
    
    current_app.logger.info(f"M-Pesa callback received: {data}")
    
    if not data:
        return jsonify({'ResultCode': 1, 'ResultDesc': 'No data received'})
    
    try:
        callback = data.get('Body', {}).get('stkCallback', {})
        checkout_request_id = callback.get('CheckoutRequestID')
        result_code = callback.get('ResultCode')
        result_desc = callback.get('ResultDesc')
        
        # Find payment by checkout request ID
        payment = Payment.query.filter_by(checkout_request_id=checkout_request_id).first()
        
        if not payment:
            current_app.logger.error(f"Payment not found for CheckoutRequestID: {checkout_request_id}")
            return jsonify({'ResultCode': 0, 'ResultDesc': 'Accepted'})
        
        if str(result_code) == '0':
            # Successful payment
            callback_metadata = callback.get('CallbackMetadata', {}).get('Item', [])
            mpesa_receipt = None
            transaction_date = None
            
            for item in callback_metadata:
                if item.get('Name') == 'MpesaReceiptNumber':
                    mpesa_receipt = item.get('Value')
                elif item.get('Name') == 'TransactionDate':
                    transaction_date = item.get('Value')
            
            payment.mark_completed(mpesa_receipt=mpesa_receipt or 'N/A')
            db.session.commit()
            current_app.logger.info(f"Payment {payment.id} completed successfully")
        else:
            # Failed payment
            payment.mark_failed(result_code=str(result_code), result_desc=result_desc)
            # Unlink delegates from failed payment
            for delegate in payment.delegates:
                delegate.payment_id = None
            db.session.commit()
            current_app.logger.info(f"Payment {payment.id} failed: {result_desc}")
        
        return jsonify({'ResultCode': 0, 'ResultDesc': 'Accepted'})
    
    except Exception as e:
        current_app.logger.error(f"Error processing M-Pesa callback: {str(e)}")
        return jsonify({'ResultCode': 1, 'ResultDesc': str(e)})


@payments_bp.route('/history')
@login_required
def payment_history():
    """Show payment history"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    payments = Payment.query.filter_by(
        user_id=current_user.id
    ).order_by(Payment.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('payments/history.html', payments=payments)
