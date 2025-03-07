from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, Message, User
from datetime import datetime

messages = Blueprint('messages', __name__)

@messages.route('/messages')
@login_required
def list_messages():
    inbox = Message.query.filter_by(recipient_id=current_user.id)\
        .order_by(Message.created_at.desc()).all()
    sent = Message.query.filter_by(sender_id=current_user.id)\
        .order_by(Message.created_at.desc()).all()
    return render_template('messages/list.html', inbox=inbox, sent=sent)

@messages.route('/messages/compose', methods=['GET', 'POST'])
@login_required
def compose_message():
    if request.method == 'POST':
        recipient_id = request.form.get('recipient_id')
        subject = request.form.get('subject')
        content = request.form.get('content')
        
        if not all([recipient_id, content]):
            flash('Recipient and message content are required', 'error')
            return redirect(url_for('messages.compose_message'))
        
        message = Message(
            sender_id=current_user.id,
            recipient_id=recipient_id,
            subject=subject,
            content=content
        )
        
        db.session.add(message)
        db.session.commit()
        
        flash('Message sent successfully', 'success')
        return redirect(url_for('messages.list_messages'))
    
    users = User.query.filter(User.id != current_user.id).all()
    return render_template('messages/compose.html', users=users)

@messages.route('/messages/<int:message_id>')
@login_required
def view_message(message_id):
    message = Message.query.get_or_404(message_id)
    
    # Check if user has permission to view this message
    if message.recipient_id != current_user.id and message.sender_id != current_user.id:
        flash('You do not have permission to view this message', 'error')
        return redirect(url_for('messages.list_messages'))
    
    # Mark as read if recipient is viewing
    if message.recipient_id == current_user.id and not message.read:
        message.read = True
        db.session.commit()
        
        # If it's an AJAX request, return JSON response
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            unread_count = Message.query.filter_by(
                recipient_id=current_user.id,
                read=False
            ).count()
            return jsonify({
                'success': True,
                'unread_count': unread_count
            })
    
    return render_template('messages/view.html', message=message)

@messages.route('/messages/<int:message_id>/delete', methods=['POST'])
@login_required
def delete_message(message_id):
    message = Message.query.get_or_404(message_id)
    
    # Check if user has permission to delete this message
    if message.recipient_id != current_user.id and message.sender_id != current_user.id:
        flash('You do not have permission to delete this message', 'error')
        return redirect(url_for('messages.list_messages'))
    
    db.session.delete(message)
    db.session.commit()
    
    flash('Message deleted successfully', 'success')
    return redirect(url_for('messages.list_messages'))

@messages.route('/api/unread-count')
@login_required
def unread_count():
    count = Message.query.filter_by(
        recipient_id=current_user.id,
        read=False
    ).count()
    return jsonify({'count': count}) 