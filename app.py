from flask import Flask, render_template, request, session, jsonify, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import json
import os
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY') or 'kero_premium_2023_secure_key'
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour session lifetime

# ألوان وتنسيقات الموقع
THEME = {
    "primary": "#FFD700",
    "secondary": "#121212",
    "accent": "#E63946",
    "text": "#FFFFFF",
    "light_bg": "#1E1E1E",
    "rating_color": "#FFC107"
}

# ديكوراتور للتحقق من تسجيل الدخول
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# تحميل البيانات
def load_data(filename):
    data_file = os.path.join('static', 'data', filename)
    if os.path.exists(data_file):
        with open(data_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return [] if filename.endswith('.json') else {}

# حفظ البيانات
def save_data(filename, data):
    data_file = os.path.join('static', 'data', filename)
    with open(data_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# المسارات الرئيسية
@app.route('/')
def home():
    return render_template('index.html', theme=THEME)

@app.route('/menu')
def menu():
    menu_items = load_data('menu.json')
    return render_template('menu.html', menu=menu_items, theme=THEME)

@app.route('/item/<int:item_id>')
def item_details(item_id):
    menu_items = load_data('menu.json')
    item = next((item for item in menu_items if item['id'] == item_id), None)
    if item:
        return render_template('item.html', item=item, theme=THEME)
    return redirect('/menu')

# نظام المستخدمين
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        users = load_data('users.json')
        user = next((u for u in users if u['username'] == username), None)
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(request.args.get('next') or url_for('home'))
        
        return render_template('login.html', error='اسم المستخدم أو كلمة المرور غير صحيحة', theme=THEME)
    
    return render_template('login.html', theme=THEME)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')
        
        users = load_data('users.json')
        if any(u['username'] == username for u in users):
            return render_template('register.html', error='اسم المستخدم موجود بالفعل', theme=THEME)
        
        new_user = {
            'id': len(users) + 1,
            'username': username,
            'password': generate_password_hash(password),
            'email': email,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        users.append(new_user)
        save_data('users.json', users)
        
        session['user_id'] = new_user['id']
        session['username'] = username
        return redirect(url_for('home'))
    
    return render_template('register.html', theme=THEME)

# نظام السلة والطلبات
@app.route('/cart', methods=['GET', 'POST'])
@login_required
def cart():
    if request.method == 'POST':
        item_id = int(request.form.get('item_id'))
        quantity = int(request.form.get('quantity', 1))
        
        carts = load_data('carts.json')
        user_cart = carts.get(str(session['user_id']), {'items': [], 'total': 0})
        
        menu_items = load_data('menu.json')
        item = next((item for item in menu_items if item['id'] == item_id), None)
        
        if item:
            existing_item = next((i for i in user_cart['items'] if i['id'] == item_id), None)
            if existing_item:
                existing_item['quantity'] += quantity
            else:
                user_cart['items'].append({
                    'id': item_id,
                    'name': item['name'],
                    'price': item['price'],
                    'quantity': quantity,
                    'image': item['image']
                })
            
            user_cart['total'] = sum(i['price'] * i['quantity'] for i in user_cart['items'])
            carts[str(session['user_id'])] = user_cart
            save_data('carts.json', carts)
        
        return redirect(url_for('cart'))
    
    carts = load_data('carts.json')
    user_cart = carts.get(str(session['user_id']), {'items': [], 'total': 0})
    return render_template('cart.html', cart=user_cart, theme=THEME)

@app.route('/checkout', methods=['POST'])
@login_required
def checkout():
    carts = load_data('carts.json')
    user_cart = carts.get(str(session['user_id']), None)
    
    if user_cart and user_cart['items']:
        orders = load_data('orders.json')
        new_order = {
            'id': len(orders) + 1,
            'user_id': session['user_id'],
            'items': user_cart['items'],
            'total': user_cart['total'],
            'status': 'pending',
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        orders.append(new_order)
        save_data('orders.json', orders)
        
        # تفريغ السلة
        del carts[str(session['user_id'])]
        save_data('carts.json', carts)
        
        return render_template('order_confirmation.html', order=new_order, theme=THEME)
    
    return redirect(url_for('cart'))

# تهيئة الملفات عند التشغيل
def initialize_files():
    os.makedirs(os.path.join('static', 'data'), exist_ok=True)
    os.makedirs(os.path.join('static', 'images', 'menu'), exist_ok=True)
    
    # إنشاء ملفات البيانات إذا لم تكن موجودة
    if not os.path.exists(os.path.join('static', 'data', 'menu.json')):
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
                    {"id": 3, "name": "لحم بقر عضوي", "price": 25}
                ],
                "gallery": [
                    "truffle-pizza-1.jpg",
                    "truffle-pizza-2.jpg",
                    "truffle-pizza-3.jpg"
                ],
                "chef_recommended": True,
                "spicy_level": 0,
                "vegetarian": False
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
                    {"id": 3, "name": "زنجبيل مخلل", "price": 5}
                ],
                "gallery": [
                    "golden-sushi-1.jpg",
                    "golden-sushi-2.jpg",
                    "golden-sushi-3.jpg"
                ],
                "chef_recommended": True,
                "spicy_level": 2,
                "vegetarian": False
            }
        ])
    
    if not os.path.exists(os.path.join('static', 'data', 'users.json')):
        save_data('users.json', [])
    
    if not os.path.exists(os.path.join('static', 'data', 'carts.json')):
        save_data('carts.json', {})
    
    if not os.path.exists(os.path.join('static', 'data', 'orders.json')):
        save_data('orders.json', [])

if __name__ == '__main__':
    initialize_files()
    app.run(debug=True, port=5001)