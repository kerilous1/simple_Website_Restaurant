"""
Kero Restaurant — Flask Web Application
========================================

A Flask-based restaurant ordering system featuring:
  - User authentication (register / login / logout)
  - Menu browsing, grouped by category
  - Per-item detail pages with add-ons
  - Shopping cart (persisted per-user in JSON)
  - Order checkout and confirmation

Architecture
------------
- app.py          : Flask application, all routes and business logic
- static/data/    : JSON flat-file "database" (menu, users, carts, orders)
- templates/      : Jinja2 HTML templates (all extend base.html)
- static/css/     : Stylesheets
- static/js/      : Client-side JavaScript

Configuration
-------------
Set the ``SECRET_KEY`` environment variable before running in production.
See ``.env.example`` for details.
"""

import os
import uuid
import json
from datetime import datetime
from functools import wraps

from flask import (
    Flask,
    render_template,
    request,
    session,
    redirect,
    url_for,
    flash,
)
from werkzeug.security import generate_password_hash, check_password_hash

# ---------------------------------------------------------------------------
# Application setup
# ---------------------------------------------------------------------------

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'change-me-in-production')
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1-hour sessions

# Absolute path to the data directory — works regardless of CWD at startup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'static', 'data')


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def load_data(filename):
    """Load and return the contents of a JSON file from the data directory.

    Parameters
    ----------
    filename : str
        Bare filename, e.g. ``'menu.json'``.

    Returns
    -------
    list or dict
        Parsed JSON.  Returns ``[]`` for missing list files and ``{}``
        for missing dict files.  Returns the same safe defaults on parse
        errors, and prints a diagnostic message to stderr.
    """
    filepath = os.path.join(DATA_DIR, filename)
    default = [] if filename != 'carts.json' else {}
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return default
    except json.JSONDecodeError as exc:
        print(f'[ERROR] Could not parse {filename}: {exc}')
        return default


def save_data(filename, data):
    """Serialise *data* and write it to a JSON file in the data directory.

    Parameters
    ----------
    filename : str
        Bare filename, e.g. ``'carts.json'``.
    data : list or dict
        Data to serialise.

    Returns
    -------
    bool
        ``True`` on success, ``False`` if an OS error occurs.
    """
    filepath = os.path.join(DATA_DIR, filename)
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return True
    except OSError as exc:
        print(f'[ERROR] Could not write {filename}: {exc}')
        return False


# ---------------------------------------------------------------------------
# Authentication decorator
# ---------------------------------------------------------------------------

