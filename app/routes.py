import os
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app, abort
from flask_login import login_user, logout_user, current_user, login_required
from app.extensions import db
from app.models import User, Car, RideRequest

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    cars = Car.query.all()
    return render_template('index.html', cars=cars)

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        location = request.form.get('location')
        if User.query.filter_by(username=username).first():
            flash('Usuário já existe.')
            return redirect(url_for('main.register'))
        user = User(username=username, location=location)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for('main.index'))
    return render_template('register.html')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user is None or not user.check_password(password):
            flash('Nome de usuário ou senha inválidos')
            return redirect(url_for('main.login'))
        login_user(user)
        return redirect(url_for('main.index'))
    return render_template('login.html')

@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.index'))

@bp.route('/dashboard')
@login_required
def dashboard():
    user_cars = current_user.cars.all()
    ride_requests = RideRequest.query.filter_by(owner_id=current_user.id).order_by(RideRequest.ride_date.desc()).all()
    all_cars = None
    if current_user.username == 'admin':
        all_cars = Car.query.all()
    return render_template('dashboard.html', cars=user_cars, all_cars=all_cars, ride_requests=ride_requests)

@bp.route('/cars', methods=['POST'])
@login_required
def add_car():
    model = request.form.get('model')
    brand = request.form.get('brand')
    mileage = request.form.get('mileage', type=int)
    modifications = request.form.get('modifications')
    location = request.form.get('location')
    horsepower = request.form.get('horsepower', type=int)
    
    photo_file = request.files.get('photo')
    photo_filename = None
    if photo_file and photo_file.filename != '':
        filename = secure_filename(photo_file.filename)
        os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
        photo_file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
        photo_filename = filename
    
    car = Car(model=model, brand=brand, mileage=mileage, modifications=modifications,
              location=location, horsepower=horsepower, photo=photo_filename, owner=current_user)
    db.session.add(car)
    db.session.commit()
    flash('Carro adicionado com sucesso!')
    return redirect(url_for('main.dashboard'))

@bp.route('/car/<int:id>')
def car_detail(id):
    car = Car.query.get_or_404(id)
    return render_template('car.html', car=car)

@bp.route('/car/<int:id>/rate', methods=['POST'])
@login_required
def rate_car_form(id):
    car = Car.query.get_or_404(id)
    rating = request.form.get('rating', type=float)
    if rating and 1 <= rating <= 5:
        car.visual_rating = ((car.visual_rating * car.rating_count) + rating) / (car.rating_count + 1)
        car.rating_count += 1
        db.session.commit()
        flash('Avaliação registrada com sucesso!')
    else:
        flash('Avaliação inválida (deve ser de 1 a 5).')
    return redirect(request.referrer or url_for('main.index'))

@bp.route('/car/<int:id>/delete', methods=['POST'])
@login_required
def delete_car(id):
    car = Car.query.get_or_404(id)
    is_owner = car.user_id == current_user.id
    admin_password = request.form.get('admin_password', '')
    is_admin = current_user.username == 'admin' and current_user.check_password(admin_password)
    if not is_owner and not is_admin:
        flash('Permissao negada.')
        return redirect(request.referrer or url_for('main.car_detail', id=id))

    if car.photo:
        photo_path = os.path.join(current_app.config['UPLOAD_FOLDER'], car.photo)
        if os.path.exists(photo_path):
            os.remove(photo_path)

    db.session.delete(car)
    db.session.commit()
    flash('Carro apagado com sucesso.')
    return redirect(url_for('main.index'))

@bp.route('/car/<int:id>/ride-request', methods=['POST'])
@login_required
def request_ride(id):
    car = Car.query.get_or_404(id)
    if car.user_id == current_user.id:
        flash('Nao e possivel pedir passeio no proprio carro.')
        return redirect(url_for('main.car_detail', id=id))

    ride_date_raw = request.form.get('ride_date', '').strip()
    message = request.form.get('message', '').strip() or None

    if not ride_date_raw:
        flash('Informe a data do passeio.')
        return redirect(url_for('main.car_detail', id=id))

    try:
        ride_date = datetime.strptime(ride_date_raw, '%Y-%m-%d').date()
    except ValueError:
        flash('Formato de data invalido (YYYY-MM-DD).')
        return redirect(url_for('main.car_detail', id=id))

    active_request = RideRequest.query.filter_by(
        car_id=car.id,
        ride_date=ride_date,
        status='approved'
    ).first()
    if active_request:
        flash('Carro indisponivel nessa data.')
        return redirect(url_for('main.car_detail', id=id))

    ride = RideRequest(
        requester_id=current_user.id,
        owner_id=car.user_id,
        car_id=car.id,
        ride_date=ride_date,
        message=message
    )
    db.session.add(ride)
    db.session.commit()
    flash('Pedido de passeio enviado!')
    return redirect(url_for('main.car_detail', id=id))

@bp.route('/rankings')
def rankings():
    fastest_cars = Car.query.order_by(Car.horsepower.desc()).limit(10).all()
    top_rated_cars = Car.query.order_by(Car.visual_rating.desc()).limit(10).all()
    return render_template('rankings.html', fastest=fastest_cars, toprated=top_rated_cars)

@bp.route('/admin/usuarios')
@login_required
def admin_users():
    if current_user.username != 'admin':
        abort(403)
    users = User.query.order_by(User.username.asc()).all()
    return render_template('admin_users.html', users=users)

