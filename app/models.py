from app.extensions import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    location = db.Column(db.String(120), nullable=True)
    cars = db.relationship('Car', backref='owner', lazy='dynamic')
    ride_requests = db.relationship('RideRequest', foreign_keys='RideRequest.requester_id', backref='requester', lazy='dynamic')
    ride_offers = db.relationship('RideRequest', foreign_keys='RideRequest.owner_id', backref='owner', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Car(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    model = db.Column(db.String(100), nullable=False)
    brand = db.Column(db.String(100), nullable=False)
    mileage = db.Column(db.Integer, default=0)
    modifications = db.Column(db.Text, nullable=True)
    location = db.Column(db.String(100), nullable=True)
    horsepower = db.Column(db.Integer, default=0)
    visual_rating = db.Column(db.Float, default=0.0)
    rating_count = db.Column(db.Integer, default=0)
    photo = db.Column(db.String(255), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

class RideRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    requester_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    car_id = db.Column(db.Integer, db.ForeignKey('car.id'), nullable=False)
    car = db.relationship('Car', backref='ride_requests', lazy='joined')
    ride_date = db.Column(db.Date, nullable=False)
    message = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), default='pending', nullable=False)
