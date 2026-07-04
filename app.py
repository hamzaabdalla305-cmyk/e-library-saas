import os
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'change-this-secret-key')

db_url = os.environ.get('DATABASE_URL', 'sqlite:///library.db')
if db_url.startswith('postgres://'):
    db_url = db_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)


class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(100))
    description = db.Column(db.Text)
    copies_total = db.Column(db.Integer, default=1)
    copies_available = db.Column(db.Integer, default=1)


class BorrowRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    borrow_date = db.Column(db.DateTime, default=datetime.utcnow)
    return_date = db.Column(db.DateTime, nullable=True)
    user = db.relationship('User', backref='borrows')
    book = db.relationship('Book', backref='borrows')


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


with app.app_context():
    db.create_all()


@app.route('/')
def index():
    query = request.args.get('q', '')
    if query:
        books = Book.query.filter(
            Book.title.contains(query) | Book.author.contains(query)
        ).all()
    else:
        books = Book.query.all()
    return render_template('index.html', books=books, query=query)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        if User.query.filter_by(email=email).first():
            flash('البريد الإلكتروني مسجل مسبقاً')
            return redirect(url_for('register'))
        is_first_user = User.query.count() == 0
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            is_admin=is_first_user
        )
        db.session.add(user)
        db.session.commit()
        flash('تم إنشاء الحساب بنجاح، سجل دخولك الآن')
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('index'))
        flash('بيانات الدخول غير صحيحة')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/dashboard')
@login_required
def dashboard():
    borrows = BorrowRecord.query.filter_by(user_id=current_user.id, return_date=None).all()
    return render_template('dashboard.html', borrows=borrows)


@app.route('/books/add', methods=['GET', 'POST'])
@login_required
def add_book():
    if not current_user.is_admin:
        flash('غير مصرح لك بهذا الإجراء')
        return redirect(url_for('index'))
    if request.method == 'POST':
        book = Book(
            title=request.form['title'],
            author=request.form['author'],
            category=request.form.get('category'),
            description=request.form.get('description'),
            copies_total=int(request.form['copies']),
            copies_available=int(request.form['copies'])
        )
        db.session.add(book)
        db.session.commit()
        flash('تمت إضافة الكتاب بنجاح')
        return redirect(url_for('index'))
    return render_template('add_book.html')


@app.route('/books/<int:book_id>/borrow')
@login_required
def borrow_book(book_id):
    book = Book.query.get_or_404(book_id)
    if book.copies_available > 0:
        book.copies_available -= 1
        record = BorrowRecord(user_id=current_user.id, book_id=book.id)
        db.session.add(record)
        db.session.commit()
        flash('تم استعارة الكتاب بنجاح')
    else:
        flash('لا توجد نسخ متاحة حالياً')
    return redirect(url_for('index'))


@app.route('/books/<int:record_id>/return')
@login_required
def return_book(record_id):
    record = BorrowRecord.query.get_or_404(record_id)
    if record.user_id == current_user.id and not record.return_date:
        record.return_date = datetime.utcnow()
        record.book.copies_available += 1
        db.session.commit()
        flash('تم إرجاع الكتاب بنجاح')
    return redirect(url_for('dashboard'))


if __name__ == '__main__':
    app.run(debug=True)