def login_required(f):
    """Route decorator that redirects unauthenticated users to the login page."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('يرجى تسجيل الدخول أولاً للوصول إلى هذه الصفحة', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


# ---------------------------------------------------------------------------
# Public routes
# ---------------------------------------------------------------------------

@app.route('/')
def home():
    """Render the restaurant landing / hero page."""
    return render_template('index.html', active_page='home')


@app.route('/menu')
def menu():
    """Render the full menu, items will be grouped by category in the template."""
    menu_items = load_data('menu.json')
    return render_template('menu.html', menu=menu_items, active_page='menu')


@app.route('/item/<int:item_id>')
def item_details(item_id):
    """Render the detail page for a single menu item.

    Parameters
    ----------
    item_id : int
        The unique identifier of the requested menu item.
    """
    menu_items = load_data('menu.json')
    item = next((i for i in menu_items if i['id'] == item_id), None)
    if item is None:
        flash('الصنف المطلوب غير موجود', 'error')
        return redirect(url_for('menu'))
    return render_template('item.html', item=item, active_page='menu')


# ---------------------------------------------------------------------------
# Authentication routes
# ---------------------------------------------------------------------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login.

    GET  — Render the login form.
    POST — Validate credentials; on success start an authenticated session.
    """
    if 'user_id' in session:
        return redirect(url_for('home'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            return render_template(
                'login.html',
                error='يرجى ملء جميع الحقول',
                active_page='login',
            )

        users = load_data('users.json')
        user = next((u for u in users if u['username'] == username), None)

        if user and check_password_hash(user['password'], password):
            session.permanent = True
            session['user_id'] = user['id']
            session['username'] = user['username']
            next_url = request.args.get('next')
            return redirect(next_url or url_for('home'))

        return render_template(
            'login.html',
            error='اسم المستخدم أو كلمة المرور غير صحيحة',
            active_page='login',
        )

    return render_template('login.html', active_page='login')


@app.route('/logout')
def logout():
    """Clear the current session and redirect to the home page."""
    session.clear()
    flash('تم تسجيل الخروج بنجاح', 'success')
    return redirect(url_for('home'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Handle new user registration.

    GET  — Render the registration form.
    POST — Validate fields, check for duplicate username / e-mail, create account.
    """
    if 'user_id' in session:
        return redirect(url_for('home'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        email = request.form.get('email', '').strip()

        # Required-field validation
        if not username or not password or not email:
            return render_template(
                'register.html',
                error='يرجى ملء جميع الحقول',
                active_page='login',
            )

        if len(password) < 6:
            return render_template(
                'register.html',
                error='يجب أن تكون كلمة المرور 6 أحرف على الأقل',
                active_page='login',
            )

        users = load_data('users.json')

        if any(u['username'] == username for u in users):
            return render_template(
                'register.html',
                error='اسم المستخدم موجود بالفعل',
                active_page='login',
            )

        if any(u.get('email') == email for u in users):
            return render_template(
                'register.html',
                error='البريد الإلكتروني مستخدم بالفعل',
                active_page='login',
            )

        new_user = {
            'id': str(uuid.uuid4()),
            'username': username,
            'password': generate_password_hash(password),
            'email': email,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
        users.append(new_user)
        save_data('users.json', users)

        session.permanent = True
        session['user_id'] = new_user['id']
        session['username'] = username
        flash('مرحباً بك! تم إنشاء حسابك بنجاح', 'success')
        return redirect(url_for('home'))

    return render_template('register.html', active_page='login')


# ---------------------------------------------------------------------------
# Cart routes
# ---------------------------------------------------------------------------

@app.route('/cart', methods=['GET', 'POST'])
@login_required
def cart():
    """Display the cart (GET) or add an item to it (POST).

    POST form parameters
    --------------------
    item_id : str
        ID of the menu item to add (will be cast to int).
    quantity : str, optional
        Number of units to add; defaults to ``'1'``.
    """
    if request.method == 'POST':
        try:
            item_id = int(request.form.get('item_id', ''))
            quantity = max(1, int(request.form.get('quantity', '1')))
        except (ValueError, TypeError):
            flash('طلب غير صالح', 'error')
            return redirect(url_for('cart'))

        carts = load_data('carts.json')
        menu_items = load_data('menu.json')
        item = next((i for i in menu_items if i['id'] == item_id), None)

        if item is None:
            flash('الصنف المطلوب غير موجود في القائمة', 'error')
            return redirect(url_for('menu'))

        user_key = str(session['user_id'])
        user_cart = carts.get(user_key, {'items': [], 'total': 0})

        existing = next(
            (i for i in user_cart['items'] if i['id'] == item_id), None
        )
        if existing:
            existing['quantity'] += quantity
        else:
            user_cart['items'].append({
                'id': item_id,
                'name': item['name'],
                'price': item['price'],
                'quantity': quantity,
                'image': item['image'],
            })

        user_cart['total'] = sum(
            i['price'] * i['quantity'] for i in user_cart['items']
        )
        carts[user_key] = user_cart
        save_data('carts.json', carts)

        flash(f'تم إضافة {item["name"]} إلى سلة التسوق', 'success')
        return redirect(url_for('cart'))

    # GET
    carts = load_data('carts.json')
    user_cart = carts.get(str(session['user_id']), {'items': [], 'total': 0})
    return render_template('cart.html', cart=user_cart, active_page='cart')


@app.route('/cart/remove/<int:item_id>', methods=['POST'])
@login_required
def remove_from_cart(item_id):
    """Remove a specific item from the current user's cart.

    Parameters
    ----------
    item_id : int
        The menu item ID to remove.
    """
    carts = load_data('carts.json')
    user_key = str(session['user_id'])
    user_cart = carts.get(user_key, {'items': [], 'total': 0})

    user_cart['items'] = [i for i in user_cart['items'] if i['id'] != item_id]
    user_cart['total'] = sum(
        i['price'] * i['quantity'] for i in user_cart['items']
    )
    carts[user_key] = user_cart
    save_data('carts.json', carts)

    flash('تم حذف الصنف من سلة التسوق', 'info')
    return redirect(url_for('cart'))


# ---------------------------------------------------------------------------
# Checkout route
# ---------------------------------------------------------------------------

@app.route('/checkout', methods=['POST'])
@login_required
def checkout():
    """Convert the current user's cart into a confirmed order.

    Clears the cart on success and renders the order confirmation page.
    """
    carts = load_data('carts.json')
    user_key = str(session['user_id'])
    user_cart = carts.get(user_key)

    if not user_cart or not user_cart.get('items'):
        flash('سلة التسوق فارغة', 'warning')
        return redirect(url_for('cart'))

    orders = load_data('orders.json')

    # Derive next ID from the current maximum to avoid collision after deletions
    next_id = max((o['id'] for o in orders), default=0) + 1

    new_order = {
        'id': next_id,
        'user_id': session['user_id'],
        'username': session['username'],
        'items': user_cart['items'],
        'total': user_cart['total'],
        'status': 'pending',
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }
    orders.append(new_order)
    save_data('orders.json', orders)

    # Clear the user's cart after a successful order
    del carts[user_key]
    save_data('carts.json', carts)

    return render_template(
        'order_confirmation.html', order=new_order, active_page=''
    )


# ---------------------------------------------------------------------------
# Application bootstrap
# ---------------------------------------------------------------------------

def initialize_data_files():
    """Ensure data directories and seed files exist before the app accepts requests.

    Creates ``static/data/`` and ``static/images/menu/`` if absent, then seeds
    ``menu.json`` with two example items and creates empty defaults for
    ``users.json``, ``carts.json``, and ``orders.json``.
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, 'static', 'images', 'menu'), exist_ok=True)

    if not os.path.exists(os.path.join(DATA_DIR, 'menu.json')):
        save_data('menu.json', [
            {
                "id": 1,
                "name": "بيتزا الترفل الأسود",
                "name_en": "Black Truffle Pizza",
                "image": "truffle-pizza.jpg",
                "price": 85,
                "category": "أطباق رئيسية",
                "rating": 4.8,
                "prep_time": "20-25 دقيقة",
                "calories": "850 سعرة",
                "description": "بيتزا فاخرة بصلصة الترفل الأسود النادر، جبنة موزاريلا عضوية، وفطر بورسيني طازج",
                "story": "وصفة حصرية من شيفنا الإيطالي الحائز على نجمة ميشلان",
                "addons": [
                    {"id": 1, "name": "شرائح الترفل الإضافية", "price": 40},
                    {"id": 2, "name": "جبنة بارميزان مبشورة", "price": 15},
                    {"id": 3, "name": "لحم بقر عضوي", "price": 25},
                ],
                "gallery": [
                    "truffle-pizza-1.jpg",
                    "truffle-pizza-2.jpg",
                    "truffle-pizza-3.jpg",
                ],
                "chef_recommended": True,
                "spicy_level": 0,
                "vegetarian": False,
            },
            {
                "id": 2,
                "name": "سوشي السلمون الذهبي",
                "name_en": "Golden Salmon Sushi",
                "image": "golden-sushi.jpg",
                "price": 120,
                "category": "مقبلات",
                "rating": 4.9,
                "prep_time": "15 دقيقة",
                "calories": "600 سعرة",
                "description": "سوشي سلمون مع رقائق الذهب الصالحة للأكل، أرز عضوي، وصوص خاص",
                "story": "وصفة مستوحاة من تقاليد طوكيو مع لمسة عصرية",
                "addons": [
                    {"id": 1, "name": "كافيار أسود", "price": 50},
                    {"id": 2, "name": "صوص واسابي إضافي", "price": 10},
                    {"id": 3, "name": "زنجبيل مخلل", "price": 5},
                ],
                "gallery": [
                    "golden-sushi-1.jpg",
                    "golden-sushi-2.jpg",
                    "golden-sushi-3.jpg",
                ],
                "chef_recommended": True,
                "spicy_level": 2,
                "vegetarian": False,
            },
        ])

    for filename, default in [
        ('users.json', []),
        ('carts.json', {}),
        ('orders.json', []),
    ]:
        if not os.path.exists(os.path.join(DATA_DIR, filename)):
            save_data(filename, default)


if __name__ == '__main__':
    initialize_data_files()
    app.run(debug=True, port=5001)