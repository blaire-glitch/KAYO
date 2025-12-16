from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime
from app import db
from app.models.delegate import Delegate
from app.models.payment import Payment
from app.models.event import Event
from app.forms import PaymentForm, CashPaymentForm
from app.services.mpesa import MpesaAPI

payments_bp = Blueprint('payments', __name__, url_prefix='/payments')

# Roles allowed to confirm cash payments
PAYMENT_CONFIRMATION_ROLES = ['finance', 'treasurer', 'admin', 'super_admin', 'registrar']


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
    delegate_fee = current_app.config.get('DELEGATE_FEE', 500)
    total_amount = len(unpaid_delegates) * delegate_fee
    
    form = PaymentForm()
    if current_user.phone:
        form.phone_number.data = current_user.phone
    
    # Check if user can confirm cash payments
    can_confirm_cash = current_user.role in PAYMENT_CONFIRMATION_ROLES
    
    # Get recent payment attempts
    recent_payments = Payment.query.filter_by(
        user_id=current_user.id
    ).order_by(Payment.created_at.desc()).limit(5).all()
    
    return render_template('payments/payment.html',
        form=form,
        unpaid_delegates=unpaid_delegates,
        total_amount=total_amount,
        delegate_fee=delegate_fee,
        recent_payments=recent_payments,
        can_confirm_cash=can_confirm_cash
    )


@payments_bp.route('/initiate', methods=['POST'])
@login_required
def initiate_payment():
    """Initiate payment based on selected method"""
    form = PaymentForm()
    
    if not form.validate_on_submit():
        flash('Please fill in the required fields.', 'danger')
        return redirect(url_for('payments.payment_page'))
    
    payment_method = form.payment_method.data
    
    # Get unpaid delegates
    unpaid_delegates = Delegate.query.filter_by(
        registered_by=current_user.id,
        is_paid=False
    ).all()
    
    if not unpaid_delegates:
        flash('No unpaid delegates to process.', 'info')
        return redirect(url_for('main.dashboard'))
    
    # Calculate total
    delegate_fee = current_app.config.get('DELEGATE_FEE', 500)
    total_amount = len(unpaid_delegates) * delegate_fee
    
    if payment_method == 'mpesa':
        # M-Pesa STK Push
        if not form.phone_number.data:
            flash('Phone number is required for M-Pesa payment.', 'danger')
            return redirect(url_for('payments.payment_page'))
        return initiate_mpesa_payment(form, unpaid_delegates, total_amount, delegate_fee)
    
    elif payment_method == 'cash':
        # Cash payment - only allowed for authorized roles
        if current_user.role not in PAYMENT_CONFIRMATION_ROLES:
            flash('Only Finance personnel can confirm cash payments.', 'danger')
            return redirect(url_for('payments.payment_page'))
        return record_cash_payment(form, unpaid_delegates, total_amount, delegate_fee)
    
    elif payment_method in ['mpesa_paybill', 'bank_transfer']:
        # Manual verification required
        if not form.receipt_number.data:
            flash('Receipt/reference number is required for manual verification.', 'danger')
            return redirect(url_for('payments.payment_page'))
        return record_manual_payment(form, unpaid_delegates, total_amount, delegate_fee, payment_method)
    
    flash('Invalid payment method selected.', 'danger')
    return redirect(url_for('payments.payment_page'))


