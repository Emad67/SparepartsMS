from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from models import db, Category

categories = Blueprint('categories', __name__)

@categories.route('/categories')
@login_required
def list_categories():
    categories = Category.query.all()
    return render_template('categories/list.html', categories=categories)

@categories.route('/categories/add', methods=['GET', 'POST'])
@login_required
def add_category():
    if request.method == 'POST':
        category = Category(
            name=request.form.get('name'),
            description=request.form.get('description')
        )
        db.session.add(category)
        db.session.commit()
        flash('Category added successfully')
        return redirect(url_for('categories.list_categories'))
    return render_template('categories/add.html')

@categories.route('/categories/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_category(id):
    category = Category.query.get_or_404(id)
    
    if request.method == 'POST':
        category.name = request.form.get('name')
        category.description = request.form.get('description')
        
        try:
            db.session.commit()
            flash('Category updated successfully', 'success')
            return redirect(url_for('categories.list_categories'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating category: {str(e)}', 'error')
            
    return render_template('categories/edit.html', category=category)

@categories.route('/categories/<int:id>/delete', methods=['POST'])
@login_required
def delete_category(id):
    category = Category.query.get_or_404(id)
    
    # Check if category has any parts
    if category.parts:
        flash('Cannot delete category that has parts assigned to it', 'error')
        return redirect(url_for('categories.list_categories'))
    
    try:
        db.session.delete(category)
        db.session.commit()
        flash('Category deleted successfully')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting category: {str(e)}', 'error')
    
    return redirect(url_for('categories.list_categories')) 