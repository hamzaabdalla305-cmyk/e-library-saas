import os
import logging
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
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

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('e-library')


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='user')

    @property
    def is_admin(self):
        return self.role == 'admin'


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


class Subscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    plan = db.Column(db.String(50), default='Free')
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime, nullable=True)
    user = db.relationship('User', backref='subscriptions')


PLAN_LIMITS = {
    'Free': 2,
    'Basic': 5,
    'Premium': 10,
    'Enterprise': 999
}

CATEGORIES = [
    'هندسة البيانات',
    'تحليل البيانات',
    'علم البيانات',
    'التعلم الآلي',
    'الذكاء الاصطناعي',
    'أمن المعلومات والتشفير',
    'الشبكات',
    'تطوير الويب',
    'قواعد البيانات',
    'الحوسبة السحابية'
]


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


with app.app_context():
    db.create_all()


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            logger.warning(f'Unauthorized admin access attempt by user_id={getattr(current_user, "id", None)}')
            flash('غير مصرح لك بهذا الإجراء')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated


def get_active_plan(user):
    sub = Subscription.query.filter_by(user_id=user.id, end_date=None).order_by(Subscription.start_date.desc()).first()
    return sub.plan if sub else 'Free'


@app.route('/')
def index():
    query = request.args.get('q', '')
    category = request.args.get('category', '')
    books_query = Book.query
    if query:
        books_query = books_query.filter(
            Book.title.contains(query) | Book.author.contains(query)
        )
    if category:
        books_query = books_query.filter(Book.category == category)
    books = books_query.all()
    return render_template('index.html', books=books, query=query, categories=CATEGORIES, selected_category=category)


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
            role='admin' if is_first_user else 'user'
        )
        db.session.add(user)
        db.session.commit()
        db.session.add(Subscription(user_id=user.id, plan='Free'))
        db.session.commit()
        logger.info(f'New user registered: {email}')
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
            logger.info(f'User logged in: {email}')
            return redirect(url_for('index'))
        logger.warning(f'Failed login attempt: {email}')
        flash('بيانات الدخول غير صحيحة')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logger.info(f'User logged out: {current_user.email}')
    logout_user()
    return redirect(url_for('index'))


@app.route('/dashboard')
@login_required
def dashboard():
    borrows = BorrowRecord.query.filter_by(user_id=current_user.id, return_date=None).all()
    plan = get_active_plan(current_user)
    return render_template('dashboard.html', borrows=borrows, plan=plan, limit=PLAN_LIMITS.get(plan, 2))