@bp.route('/api/usuarios', methods=['GET'])
@login_required
def api_list_users():
    if current_user.username != 'admin':
        return jsonify({'error': 'Permissao negada'}), 403
    users = User.query.order_by(User.username.asc()).all()
    return jsonify([{
        'id': user.id,
        'username': user.username,
        'location': user.location
    } for user in users]), 200

@bp.route('/api/cars/<int:id>/rate', methods=['POST'])
@login_required
def rate_car(id):
    car = Car.query.get_or_404(id)
    rating = request.json.get('rating')
    if rating:
        rating = float(rating)
        car.visual_rating = ((car.visual_rating * car.rating_count) + rating) / (car.rating_count + 1)
        car.rating_count += 1
        db.session.commit()
        return jsonify({'message': 'Avaliação registrada', 'new_rating': car.visual_rating}), 200
    return jsonify({'error': 'Avaliação inválida'}), 400

@bp.route('/api/carros', methods=['GET'])
def api_list_cars():
    cars = Car.query.all()
    return jsonify([{
        'id': car.id,
        'brand': car.brand,
        'model': car.model,
        'mileage': car.mileage,
        'modifications': car.modifications,
        'location': car.location,
        'horsepower': car.horsepower,
        'visual_rating': car.visual_rating,
        'rating_count': car.rating_count,
        'photo': car.photo,
        'user_id': car.user_id
    } for car in cars]), 200

@bp.route('/api/carros', methods=['POST'])
@login_required
def api_create_car():
    data = request.json or {}
    if not data.get('brand') or not data.get('model'):
        return jsonify({'error': 'Campos obrigatorios: brand, model'}), 400

    car = Car(
        brand=data['brand'],
        model=data['model'],
        mileage=data.get('mileage', 0),
        modifications=data.get('modifications'),
        location=data.get('location'),
        horsepower=data.get('horsepower', 0),
        photo=data.get('photo'),
        user_id=current_user.id
    )
    db.session.add(car)
    db.session.commit()
    return jsonify({'message': 'Carro criado', 'id': car.id}), 201

@bp.route('/api/carros/<int:car_id>', methods=['GET'])
def api_get_car(car_id):
    car = Car.query.get_or_404(car_id)
    return jsonify({
        'id': car.id,
        'brand': car.brand,
        'model': car.model,
        'mileage': car.mileage,
        'modifications': car.modifications,
        'location': car.location,
        'horsepower': car.horsepower,
        'visual_rating': car.visual_rating,
        'rating_count': car.rating_count,
        'photo': car.photo,
        'user_id': car.user_id
    }), 200

@bp.route('/api/carros/<int:car_id>', methods=['PUT'])
@login_required
def api_update_car(car_id):
    car = Car.query.get_or_404(car_id)
    if car.user_id != current_user.id and current_user.username != 'admin':
        return jsonify({'error': 'Permissao negada'}), 403
    data = request.json or {}
    for field in ['brand', 'model', 'mileage', 'modifications', 'location', 'horsepower', 'photo']:
        if field in data:
            setattr(car, field, data[field])
    db.session.commit()
    return jsonify({'message': 'Carro atualizado'}), 200

@bp.route('/api/carros/<int:car_id>', methods=['DELETE'])
@login_required
def api_delete_car(car_id):
    car = Car.query.get_or_404(car_id)
    if car.user_id != current_user.id and current_user.username != 'admin':
        return jsonify({'error': 'Permissao negada'}), 403
    db.session.delete(car)
    db.session.commit()
    return jsonify({'message': 'Carro removido'}), 200

@bp.route('/api/emprestimos', methods=['GET', 'POST'])
@login_required
def api_ride_requests():
    if request.method == 'GET':
        if current_user.username == 'admin':
            rides = RideRequest.query.all()
        else:
            rides = RideRequest.query.filter(
                (RideRequest.requester_id == current_user.id) | (RideRequest.owner_id == current_user.id)
            ).all()
        return jsonify([{
            'id': ride.id,
            'requester_id': ride.requester_id,
            'owner_id': ride.owner_id,
            'car_id': ride.car_id,
            'ride_date': ride.ride_date.isoformat(),
            'message': ride.message,
            'status': ride.status
        } for ride in rides]), 200

    data = request.json or {}
    if not data.get('car_id') or not data.get('ride_date'):
        return jsonify({'error': 'Campos obrigatorios: car_id, ride_date'}), 400

    car = Car.query.get_or_404(data['car_id'])
    if car.user_id == current_user.id:
        return jsonify({'error': 'Nao e possivel pedir passeio no proprio carro'}), 400

    try:
        ride_date = datetime.strptime(data['ride_date'], '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Formato de data invalido (YYYY-MM-DD)'}), 400

    active_request = RideRequest.query.filter_by(car_id=car.id, ride_date=ride_date, status='approved').first()
    if active_request:
        return jsonify({'error': 'Carro indisponivel nessa data'}), 409

    ride = RideRequest(
        requester_id=current_user.id,
        owner_id=car.user_id,
        car_id=car.id,
        ride_date=ride_date,
        message=data.get('message')
    )
    db.session.add(ride)
    db.session.commit()
    return jsonify({'message': 'Pedido de passeio registrado', 'id': ride.id}), 201
