from flask import render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash

from . import admin_bp
from .forms import UserForm
from extensions import db
from models import User

def admin_required(fn):
    from functools import wraps
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Apenas administradores.', 'warning')
            return redirect('/')
        return fn(*args, **kwargs)
    return wrapper

@admin_bp.route('/users')
@login_required
@admin_required
def users_list():
    users = User.query.order_by(User.name).all()
    return render_template('admin/users.html', users=users)

@admin_bp.route('/users/new', methods=['GET','POST'])
@login_required
@admin_required
def users_new():
    form = UserForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data.lower()).first():
            flash('Já existe usuário com esse e-mail.', 'danger')
        else:
            u = User(name=form.name.data.strip(), email=form.email.data.lower(),
                     role=form.role.data, is_active=form.is_active.data,
                     password_hash=generate_password_hash(form.password.data or 'changeme'))
            db.session.add(u)
            db.session.commit()
            flash('Usuário criado.', 'success')
            return redirect(url_for('admin.users_list'))
    return render_template('admin/user_form.html', form=form, mode='new')

@admin_bp.route('/users/<int:user_id>/edit', methods=['GET','POST'])
@login_required
@admin_required
def users_edit(user_id: int):
    u = User.query.get_or_404(user_id)
    form = UserForm(obj=u)
    if form.validate_on_submit():
        u.name = form.name.data.strip()
        u.email = form.email.data.lower()
        u.role = form.role.data
        u.is_active = form.is_active.data
        if form.password.data:
            u.password_hash = generate_password_hash(form.password.data)
        db.session.commit()
        flash('Usuário atualizado.', 'success')
        return redirect(url_for('admin.users_list'))
    return render_template('admin/user_form.html', form=form, mode='edit', user=u)

@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def users_delete(user_id: int):
    if current_user.id == user_id:
        flash('Você não pode excluir a si mesmo.', 'warning')
        return redirect(url_for('admin.users_list'))
    u = User.query.get_or_404(user_id)
    db.session.delete(u)
    db.session.commit()
    flash('Usuário excluído.', 'success')
    return redirect(url_for('admin.users_list'))