@app.route('/books/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_book():
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
        logger.info(f'Book added: {book.title} by admin {current_user.email}')
        flash('تمت إضافة الكتاب بنجاح')
        return redirect(url_for('index'))
    return render_template('add_book.html', categories=CATEGORIES)


@app.route('/books/<int:book_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_book(book_id):
    book = Book.query.get_or_404(book_id)
    if request.method == 'POST':
        book.title = request.form['title']
        book.author = request.form['author']
        book.category = request.form.get('category')
        book.description = request.form.get('description')
        new_total = int(request.form['copies'])
        diff = new_total - book.copies_total
        book.copies_total = new_total
        book.copies_available = max(0, book.copies_available + diff)
        db.session.commit()
        logger.info(f'Book edited: {book.title} by admin {current_user.email}')
        flash('تم تعديل الكتاب بنجاح')
        return redirect(url_for('index'))
    return render_template('edit_book.html', book=book, categories=CATEGORIES)


@app.route('/books/<int:book_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_book(book_id):
    book = Book.query.get_or_404(book_id)
    BorrowRecord.query.filter_by(book_id=book.id).delete()
    db.session.delete(book)
    db.session.commit()
    logger.info(f'Book deleted: {book.title} by admin {current_user.email}')
    flash('تم حذف الكتاب بنجاح')
    return redirect(url_for('index'))


@app.route('/books/<int:book_id>/borrow')
@login_required
def borrow_book(book_id):
    if current_user.is_admin:
        flash('الأدمن لا يقوم بشراء الكتب')
        return redirect(url_for('index'))

    book = Book.query.get_or_404(book_id)
    plan = get_active_plan(current_user)
    limit = PLAN_LIMITS.get(plan, 2)
    active_borrows = BorrowRecord.query.filter_by(user_id=current_user.id, return_date=None).count()

    if active_borrows >= limit:
        flash(f'وصلت للحد الأقصى لباقتك ({plan}: {limit} كتب). قم بترقية اشتراكك.')
        return redirect(url_for('dashboard'))

    if book.copies_available > 0:
        book.copies_available -= 1
        record = BorrowRecord(user_id=current_user.id, book_id=book.id)
        db.session.add(record)
        db.session.commit()
        logger.info(f'Book borrowed: {book.title} by {current_user.email}')
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
        logger.info(f'Book returned: record_id={record_id} by {current_user.email}')
        flash('تم إرجاع الكتاب بنجاح')
    return redirect(url_for('dashboard'))


@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.get_json()
    if not data or not all(k in data for k in ('username', 'email', 'password')):
        return jsonify({'error': 'missing fields'}), 400
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'email already registered'}), 409
    user = User(
        username=data['username'],
        email=data['email'],
        password_hash=generate_password_hash(data['password']),
        role='user'
    )
    db.session.add(user)
    db.session.commit()
    db.session.add(Subscription(user_id=user.id, plan='Free'))
    db.session.commit()
    logger.info(f'API register: {data["email"]}')
    return jsonify({'message': 'user created', 'user_id': user.id}), 201


@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'missing fields'}), 400
    user = User.query.filter_by(email=data.get('email')).first()
    if user and check_password_hash(user.password_hash, data.get('password', '')):
        login_user(user)
        return jsonify({'message': 'login successful', 'user_id': user.id, 'role': user.role})
    return jsonify({'error': 'invalid credentials'}), 401


@app.route('/api/users', methods=['GET'])
@login_required
@admin_required
def api_get_users():
    users = User.query.all()
    return jsonify([{'id': u.id, 'username': u.username, 'email': u.email, 'role': u.role} for u in users])


@app.route('/api/books', methods=['GET'])
def api_get_books():
    books = Book.query.all()
    return jsonify([{
        'id': b.id, 'title': b.title, 'author': b.author,
        'category': b.category, 'copies_available': b.copies_available
    } for b in books])


@app.route('/api/subscription', methods=['POST'])
@login_required
def api_subscription():
    data = request.get_json()
    plan = data.get('plan') if data else None
    if plan not in PLAN_LIMITS:
        return jsonify({'error': 'invalid plan'}), 400
    old = Subscription.query.filter_by(user_id=current_user.id, end_date=None).first()
    if old:
        old.end_date = datetime.utcnow()
    new_sub = Subscription(user_id=current_user.id, plan=plan)
    db.session.add(new_sub)
    db.session.commit()
    logger.info(f'Subscription updated: user={current_user.email}, plan={plan}')
    return jsonify({'message': f'subscribed to {plan}'})


if __name__ == '__main__':
    app.run(debug=True)    plan = db.Column(db.String(50), default='Free')
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime, nullable=True)
    user = db.relationship('User', backref='subscriptions')


PLAN_LIMITS = {
    'Free': 2,
    'Basic': 5,
    'Premium': 10,
    'Enterprise': 999
}


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


with app.app_context():
    db.create_all()


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            logger.warning(f'Unauthorized admin access attempt by user_id={getattr(current_user, "id", None)}')
            flash('غير مصرح لك بهذا الإجراء')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated


def get_active_plan(user):
    sub = Subscription.query.filter_by(user_id=user.id, end_date=None).order_by(Subscription.start_date.desc()).first()
    return sub.plan if sub else 'Free'


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
            role='admin' if is_first_user else 'user'
        )
        db.session.add(user)
        db.session.commit()
        sub = Subscription(user_id=user.id, plan='Free')
        db.session.add(sub)
        db.session.commit()
        logger.info(f'New user registered: {email}')
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
            logger.info(f'User logged in: {email}')
            return redirect(url_for('index'))
        logger.warning(f'Failed login attempt: {email}')
        flash('بيانات الدخول غير صحيحة')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logger.info(f'User logged out: {current_user.email}')
    logout_user()
    return redirect(url_for('index'))