def initiate_mpesa_payment(form, unpaid_delegates, total_amount, delegate_fee):
    """Handle M-Pesa STK Push payment"""
    # Create payment record
    payment = Payment(
        user_id=current_user.id,
        amount=total_amount,
        payment_mode='M-Pesa STK Push',
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


def record_cash_payment(form, unpaid_delegates, total_amount, delegate_fee):
    """Handle cash payment confirmation"""
    try:
        # Create payment record
        payment = Payment(
            user_id=current_user.id,
            amount=total_amount,
            payment_mode='Cash',
            mpesa_receipt_number=form.receipt_number.data or f"CASH-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            delegates_count=len(unpaid_delegates),
            status='completed',
            completed_at=datetime.utcnow()
        )
        db.session.add(payment)
        db.session.commit()
        
        # Link delegates and mark as paid, assign ticket numbers
        tickets_issued = 0
        for delegate in unpaid_delegates:
            # Explicit updates with db.session.add to ensure tracking
            delegate.payment_id = payment.id
            delegate.is_paid = True
            delegate.amount_paid = delegate_fee
            delegate.payment_confirmed_by = current_user.id
            delegate.payment_confirmed_at = datetime.utcnow()
            
            # Generate ticket number if not already assigned
            if not delegate.ticket_number or delegate.ticket_number.startswith('PENDING-'):
                event = Event.query.get(delegate.event_id) if delegate.event_id else None
                delegate.ticket_number = Delegate.generate_ticket_number(event)
                tickets_issued += 1
            
            # Explicitly add to session to ensure changes are tracked
            db.session.add(delegate)
        
        db.session.commit()
        
        current_app.logger.info(f'Cash payment recorded: {payment.id}, Amount: {total_amount}, Delegates: {len(unpaid_delegates)}, is_paid updated: True')
        flash(f'Cash payment of KSh {total_amount:,.2f} confirmed for {len(unpaid_delegates)} delegate(s). {tickets_issued} ticket(s) issued.', 'success')
        return redirect(url_for('payments.payment_status', payment_id=payment.id))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error recording cash payment: {str(e)}')
        flash(f'Error recording payment: {str(e)}', 'danger')
        return redirect(url_for('payments.payment_page'))


def record_manual_payment(form, unpaid_delegates, total_amount, delegate_fee, payment_method):
    """Handle manual payment verification (paybill/bank transfer)"""
    try:
        payment_mode = 'M-Pesa Paybill' if payment_method == 'mpesa_paybill' else 'Bank Transfer'
        
        # Create payment record
        payment = Payment(
            user_id=current_user.id,
            amount=total_amount,
            payment_mode=payment_mode,
            mpesa_receipt_number=form.receipt_number.data,
            phone_number=form.phone_number.data,
            delegates_count=len(unpaid_delegates),
            status='completed',
            completed_at=datetime.utcnow()
        )
        db.session.add(payment)
        db.session.commit()
        
        # Link delegates and mark as paid, assign ticket numbers
        tickets_issued = 0
        for delegate in unpaid_delegates:
            # Explicit updates with db.session.add to ensure tracking
            delegate.payment_id = payment.id
            delegate.is_paid = True
            delegate.amount_paid = delegate_fee
            delegate.payment_confirmed_by = current_user.id
            delegate.payment_confirmed_at = datetime.utcnow()
            
            # Generate ticket number if not already assigned
            if not delegate.ticket_number or delegate.ticket_number.startswith('PENDING-'):
                event = Event.query.get(delegate.event_id) if delegate.event_id else None
                delegate.ticket_number = Delegate.generate_ticket_number(event)
                tickets_issued += 1
            
            # Explicitly add to session to ensure changes are tracked
            db.session.add(delegate)
        
        db.session.commit()
        
        current_app.logger.info(f'{payment_mode} payment recorded: {payment.id}, Receipt: {form.receipt_number.data}, is_paid updated: True')
        flash(f'{payment_mode} payment confirmed for {len(unpaid_delegates)} delegate(s). {tickets_issued} ticket(s) issued.', 'success')
        return redirect(url_for('payments.payment_status', payment_id=payment.id))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error recording manual payment: {str(e)}')
        flash(f'Error recording payment: {str(e)}', 'danger')
        return redirect(url_for('payments.payment_page'))


@payments_bp.route('/confirm-cash', methods=['GET', 'POST'])
@login_required
def confirm_cash_payment():
    """Page for finance to confirm cash payments for any delegates"""
    if current_user.role not in PAYMENT_CONFIRMATION_ROLES:
        flash('Access denied. Only Finance personnel can confirm cash payments.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    form = CashPaymentForm()
    delegate_fee = current_app.config.get('DELEGATE_FEE', 500)
    
    # Get all unpaid delegates
    unpaid_delegates = Delegate.query.filter_by(is_paid=False).order_by(
        Delegate.archdeaconry, Delegate.parish, Delegate.name
    ).all()
    
    if request.method == 'POST' and form.validate_on_submit():
        try:
            # Parse delegate IDs
            delegate_ids = [int(id.strip()) for id in form.delegate_ids.data.split(',') if id.strip()]
            
            if not delegate_ids:
                flash('Please select at least one delegate.', 'danger')
                return render_template('payments/confirm_cash.html', form=form, unpaid_delegates=unpaid_delegates, delegate_fee=delegate_fee)
            
            # Get delegates
            delegates = Delegate.query.filter(Delegate.id.in_(delegate_ids)).all()
            
            if not delegates:
                flash('No delegates found with the provided IDs.', 'danger')
                return render_template('payments/confirm_cash.html', form=form, unpaid_delegates=unpaid_delegates, delegate_fee=delegate_fee)
            
            # Calculate amount
            total_amount = len(delegates) * delegate_fee
            
            # Create payment record
            payment = Payment(
                user_id=current_user.id,
                amount=total_amount,
                payment_mode='Cash',
                mpesa_receipt_number=form.receipt_number.data or f"CASH-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                result_desc=form.notes.data,
                delegates_count=len(delegates),
                status='completed',
                completed_at=datetime.utcnow()
            )
            db.session.add(payment)
            db.session.commit()
            
            # Mark delegates as paid and assign tickets
            tickets_issued = 0
            for delegate in delegates:
                # Explicit updates with db.session.add to ensure tracking
                delegate.payment_id = payment.id
                delegate.is_paid = True
                delegate.amount_paid = delegate_fee
                delegate.payment_confirmed_by = current_user.id
                delegate.payment_confirmed_at = datetime.utcnow()
                
                # Generate ticket number if not already assigned
                if not delegate.ticket_number or delegate.ticket_number.startswith('PENDING-'):
                    event = Event.query.get(delegate.event_id) if delegate.event_id else None
                    delegate.ticket_number = Delegate.generate_ticket_number(event)
                    tickets_issued += 1
                
                # Explicitly add to session to ensure changes are tracked
                db.session.add(delegate)
            
            db.session.commit()
            
            current_app.logger.info(f'Cash payment confirmed by {current_user.name}: {payment.id}, Delegates: {len(delegates)}, is_paid updated: True')
            flash(f'Cash payment confirmed for {len(delegates)} delegate(s). {tickets_issued} ticket(s) issued.', 'success')
            return redirect(url_for('payments.confirm_cash_payment'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Error confirming cash payment: {str(e)}')
            flash(f'Error: {str(e)}', 'danger')
    
    return render_template('payments/confirm_cash.html', form=form, unpaid_delegates=unpaid_delegates, delegate_fee=delegate_fee)


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