@app.route('/dashboard')
@login_required
def dashboard():
    borrows = BorrowRecord.query.filter_by(user_id=current_user.id, return_date=None).all()
    plan = get_active_plan(current_user)
    return render_template('dashboard.html', borrows=borrows, plan=plan, limit=PLAN_LIMITS.get(plan, 2))


@app.route('/books/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_book():
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
        logger.info(f'Book added: {book.title} by admin {current_user.email}')
        flash('تمت إضافة الكتاب بنجاح')
        return redirect(url_for('index'))
    return render_template('add_book.html')


@app.route('/books/<int:book_id>/borrow')
@login_required
def borrow_book(book_id):
    book = Book.query.get_or_404(book_id)
    plan = get_active_plan(current_user)
    limit = PLAN_LIMITS.get(plan, 2)
    active_borrows = BorrowRecord.query.filter_by(user_id=current_user.id, return_date=None).count()

    if active_borrows >= limit:
        flash(f'وصلت للحد الأقصى لباقتك ({plan}: {limit} كتب). قم بترقية اشتراكك.')
        return redirect(url_for('dashboard'))

    if book.copies_available > 0:
        book.copies_available -= 1
        record = BorrowRecord(user_id=current_user.id, book_id=book.id)
        db.session.add(record)
        db.session.commit()
        logger.info(f'Book borrowed: {book.title} by {current_user.email}')
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
        logger.info(f'Book returned: record_id={record_id} by {current_user.email}')
        flash('تم إرجاع الكتاب بنجاح')
    return redirect(url_for('dashboard'))


@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.get_json()
    if not data or not all(k in data for k in ('username', 'email', 'password')):
        return jsonify({'error': 'missing fields'}), 400
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'email already registered'}), 409
    user = User(
        username=data['username'],
        email=data['email'],
        password_hash=generate_password_hash(data['password']),
        role='user'
    )
    db.session.add(user)
    db.session.commit()
    db.session.add(Subscription(user_id=user.id, plan='Free'))
    db.session.commit()
    logger.info(f'API register: {data["email"]}')
    return jsonify({'message': 'user created', 'user_id': user.id}), 201


@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'missing fields'}), 400
    user = User.query.filter_by(email=data.get('email')).first()
    if user and check_password_hash(user.password_hash, data.get('password', '')):
        login_user(user)
        return jsonify({'message': 'login successful', 'user_id': user.id, 'role': user.role})
    return jsonify({'error': 'invalid credentials'}), 401


@app.route('/api/users', methods=['GET'])
@login_required
@admin_required
def api_get_users():
    users = User.query.all()
    return jsonify([{'id': u.id, 'username': u.username, 'email': u.email, 'role': u.role} for u in users])


@app.route('/api/books', methods=['GET'])
def api_get_books():
    books = Book.query.all()
    return jsonify([{
        'id': b.id, 'title': b.title, 'author': b.author,
        'category': b.category, 'copies_available': b.copies_available
    } for b in books])


@app.route('/api/subscription', methods=['POST'])
@login_required
def api_subscription():
    data = request.get_json()
    plan = data.get('plan') if data else None
    if plan not in PLAN_LIMITS:
        return jsonify({'error': 'invalid plan'}), 400
    old = Subscription.query.filter_by(user_id=current_user.id, end_date=None).first()
    if old:
        old.end_date = datetime.utcnow()
    new_sub = Subscription(user_id=current_user.id, plan=plan)
    db.session.add(new_sub)
    db.session.commit()
    logger.info(f'Subscription updated: user={current_user.email}, plan={plan}')
    return jsonify({'message': f'subscribed to {plan}'})


if __name__ == '__main__':
    app.run(debug=True)
