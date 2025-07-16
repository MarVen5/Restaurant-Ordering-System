from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime, timedelta
from functools import wraps
import random
from decimal import Decimal

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.permanent_session_lifetime = timedelta(days=7)  # 设置session有效期为7天

# 管理员权限装饰器
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'is_admin' not in session or not session['is_admin']:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# 用户登录装饰器
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# 数据库连接配置
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '123456',  # 根据实际情况修改密码
    'database': 'restaurant_db'
}

# 连接数据库
def get_db_connection():
    conn = mysql.connector.connect(**db_config)
    return conn

# 初始化reviews表
def init_reviews_table():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 创建评论表
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reviews (
                review_id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                bulk_order_id INT NOT NULL,
                rating INT NOT NULL CHECK (rating BETWEEN 1 AND 5),
                content TEXT NOT NULL,
                review_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                food_rating INT DEFAULT 5,
                service_rating INT DEFAULT 5,
                environment_rating INT DEFAULT 5,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (bulk_order_id) REFERENCES bulk_orders(bulk_order_id) ON DELETE CASCADE
            )
        ''')
        conn.commit()
        print("初始化评论表完成")
        
        # 检查是否已有评论
        cursor.execute('SELECT COUNT(*) as count FROM reviews')
        result = cursor.fetchone()
        
        # 如果没有评论，添加一些默认评论
        if result[0] == 0:
            # 创建一个默认用户（如果不存在）
            try:
                cursor.execute('SELECT user_id FROM users WHERE username = "系统管理员" LIMIT 1')
                admin_user = cursor.fetchone()
                if not admin_user:
                    hashed_password = generate_password_hash("admin123")
                    cursor.execute(
                        'INSERT INTO users (username, password, phone) VALUES (%s, %s, %s)',
                        ("系统管理员", hashed_password, "13800138000")
                    )
                    conn.commit()
                    admin_user_id = cursor.lastrowid
                else:
                    admin_user_id = admin_user[0]
                
                # 创建默认订单（如果没有订单）
                cursor.execute('SELECT bulk_order_id FROM bulk_orders LIMIT 1')
                default_order = cursor.fetchone()
                if not default_order:
                    cursor.execute(
                        '''INSERT INTO bulk_orders 
                            (user_id, total_amount, address, phone, payment_method, status, order_time, dining_type) 
                           VALUES (%s, 100.00, '', '', 'cash', '已完成', NOW(), 'dine-in')''',
                        (admin_user_id,)
                    )
                    conn.commit()
                    default_order_id = cursor.lastrowid
                else:
                    default_order_id = default_order[0]
                
                # 添加默认评论
                default_reviews = [
                    (admin_user_id, default_order_id, 5, "菜品非常美味，服务态度很好，环境优雅，强烈推荐！", 5, 5, 5),
                    (admin_user_id, default_order_id, 4, "菜品很棒，价格合理，就餐环境舒适，服务周到。", 5, 4, 5),
                    (admin_user_id, default_order_id, 5, "这家店的厨师很有水平，出品的菜肴味道独特，非常好吃！", 5, 5, 4),
                    (admin_user_id, default_order_id, 4, "环境不错，服务态度很好，菜品也很精致。", 4, 5, 5),
                    (admin_user_id, default_order_id, 5, "餐厅环境优雅，服务贴心，菜品美味可口，值得再次光顾。", 5, 5, 5)
                ]
                
                for review in default_reviews:
                    cursor.execute(
                        '''INSERT INTO reviews 
                            (user_id, bulk_order_id, rating, content, food_rating, service_rating, environment_rating, review_time) 
                           VALUES (%s, %s, %s, %s, %s, %s, %s, DATE_SUB(NOW(), INTERVAL RAND() * 30 DAY))''',
                        review
                    )
                
                conn.commit()
                print("添加默认评论完成")
            except mysql.connector.Error as err:
                print(f"添加默认评论失败: {err}")
                conn.rollback()
                
    except mysql.connector.Error as err:
        print(f"初始化评论表失败: {err}")
    
    cursor.close()
    conn.close()

# 初始化菜品数据
def init_dishes_data():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 检查菜品表是否为空
    cursor.execute('SELECT COUNT(*) as count FROM dishes')
    result = cursor.fetchone()
    
    if result['count'] == 0:
        # 如果菜品表为空，插入示例数据
        dishes_data = [
            # 主食类
            ('玛格丽特披萨', 68.00, '经典意式披萨，配以新鲜番茄酱、马苏里拉奶酪、罗勒叶和特级初榨橄榄油。', '/static/images/dish1.png', '主食'),
            ('意式肉酱面', 58.00, '意大利传统肉酱面，选用上等牛肉和猪肉混合慢炖，搭配新鲜番茄和香料，浇在手工制作的意面上。', '/static/images/dish2.png', '主食'),
            ('海鲜烩饭', 78.00, '西班牙风味海鲜烩饭，精选新鲜虾、贻贝、鱿鱼等海鲜，配以番红花米饭，口感鲜美。', '/static/images/dish3.png', '主食'),
            ('黑椒牛排', 128.00, '精选澳洲进口牛排，搭配黑椒汁，口感鲜嫩多汁，配以时令蔬菜和土豆泥。', '/static/images/dish4.png', '主食'),
            ('泰式炒河粉', 48.00, '泰国风味炒河粉，配以鲜虾、豆芽、葱花和花生碎，酸甜可口。', '/static/images/dish5.png', '主食'),

            # 小食类
            ('薯条', 28.00, '精选优质土豆，切条后油炸至金黄酥脆，搭配番茄酱和蒜香蛋黄酱。', '/static/images/dish6.png', '小食'),
            ('炸鸡翅', 42.00, '选用新鲜鸡翅，经过特制香料腌制，油炸至外酥里嫩，搭配特制酱料。', '/static/images/dish7.png', '小食'),
            ('芝士焗蘑菇', 38.00, '新鲜蘑菇填充香浓芝士，烤至金黄，外酥内软，奶香四溢。', '/static/images/dish8.png', '小食'),
            ('洋葱圈', 26.00, '新鲜洋葱切片，裹以特制面糊，炸至金黄酥脆，搭配蒜香酱。', '/static/images/dish9.png', '小食'),
            ('蒜香面包', 22.00, '法式面包涂抹大蒜黄油，烤至金黄，外酥内软，蒜香浓郁。', '/static/images/dish10.png', '小食'),

            # 饮品类
            ('鲜榨橙汁', 22.00, '使用新鲜橙子现场压榨，不添加任何糖分和防腐剂，保留水果的原始风味。', '/static/images/dish11.png', '饮品'),
            ('卡布奇诺', 25.00, '意式浓缩咖啡与蒸汽牛奶的完美结合，顶部撒有可可粉。', '/static/images/dish12.png', '饮品'),
            ('草莓奶昔', 28.00, '新鲜草莓与优质冰淇淋混合制成，口感丝滑，香甜可口。', '/static/images/dish13.png', '饮品'),
            ('柠檬冰茶', 18.00, '精选红茶搭配新鲜柠檬片和蜂蜜，冰镇后清爽解渴。', '/static/images/dish14.png', '饮品'),
            ('芒果冰沙', 26.00, '新鲜芒果打成冰沙，加入少量蜂蜜调味，口感顺滑，芒果香气浓郁。', '/static/images/dish15.png', '饮品'),

            # 沙拉类
            ('凯撒沙拉', 42.00, '新鲜罗马生菜，配以自制凯撒酱、帕玛森奶酪、香脆面包丁和烤鸡肉。', '/static/images/dish16.png', '沙拉'),
            ('希腊沙拉', 38.00, '新鲜番茄、黄瓜、红洋葱、橄榄和菲达奶酪，搭配特制橄榄油醋汁。', '/static/images/dish17.png', '沙拉'),
            ('水果沙拉', 36.00, '时令水果混合，搭配酸奶和蜂蜜，清新爽口。', '/static/images/dish18.png', '沙拉'),
            ('鲜虾牛油果沙拉', 58.00, '新鲜虾仁、牛油果、樱桃番茄和混合生菜，搭配柠檬汁和橄榄油。', '/static/images/dish19.png', '沙拉'),
            ('烟熏三文鱼沙拉', 62.00, '挪威烟熏三文鱼，搭配混合生菜、小番茄、红洋葱和酸豆，淋上特制酱汁。', '/static/images/dish20.png', '沙拉'),

            # 甜点类
            ('提拉米苏', 36.00, '经典意式甜点，由手指饼干浸泡咖啡酒，层叠马斯卡彭奶酪霜和可可粉制成。', '/static/images/dish21.png', '甜点'),
            ('芝士蛋糕', 32.00, '浓郁细腻的芝士蛋糕，底层为酥脆饼干，表面淋上新鲜水果酱。', '/static/images/dish22.png', '甜点'),
            ('巧克力熔岩蛋糕', 38.00, '外层松软，内含热熔巧克力，搭配香草冰淇淋，口感丰富。', '/static/images/dish23.png', '甜点'),
            ('焦糖布丁', 28.00, '细腻顺滑的焦糖布丁，表面覆盖一层香甜焦糖，入口即化。', '/static/images/dish24.png', '甜点'),
            ('水果塔', 34.00, '酥脆塔皮，填充香滑奶油，表面装饰时令水果，清新美味。', '/static/images/dish25.png', '甜点')
        ]
        
        for dish in dishes_data:
            try:
                cursor.execute(
                    'INSERT INTO dishes (name, price, description, image_url, category) VALUES (%s, %s, %s, %s, %s)',
                    dish
                )
            except mysql.connector.Error as err:
                print(f"Error inserting dish {dish[0]}: {err}")
                continue
        
        conn.commit()
        print("初始化菜品数据完成")
    
    cursor.close()
    conn.close()

# 初始化管理员账户
def init_admin():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # 检查users表是否有is_admin字段
        cursor.execute("SHOW COLUMNS FROM users LIKE 'is_admin'")
        has_admin_column = cursor.fetchone() is not None
        
        if not has_admin_column:
            print("users表缺少is_admin字段，请先运行update_db.py更新数据库结构")
            return
        
        # 检查是否已有管理员账户
        cursor.execute('SELECT * FROM users WHERE is_admin = TRUE LIMIT 1')
        admin = cursor.fetchone()
        
        if not admin:
            # 创建一个管理员账户
            hashed_password = generate_password_hash("admin123")
            try:
                cursor.execute(
                    'INSERT INTO users (username, password, phone, is_admin) VALUES (%s, %s, %s, %s)',
                    ("admin", hashed_password, "13800138000", True)
                )
                conn.commit()
                print("初始化管理员账户完成")
            except mysql.connector.Error as err:
                print(f"初始化管理员账户失败: {err}")
    except mysql.connector.Error as err:
        print(f"初始化管理员账户时出错: {err}")
    
    cursor.close()
    conn.close()

# 初始化餐桌数据
def init_tables():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # 创建tables表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tables (
                table_id INT AUTO_INCREMENT PRIMARY KEY,
                table_name VARCHAR(50) NOT NULL UNIQUE,
                seats INT NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'available'
            )
        ''')
        conn.commit()
        
        # 检查是否已有表数据
        cursor.execute('SELECT COUNT(*) as count FROM tables')
        result = cursor.fetchone()
        
        if result['count'] == 0:
            # 插入一些示例桌位
            tables_data = [
                ('A-1', 2, 'available'),
                ('A-2', 2, 'available'),
                ('A-3', 2, 'available'),
                ('B-1', 4, 'available'),
                ('B-2', 4, 'available'),
                ('B-3', 4, 'available'),
                ('C-1', 6, 'available'),
                ('C-2', 6, 'available'),
                ('D-1', 8, 'available'),
                ('VIP-1', 10, 'available')
            ]
            
            for table in tables_data:
                try:
                    cursor.execute(
                        'INSERT INTO tables (table_name, seats, status) VALUES (%s, %s, %s)',
                        table
                    )
                except mysql.connector.Error as err:
                    print(f"Error inserting table {table[0]}: {err}")
                    continue
            
            conn.commit()
            print("初始化餐桌数据完成")
    except mysql.connector.Error as err:
        print(f"初始化餐桌表失败: {err}")
    finally:
        cursor.close()
        conn.close()

# 初始化预订表
def init_reservations_table():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS table_reservations (
                reservation_id INT AUTO_INCREMENT PRIMARY KEY,
                table_id INT NOT NULL,
                user_id INT NOT NULL,
                reservation_time DATETIME NOT NULL,
                duration INT NOT NULL DEFAULT 120,
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                notes TEXT,
                people_count INT NOT NULL DEFAULT 2,
                FOREIGN KEY (table_id) REFERENCES tables(table_id),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')
        conn.commit()
        print("初始化预订表完成")
    except mysql.connector.Error as err:
        print(f"初始化预订表失败: {err}")
    
    cursor.close()
    conn.close()

# 首页路由
@app.route('/')
def index():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 获取主食类的前三项
    cursor.execute('SELECT * FROM dishes WHERE category = "主食" ORDER BY dish_id LIMIT 3')
    featured_dishes = cursor.fetchall()
    
    # 获取评论数据
    try:
        cursor.execute('SELECT r.*, u.username FROM reviews r JOIN users u ON r.user_id = u.user_id ORDER BY r.review_time DESC LIMIT 5')
        reviews = cursor.fetchall()
    except mysql.connector.Error:
        # 如果表不存在或查询失败，返回空列表
        reviews = []

    # 计算平均评分
    try:
        cursor.execute('SELECT AVG(rating) as avg_rating, COUNT(*) as total FROM reviews')
        rating_info = cursor.fetchone()
        if rating_info and rating_info['total'] > 0:
            average_rating = rating_info['avg_rating'] if rating_info['avg_rating'] else 0
            total_reviews = rating_info['total']
        else:
            average_rating = 0
            total_reviews = 0
    except mysql.connector.Error:
        # 如果表不存在或查询失败，设置默认值
        average_rating = 0
        total_reviews = 0
    
    cursor.close()
    conn.close()
    
    # 确保评分转换为0-10分制
    average_rating = min(average_rating * 2, 10) if average_rating > 0 else 0
    
    return render_template('index.html', 
                         featured_dishes=featured_dishes,
                         reviews=reviews,
                         average_rating=average_rating,
                         total_reviews=total_reviews)

# 登录路由
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
        user = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if user:
            is_valid_password = False
            
            # 管理员账户特殊处理：检查明文密码
            if user['username'] == 'admin' and user['is_admin'] and password == user['password']:
                is_valid_password = True
            # 普通用户使用安全的密码哈希验证
            elif check_password_hash(user['password'], password):
                is_valid_password = True
                
            if is_valid_password:
                session['user_id'] = user['user_id']
                session['username'] = user['username']
                session['is_admin'] = user['is_admin']
                
                # 如果是管理员，直接跳转到菜品管理页面，而不是仪表盘
                if user['is_admin']:
                    return redirect(url_for('admin_dishes'))
                else:
                    return redirect(url_for('menu'))
            else:
                return render_template('login.html', error='用户名或密码错误')
        else:
            return render_template('login.html', error='用户名或密码错误')
    
    return render_template('login.html')

# 注册路由
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        phone = request.form['phone']
        
        # 密码加密
        hashed_password = generate_password_hash(password)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 插入用户数据
            cursor.execute(
                'INSERT INTO users (username, password, phone) VALUES (%s, %s, %s)',
                (username, hashed_password, phone)
            )
            conn.commit()
            
            return redirect(url_for('login'))
        except mysql.connector.Error as err:
            return render_template('register.html', error=f'注册失败: {err}')
        finally:
            cursor.close()
            conn.close()
    
    return render_template('register.html')

# 主页路由
@app.route('/home')
def home():
    return redirect(url_for('index'))

# 菜单路由
@app.route('/menu')
@login_required
def menu():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 获取所有分类
    cursor.execute('SELECT DISTINCT category FROM dishes ORDER BY category')
    categories = [row['category'] for row in cursor.fetchall()]
    
    # 获取所有菜品，按sort_order排序
    cursor.execute('SELECT * FROM dishes ORDER BY category, sort_order, name')
    dishes = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('menu.html', dishes=dishes, categories=categories)

# 菜品搜索API
@app.route('/api/search_dishes')
@login_required
def search_dishes():
    if 'user_id' not in session:
        return jsonify({'error': '请先登录'}), 401
    
    query = request.args.get('query', '').strip()
    category = request.args.get('category', '')
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if category and category != 'all':
        cursor.execute(
            'SELECT * FROM dishes WHERE category = %s AND (name LIKE %s OR description LIKE %s) ORDER BY name',
            (category, f'%{query}%', f'%{query}%')
        )
    else:
        cursor.execute(
            'SELECT * FROM dishes WHERE name LIKE %s OR description LIKE %s ORDER BY category, name',
            (f'%{query}%', f'%{query}%')
        )
    
    dishes = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return jsonify(dishes)

# 获取菜品详情API
@app.route('/api/dish/<int:dish_id>')
@login_required
def get_dish_detail(dish_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute('SELECT * FROM dishes WHERE dish_id = %s', (dish_id,))
    dish = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    if dish:
        return jsonify(dish)
    else:
        return jsonify({'error': '菜品不存在'}), 404

# 菜品详情路由
@app.route('/dish/<int:dish_id>')
@login_required
def dish_detail(dish_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 获取菜品详情
    cursor.execute('SELECT * FROM dishes WHERE dish_id = %s', (dish_id,))
    dish = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    if dish:
        return render_template('dish_detail.html', dish=dish)
    else:
        return redirect(url_for('menu'))

# 下单路由
@app.route('/place_order', methods=['POST'])
@login_required
def place_order():
    dish_id = request.form['dish_id']
    quantity = int(request.form['quantity'])
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 获取菜品信息
    cursor.execute('SELECT * FROM dishes WHERE dish_id = %s', (dish_id,))
    dish = cursor.fetchone()
    
    if dish:
        # 计算订单金额
        amount = dish['price'] * quantity
        
        # 创建订单
        cursor.execute(
            'INSERT INTO orders (user_id, dish_name, quantity, amount, status, order_time) VALUES (%s, %s, %s, %s, %s, %s)',
            (session['user_id'], dish['name'], quantity, amount, '已下单', datetime.now())
        )
        conn.commit()
        
        # 获取新创建的订单ID
        order_id = cursor.lastrowid
        
        cursor.close()
        conn.close()
        
        return redirect(url_for('order_detail', order_id=order_id))
    
    cursor.close()
    conn.close()
    return redirect(url_for('menu'))

# 批量下单路由
@app.route('/place_bulk_order', methods=['POST'])
@login_required
def place_bulk_order():
    # 获取JSON数据
    data = request.json
    items = data.get('items', [])
    dining_type = data.get('diningType', 'dine-in')  # 就餐方式：堂食或外送
    address = data.get('address', '')
    phone = data.get('phone', '')
    payment = data.get('payment', '')
    total = data.get('total', 0)
    
    if not items:
        return jsonify({'success': False, 'message': '购物车为空'})
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # 创建订单主表记录
        cursor.execute(
            'INSERT INTO bulk_orders (user_id, total_amount, address, phone, payment_method, status, order_time, dining_type) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)',
            (session['user_id'], total, address, phone, payment, '已下单', datetime.now(), dining_type)
        )
        conn.commit()
        bulk_order_id = cursor.lastrowid
        
        # 创建订单详情记录
        for item in items:
            dish_id = item['id']
            quantity = item['quantity']
            price = item['price']
            amount = price * quantity
            
            cursor.execute(
                'INSERT INTO order_details (bulk_order_id, dish_id, dish_name, quantity, price, amount) VALUES (%s, %s, %s, %s, %s, %s)',
                (bulk_order_id, dish_id, item['name'], quantity, price, amount)
            )
        
        conn.commit()
        return jsonify({'success': True, 'message': '订单提交成功', 'order_id': bulk_order_id})
    
    except mysql.connector.Error as err:
        conn.rollback()
        return jsonify({'success': False, 'message': f'订单提交失败: {err}'})
    
    finally:
        cursor.close()
        conn.close()

# 订单详情路由
@app.route('/order/<int:order_id>')
@login_required
def order_detail(order_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 获取订单详情
    cursor.execute('SELECT * FROM orders WHERE order_id = %s AND user_id = %s', (order_id, session['user_id']))
    order = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    if order:
        return render_template('order_detail.html', order=order)
    else:
        return redirect(url_for('menu'))

# 批量订单详情路由
@app.route('/bulk_order/<int:bulk_order_id>')
@login_required
def bulk_order_detail(bulk_order_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 获取订单主表信息
    cursor.execute('SELECT * FROM bulk_orders WHERE bulk_order_id = %s AND user_id = %s', (bulk_order_id, session['user_id']))
    order = cursor.fetchone()
    
    if not order:
        cursor.close()
        conn.close()
        return redirect(url_for('menu'))
    
    # 获取订单详情
    cursor.execute('SELECT * FROM order_details WHERE bulk_order_id = %s', (bulk_order_id,))
    order_details = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('bulk_order_detail.html', order=order, order_details=order_details)

# 退出登录路由
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# 用户所有评论页面
@app.route('/my_reviews')
def my_reviews():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # 获取所有评论
        cursor.execute('''
            SELECT r.*, u.username 
            FROM reviews r
            JOIN users u ON r.user_id = u.user_id
            ORDER BY r.review_time DESC
        ''')
        
        reviews = []
        for row in cursor.fetchall():
            # 确保日期格式正确
            if isinstance(row['review_time'], bytes):
                try:
                    row['review_time'] = datetime.fromisoformat(row['review_time'].decode('utf-8'))
                except (UnicodeDecodeError, ValueError):
                    try:
                        row['review_time'] = datetime.fromisoformat(row['review_time'].decode('latin1'))
                    except (UnicodeDecodeError, ValueError):
                        row['review_time'] = datetime.now()
            
            reviews.append(row)
        
        # 计算平均评分
        cursor.execute('SELECT AVG(rating) as avg_rating, COUNT(*) as total FROM reviews')
        rating_info = cursor.fetchone()
        
        if rating_info and rating_info['avg_rating']:
            average_rating = float(rating_info['avg_rating'])
            total_reviews = int(rating_info['total'])
        else:
            average_rating = 0
            total_reviews = 0
        
        return render_template('my_reviews.html', 
                              reviews=reviews, 
                              average_rating=average_rating, 
                              total_reviews=total_reviews)
    except mysql.connector.Error as err:
        print(f"获取评论失败: {err}")
        flash('获取评论失败，请稍后再试', 'error')
        return redirect(url_for('index'))
    finally:
        cursor.close()
        conn.close()

# 添加评论
@app.route('/add_review/<int:bulk_order_id>', methods=['GET', 'POST'])
@login_required
def add_review(bulk_order_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 验证订单属于当前用户
    cursor.execute('SELECT * FROM bulk_orders WHERE bulk_order_id = %s AND user_id = %s', 
                  (bulk_order_id, session['user_id']))
    order = cursor.fetchone()
    
    if not order:
        flash('您无权为此订单添加评论', 'error')
        cursor.close()
        conn.close()
        return redirect(url_for('my_orders'))
    
    # 检查是否已经评论过
    cursor.execute('SELECT * FROM reviews WHERE bulk_order_id = %s AND user_id = %s', 
                  (bulk_order_id, session['user_id']))
    existing_review = cursor.fetchone()
    
    if existing_review:
        flash('您已经评论过此订单', 'error')
        cursor.close()
        conn.close()
        return redirect(url_for('my_orders'))
    
    if request.method == 'POST':
        rating = int(request.form.get('rating', 5))
        food_rating = int(request.form.get('food_rating', 5))
        service_rating = int(request.form.get('service_rating', 5))
        environment_rating = int(request.form.get('environment_rating', 5))
        content = request.form.get('content', '').strip()
        
        # 验证评分范围
        if rating < 1 or rating > 5:
            rating = 5
        if food_rating < 1 or food_rating > 5:
            food_rating = 5
        if service_rating < 1 or service_rating > 5:
            service_rating = 5
        if environment_rating < 1 or environment_rating > 5:
            environment_rating = 5
        
        # 验证内容不为空
        if not content:
            flash('评论内容不能为空', 'error')
        else:
            # 添加评论
            try:
                cursor.execute(
                    '''INSERT INTO reviews 
                       (user_id, bulk_order_id, rating, content, food_rating, service_rating, environment_rating) 
                       VALUES (%s, %s, %s, %s, %s, %s, %s)''',
                    (session['user_id'], bulk_order_id, rating, content, food_rating, service_rating, environment_rating)
                )
                conn.commit()
                flash('评论添加成功', 'success')
                cursor.close()
                conn.close()
                return redirect(url_for('my_reviews'))
            except mysql.connector.Error as err:
                print(f"添加评论失败: {err}")
                flash('添加评论失败，请稍后再试', 'error')
                conn.rollback()
    
    # 获取订单详情
    cursor.execute('''
        SELECT od.*, d.name as dish_name 
        FROM order_details od 
        JOIN dishes d ON od.dish_id = d.dish_id 
        WHERE od.bulk_order_id = %s
    ''', (bulk_order_id,))
    order_details = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('add_review.html', order=order, order_details=order_details)

# 编辑评论
@app.route('/edit_review/<int:review_id>', methods=['GET', 'POST'])
@login_required
def edit_review(review_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 验证评论属于当前用户
    cursor.execute('SELECT * FROM reviews WHERE review_id = %s AND user_id = %s', 
                  (review_id, session['user_id']))
    review = cursor.fetchone()
    
    if not review:
        flash('您无权编辑此评论', 'error')
        cursor.close()
        conn.close()
        return redirect(url_for('my_reviews'))
    
    if request.method == 'POST':
        rating = int(request.form.get('rating', 5))
        food_rating = int(request.form.get('food_rating', 5))
        service_rating = int(request.form.get('service_rating', 5))
        environment_rating = int(request.form.get('environment_rating', 5))
        content = request.form.get('content', '').strip()
        
        # 验证评分范围
        if rating < 1 or rating > 5:
            rating = 5
        if food_rating < 1 or food_rating > 5:
            food_rating = 5
        if service_rating < 1 or service_rating > 5:
            service_rating = 5
        if environment_rating < 1 or environment_rating > 5:
            environment_rating = 5
        
        # 验证内容不为空
        if not content:
            flash('评论内容不能为空', 'error')
        else:
            # 更新评论
            try:
                cursor.execute(
                    '''UPDATE reviews 
                       SET rating = %s, content = %s, food_rating = %s, service_rating = %s, environment_rating = %s, review_time = %s
                       WHERE review_id = %s AND user_id = %s''',
                    (rating, content, food_rating, service_rating, environment_rating, datetime.now(), review_id, session['user_id'])
                )
                conn.commit()
                flash('评论更新成功', 'success')
                cursor.close()
                conn.close()
                return redirect(url_for('my_reviews'))
            except mysql.connector.Error as err:
                print(f"更新评论失败: {err}")
                flash('更新评论失败，请稍后再试', 'error')
                conn.rollback()
    
    # 获取订单详情
    cursor.execute('''
        SELECT bo.*, od.*, d.name as dish_name 
        FROM bulk_orders bo
        JOIN order_details od ON bo.bulk_order_id = od.bulk_order_id
        JOIN dishes d ON od.dish_id = d.dish_id 
        WHERE bo.bulk_order_id = %s
    ''', (review['bulk_order_id'],))
    order_details = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('edit_review.html', review=review, order_details=order_details)

# 删除评论
@app.route('/delete_review/<int:review_id>', methods=['POST'])
@login_required
def delete_review(review_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 验证评论属于当前用户
    cursor.execute('SELECT * FROM reviews WHERE review_id = %s AND user_id = %s', 
                  (review_id, session['user_id']))
    review = cursor.fetchone()
    
    if not review:
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': '您无权删除此评论'})
    
    # 删除评论
    try:
        cursor.execute('DELETE FROM reviews WHERE review_id = %s AND user_id = %s', 
                      (review_id, session['user_id']))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'success': True})
    except mysql.connector.Error as err:
        print(f"删除评论失败: {err}")
        conn.rollback()
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': '删除评论失败，请稍后再试'})

# 管理员面板路由 - 重定向到菜品管理页面
@app.route('/admin')
@admin_required
def admin_dashboard():
    return redirect(url_for('admin_dishes'))

# 管理员菜品管理
@app.route('/admin/dishes', methods=['GET', 'POST', 'DELETE'])
@admin_required
def admin_dishes():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        # 添加新菜品
        name = request.form['name']
        price = float(request.form['price'])
        description = request.form['description']
        category = request.form['category']
        image_url = request.form.get('image_url', f'/static/images/dish{random.randint(1, 25)}.png')
        
        try:
            cursor.execute(
                'INSERT INTO dishes (name, price, description, category, image_url) VALUES (%s, %s, %s, %s, %s)',
                (name, price, description, category, image_url)
            )
            conn.commit()
            flash('菜品添加成功', 'success')
        except mysql.connector.Error as err:
            flash(f'添加失败: {err}', 'error')
    
    # 获取所有菜品
    cursor.execute('SELECT * FROM dishes ORDER BY category, sort_order, name')
    dishes = cursor.fetchall()
    
    # 获取所有分类
    cursor.execute('SELECT DISTINCT category FROM dishes ORDER BY category')
    categories = [row['category'] for row in cursor.fetchall()]
    
    cursor.close()
    conn.close()
    
    return render_template('admin/dishes.html', dishes=dishes, categories=categories)

# 管理员修改菜品
@app.route('/admin/dishes/<int:dish_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_dish(dish_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        # 更新菜品
        name = request.form['name']
        price = float(request.form['price'])
        description = request.form['description']
        category = request.form['category']
        image_url = request.form.get('image_url', '')
        
        try:
            cursor.execute(
                'UPDATE dishes SET name = %s, price = %s, description = %s, category = %s, image_url = %s WHERE dish_id = %s',
                (name, price, description, category, image_url, dish_id)
            )
            conn.commit()
            flash('菜品更新成功', 'success')
            return redirect(url_for('admin_dishes'))
        except mysql.connector.Error as err:
            flash(f'更新失败: {err}', 'error')
    
    # 获取菜品详情
    cursor.execute('SELECT * FROM dishes WHERE dish_id = %s', (dish_id,))
    dish = cursor.fetchone()
    
    # 获取所有分类
    cursor.execute('SELECT DISTINCT category FROM dishes ORDER BY category')
    categories = [row['category'] for row in cursor.fetchall()]
    
    cursor.close()
    conn.close()
    
    if not dish:
        flash('菜品不存在', 'error')
        return redirect(url_for('admin_dishes'))
    
    return render_template('admin/edit_dish.html', dish=dish, categories=categories)

# 管理员删除菜品
@app.route('/admin/dishes/<int:dish_id>/delete', methods=['POST'])
@admin_required
def admin_delete_dish(dish_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 首先检查菜品是否在订单中被引用
        cursor.execute('SELECT COUNT(*) FROM order_details WHERE dish_id = %s', (dish_id,))
        count = cursor.fetchone()[0]
        
        if count > 0:
            # 如果菜品已被订单引用，提示无法删除
            flash(f'无法删除该菜品，因为它被 {count} 个订单引用', 'error')
        else:
            # 如果没有引用，则安全删除
            cursor.execute('DELETE FROM dishes WHERE dish_id = %s', (dish_id,))
            conn.commit()
            flash('菜品已删除', 'success')
    except mysql.connector.Error as err:
        flash(f'删除失败: {err}', 'error')
    
    cursor.close()
    conn.close()
    
    return redirect(url_for('admin_dishes'))

# 管理员查看所有订单
@app.route('/admin/orders')
@admin_required
def admin_orders():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 获取所有订单
    cursor.execute('''
        SELECT bo.*, u.username 
        FROM bulk_orders bo 
        JOIN users u ON bo.user_id = u.user_id 
        ORDER BY bo.order_time DESC
    ''')
    orders = cursor.fetchall()
    
    # 将中文状态转换为英文状态，以便在模板中正确显示
    for order in orders:
        if order['status'] == '待处理':
            order['status'] = 'pending'
        elif order['status'] == '处理中':
            order['status'] = 'preparing'
        elif order['status'] == '已完成':
            order['status'] = 'completed'
        elif order['status'] == '已取消':
            order['status'] = 'cancelled'
    
    cursor.close()
    conn.close()
    
    return render_template('admin/orders.html', orders=orders)

# 管理员查看订单详情
@app.route('/admin/orders/<int:order_id>')
@admin_required
def admin_order_detail(order_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 获取订单主表信息
    cursor.execute('''
        SELECT bo.*, u.username, u.phone as user_phone 
        FROM bulk_orders bo 
        JOIN users u ON bo.user_id = u.user_id 
        WHERE bo.bulk_order_id = %s
    ''', (order_id,))
    order = cursor.fetchone()
    
    if not order:
        flash('订单不存在', 'error')
        return redirect(url_for('admin_orders'))
    
    # 获取订单详情
    cursor.execute('SELECT * FROM order_details WHERE bulk_order_id = %s', (order_id,))
    order_details = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('admin/order_detail.html', order=order, order_details=order_details)

# 管理员更新订单状态（处理表单提交）
@app.route('/admin/orders/update/<int:order_id>', methods=['POST'])
@admin_required
def admin_update_order(order_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    status = request.form['status']
    
    try:
        cursor.execute(
            'UPDATE bulk_orders SET status = %s WHERE bulk_order_id = %s',
            (status, order_id)
        )
        conn.commit()
        flash('订单状态已更新', 'success')
    except mysql.connector.Error as err:
        flash(f'更新失败: {err}', 'error')
    
    cursor.close()
    conn.close()
    
    return redirect(url_for('admin_order_detail', order_id=order_id))

# 管理员更新订单状态（处理AJAX请求）
@app.route('/admin/orders/<int:order_id>/update', methods=['POST'])
@admin_required
def admin_update_order_ajax(order_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    status = request.form['status']
    
    # 将英文状态转换为中文状态（如果需要的话）
    status_mapping = {
        'pending': '待处理',
        'preparing': '处理中',
        'completed': '已完成',
        'cancelled': '已取消'
    }
    
    # 如果状态是英文格式，转换为中文
    if status in status_mapping:
        db_status = status_mapping[status]
    else:
        db_status = status  # 如果已经是中文，直接使用
    
    try:
        cursor.execute(
            'UPDATE bulk_orders SET status = %s WHERE bulk_order_id = %s',
            (db_status, order_id)
        )
        conn.commit()
        response = {'success': True, 'message': '订单状态已更新'}
    except mysql.connector.Error as err:
        response = {'success': False, 'message': f'更新失败: {str(err)}'}
    
    cursor.close()
    conn.close()
    
    return jsonify(response)

# 管理员桌位管理
@app.route('/admin/tables', methods=['GET', 'POST'])
@admin_required
def admin_tables():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        # 添加新桌位
        table_name = request.form['table_name']
        seats = int(request.form['seats'])
        
        try:
            cursor.execute(
                'INSERT INTO tables (table_name, seats, status) VALUES (%s, %s, %s)',
                (table_name, seats, 'available')
            )
            conn.commit()
            flash('桌位添加成功', 'success')
        except mysql.connector.Error as err:
            flash(f'添加失败: {err}', 'error')
    
    # 获取所有桌位
    cursor.execute('SELECT * FROM tables ORDER BY table_name')
    tables = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('admin/tables.html', tables=tables)

# 管理员修改桌位
@app.route('/admin/tables/<int:table_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_table(table_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        # 更新桌位
        table_name = request.form['table_name']
        seats = int(request.form['seats'])
        status = request.form['status']
        
        try:
            cursor.execute(
                'UPDATE tables SET table_name = %s, seats = %s, status = %s WHERE table_id = %s',
                (table_name, seats, status, table_id)
            )
            conn.commit()
            flash('桌位更新成功', 'success')
            return redirect(url_for('admin_tables'))
        except mysql.connector.Error as err:
            flash(f'更新失败: {err}', 'error')
    
    # 获取桌位详情
    cursor.execute('SELECT * FROM tables WHERE table_id = %s', (table_id,))
    table = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    if not table:
        flash('桌位不存在', 'error')
        return redirect(url_for('admin_tables'))
    
    return render_template('admin/edit_table.html', table=table)

# 管理员删除桌位
@app.route('/admin/tables/<int:table_id>/delete', methods=['POST'])
@admin_required
def admin_delete_table(table_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('DELETE FROM tables WHERE table_id = %s', (table_id,))
        conn.commit()
        flash('桌位已删除', 'success')
    except mysql.connector.Error as err:
        flash(f'删除失败: {err}', 'error')
    
    cursor.close()
    conn.close()
    
    return redirect(url_for('admin_tables'))

# 管理员查看预订
@app.route('/admin/reservations')
@admin_required
def admin_reservations():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 获取所有预订
    cursor.execute('''
        SELECT r.*, t.table_name, u.username, u.phone
        FROM table_reservations r
        JOIN tables t ON r.table_id = t.table_id
        JOIN users u ON r.user_id = u.user_id
        ORDER BY r.reservation_time DESC
    ''')
    reservations = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('admin/reservations.html', reservations=reservations)

# 用户查看桌位状态
@app.route('/tables')
@login_required
def tables():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 获取所有可用桌位
    cursor.execute("SELECT * FROM tables WHERE status = 'available' ORDER BY seats")
    available_tables = cursor.fetchall()
    
    # 获取所有预订桌位
    cursor.execute("SELECT * FROM tables WHERE status = 'reserved' ORDER BY seats")
    reserved_tables = cursor.fetchall()
    
    # 获取所有使用中桌位
    cursor.execute("SELECT * FROM tables WHERE status = 'occupied' ORDER BY seats")
    occupied_tables = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('tables.html', 
                          available_tables=available_tables, 
                          reserved_tables=reserved_tables, 
                          occupied_tables=occupied_tables)

# 用户预订桌位页面
@app.route('/reservation/<int:table_id>', methods=['GET', 'POST'])
@login_required
def reserve_table(table_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 获取桌位信息
    cursor.execute('SELECT * FROM tables WHERE table_id = %s', (table_id,))
    table = cursor.fetchone()
    
    if not table:
        flash('桌位不存在', 'error')
        return redirect(url_for('tables'))
    
    if table['status'] != 'available':
        flash('该桌位当前不可预订', 'error')
        return redirect(url_for('tables'))
    
    # 获取当前时间，格式化为datetime-local输入字段可用的格式
    now = datetime.now()
    now_formatted = now.strftime('%Y-%m-%dT%H:%M')
    
    if request.method == 'POST':
        # 处理预订提交
        reservation_time = request.form['reservation_time']
        duration = int(request.form['duration'])
        people_count = int(request.form['people_count'])
        notes = request.form['notes']
        
        # 验证数据
        if people_count > table['seats']:
            flash(f'预订人数不能超过桌位容量（{table["seats"]}人）', 'error')
            return render_template('reservation.html', table=table, now_formatted=now_formatted)
        
        try:
            # 创建预订记录 - 使用datetime对象而不是字符串
            reservation_datetime = datetime.strptime(reservation_time, '%Y-%m-%dT%H:%M')
            # 直接插入confirmed状态
            cursor.execute(
                '''INSERT INTO table_reservations 
                    (table_id, user_id, reservation_time, duration, status, notes, people_count) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s)''',
                (table_id, session['user_id'], reservation_datetime, duration, 'confirmed', notes, people_count)
            )
            # 同时将桌位状态设为reserved
            cursor.execute('UPDATE tables SET status = %s WHERE table_id = %s', ('reserved', table_id))
            conn.commit()
            flash('预订成功！', 'success')
            return redirect(url_for('my_reservations'))
        except mysql.connector.Error as err:
            flash(f'预订失败: {err}', 'error')
        except ValueError as e:
            flash(f'日期格式错误: {e}', 'error')
    
    cursor.close()
    conn.close()
    
    return render_template('reservation.html', table=table, now_formatted=now_formatted)

# 用户查看自己的预订
@app.route('/my_reservations')
@login_required
def my_reservations():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # 获取用户所有预订
        cursor.execute('''
            SELECT r.*, t.table_name, t.seats
            FROM table_reservations r
            JOIN tables t ON r.table_id = t.table_id
            WHERE r.user_id = %s
            ORDER BY r.reservation_time DESC
        ''', (session['user_id'],))
        
        reservations = []
        for row in cursor.fetchall():
            # 确保日期格式正确
            if isinstance(row['reservation_time'], bytes):
                try:
                    # 尝试使用latin1编码，这通常适用于MySQL的二进制日期
                    row['reservation_time'] = datetime.fromisoformat(row['reservation_time'].decode('latin1'))
                except (UnicodeDecodeError, ValueError):
                    try:
                        # 尝试使用cp1252编码
                        row['reservation_time'] = datetime.fromisoformat(row['reservation_time'].decode('cp1252'))
                    except (UnicodeDecodeError, ValueError):
                        try:
                            # 尝试使用utf-8编码，忽略错误
                            row['reservation_time'] = datetime.fromisoformat(row['reservation_time'].decode('utf-8', 'ignore'))
                        except (UnicodeDecodeError, ValueError):
                            try:
                                # 尝试使用ascii编码，忽略错误
                                row['reservation_time'] = datetime.fromisoformat(row['reservation_time'].decode('ascii', 'ignore'))
                            except (UnicodeDecodeError, ValueError):
                                try:
                                    # 尝试直接使用字符串表示
                                    row['reservation_time'] = str(row['reservation_time'])
                                except:
                                    # 如果所有尝试都失败，使用当前时间
                                    row['reservation_time'] = datetime.now()
            reservations.append(row)
    except Exception as e:
        flash(f'获取预订信息失败: {e}', 'error')
        reservations = []
    
    cursor.close()
    conn.close()
    
    return render_template('my_reservations.html', reservations=reservations)

# 用户取消预订
@app.route('/my_reservations/<int:reservation_id>/cancel', methods=['POST'])
@login_required
def cancel_reservation(reservation_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 验证预订属于当前用户
    cursor.execute(
        'SELECT * FROM table_reservations WHERE reservation_id = %s AND user_id = %s',
        (reservation_id, session['user_id'])
    )
    reservation = cursor.fetchone()
    
    if not reservation:
        flash('预订不存在或您无权取消', 'error')
        return redirect(url_for('my_reservations'))
    
    # 只有待确认或已确认的预订可以取消
    if reservation['status'] not in ['pending', 'confirmed']:
        flash('该预订状态无法取消', 'error')
        return redirect(url_for('my_reservations'))
    
    try:
        # 更新预订状态为已取消
        cursor.execute('UPDATE table_reservations SET status = %s WHERE reservation_id = %s', ('cancelled', reservation_id))
        conn.commit()
        
        # 如果预订已确认，则将桌位状态改回可用
        if reservation['status'] == 'confirmed':
            cursor.execute('UPDATE tables SET status = %s WHERE table_id = %s', ('available', reservation['table_id']))
            conn.commit()
        
        flash('预订已成功取消', 'success')
    except mysql.connector.Error as err:
        flash(f'取消失败: {err}', 'error')
    
    cursor.close()
    conn.close()
    
    return redirect(url_for('my_reservations'))

# 用户查看自己的订单
@app.route('/my_orders')
@login_required
def my_orders():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 获取用户的所有订单
    cursor.execute('''
        SELECT * FROM bulk_orders
        WHERE user_id = %s
        ORDER BY order_time DESC
    ''', (session['user_id'],))
    orders = cursor.fetchall()
    
    # 确保订单状态为英文，以便在模板中正确分类
    for order in orders:
        # 将中文状态转换为英文状态
        if order['status'] == '已下单':
            order['status'] = 'pending'
        elif order['status'] == '准备中':
            order['status'] = 'preparing'
        elif order['status'] == '已完成':
            order['status'] = 'completed'
        elif order['status'] == '已取消':
            order['status'] = 'cancelled'
    
    cursor.close()
    conn.close()
    
    return render_template('my_orders.html', orders=orders)

# 直接发布评论
@app.route('/post_review', methods=['POST'])
@login_required
def post_review():
    if request.method == 'POST':
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        rating = int(request.form.get('rating', 5))
        food_rating = int(request.form.get('food_rating', 5))
        service_rating = int(request.form.get('service_rating', 5))
        environment_rating = int(request.form.get('environment_rating', 5))
        content = request.form.get('content', '').strip()
        
        # 验证评分范围
        if rating < 1 or rating > 5:
            rating = 5
        if food_rating < 1 or food_rating > 5:
            food_rating = 5
        if service_rating < 1 or service_rating > 5:
            service_rating = 5
        if environment_rating < 1 or environment_rating > 5:
            environment_rating = 5
        
        # 验证内容不为空
        if not content:
            flash('评论内容不能为空', 'error')
            cursor.close()
            conn.close()
            return redirect(url_for('my_reviews'))
        
        # 添加评论
        try:
            # 不需要bulk_order_id字段
            cursor.execute(
                '''INSERT INTO reviews 
                   (user_id, rating, content, food_rating, service_rating, environment_rating, review_time) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s)''',
                (session['user_id'], rating, content, food_rating, service_rating, environment_rating, datetime.now())
            )
            conn.commit()
            flash('评论发布成功', 'success')
        except mysql.connector.Error as err:
            print(f"发布评论失败: {err}")
            flash('发布评论失败，请稍后再试', 'error')
            conn.rollback()
        except Exception as e:
            print(f"发布评论异常: {e}")
            flash('发布评论失败，请稍后再试', 'error')
            conn.rollback()
        finally:
            cursor.close()
            conn.close()
        
    return redirect(url_for('my_reviews'))

# 用户AJAX预订桌位
@app.route('/api/reserve_table', methods=['POST'])
@login_required
def api_reserve_table():
    if request.method == 'POST':
        try:
            # 获取JSON数据
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': '无效的请求数据'})
                
            table_id = data.get('table_id')
            if not table_id:
                return jsonify({'success': False, 'message': '桌位ID不能为空'})
                
            reservation_time = data.get('reservation_time')
            if not reservation_time:
                return jsonify({'success': False, 'message': '预订时间不能为空'})
                
            try:
                duration = int(data.get('duration', 0))
                if duration <= 0:
                    return jsonify({'success': False, 'message': '用餐时长必须大于0'})
            except (ValueError, TypeError):
                return jsonify({'success': False, 'message': '无效的用餐时长'})
                
            try:
                people_count = int(data.get('people_count', 0))
                if people_count <= 0:
                    return jsonify({'success': False, 'message': '用餐人数必须大于0'})
            except (ValueError, TypeError):
                return jsonify({'success': False, 'message': '无效的用餐人数'})
                
            notes = data.get('notes', '')
            
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            # 获取桌位信息
            cursor.execute('SELECT * FROM tables WHERE table_id = %s', (table_id,))
            table = cursor.fetchone()
            
            if not table:
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': '桌位不存在'})
            
            if table['status'] != 'available':
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': '该桌位当前不可预订'})
            
            # 验证数据
            if people_count > table['seats']:
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': f'预订人数不能超过桌位容量（{table["seats"]}人）'})
            
            # 创建预订记录
            try:
                reservation_datetime = datetime.strptime(reservation_time, '%Y-%m-%dT%H:%M')
                cursor.execute(
                    '''INSERT INTO table_reservations 
                        (table_id, user_id, reservation_time, duration, status, notes, people_count) 
                       VALUES (%s, %s, %s, %s, %s, %s, %s)''',
                    (table_id, session['user_id'], reservation_datetime, duration, 'confirmed', notes, people_count)
                )
                
                # 更新桌位状态为已预订
                cursor.execute('UPDATE tables SET status = %s WHERE table_id = %s', ('reserved', table_id))
                
                conn.commit()
                
                # 获取刚插入的预订ID
                reservation_id = cursor.lastrowid
                
                # 获取预订信息以返回
                cursor.execute('SELECT r.*, t.table_name, t.seats FROM table_reservations r JOIN tables t ON r.table_id = t.table_id WHERE r.reservation_id = %s', (reservation_id,))
                reservation = cursor.fetchone()
                
                if not reservation:
                    cursor.close()
                    conn.close()
                    return jsonify({'success': True, 'message': '预订成功'})
                
                # 处理时间格式问题
                if isinstance(reservation['reservation_time'], datetime):
                    reservation['reservation_time'] = reservation['reservation_time'].strftime('%Y-%m-%d %H:%M')
                elif isinstance(reservation['reservation_time'], bytes):
                    try:
                        reservation['reservation_time'] = datetime.fromisoformat(reservation['reservation_time'].decode('utf-8')).strftime('%Y-%m-%d %H:%M')
                    except:
                        reservation['reservation_time'] = str(reservation['reservation_time'])
                
                cursor.close()
                conn.close()
                return jsonify({
                    'success': True, 
                    'message': '预订成功！',
                    'reservation': reservation
                })
            except ValueError as e:
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': f'日期格式错误: {e}'})
            except mysql.connector.Error as e:
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': f'预订失败: {e}'})
                
        except Exception as e:
            return jsonify({'success': False, 'message': f'系统错误: {e}'})
    
    return jsonify({'success': False, 'message': '不支持的请求方法'})

# 用户查询自己的预订API
@app.route('/api/my_reservations')
@login_required
def api_my_reservations():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # 获取用户所有预订
        cursor.execute('''
            SELECT r.*, t.table_name, t.seats
            FROM table_reservations r
            JOIN tables t ON r.table_id = t.table_id
            WHERE r.user_id = %s
            ORDER BY r.reservation_time DESC
        ''', (session['user_id'],))
        
        reservations = []
        for row in cursor.fetchall():
            # 处理时间格式
            if isinstance(row['reservation_time'], datetime):
                row['reservation_time'] = row['reservation_time'].strftime('%Y-%m-%d %H:%M')
            elif isinstance(row['reservation_time'], bytes):
                try:
                    row['reservation_time'] = datetime.fromisoformat(row['reservation_time'].decode('utf-8')).strftime('%Y-%m-%d %H:%M')
                except:
                    row['reservation_time'] = str(row['reservation_time'])
            
            # 转换status为中文
            status_map = {
                'pending': '待确认',
                'confirmed': '已确认',
                'cancelled': '已取消',
                'completed': '已完成'
            }
            row['status_display'] = status_map.get(row['status'], row['status'])
            
            reservations.append(row)
            
        return jsonify({'success': True, 'reservations': reservations})
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取预订信息失败: {e}'})
    finally:
        cursor.close()
        conn.close()

# 用户AJAX取消预订
@app.route('/api/cancel_reservation/<int:reservation_id>', methods=['POST'])
@login_required
def api_cancel_reservation(reservation_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # 验证预订属于当前用户
        cursor.execute(
            'SELECT * FROM table_reservations WHERE reservation_id = %s AND user_id = %s',
            (reservation_id, session['user_id'])
        )
        reservation = cursor.fetchone()
        
        if not reservation:
            return jsonify({'success': False, 'message': '预订不存在或您无权取消'})
        
        # 只有待确认或已确认的预订可以取消
        if reservation['status'] not in ['pending', 'confirmed']:
            return jsonify({'success': False, 'message': '该预订状态无法取消'})
        
        # 更新预订状态为已取消
        cursor.execute('UPDATE table_reservations SET status = %s WHERE reservation_id = %s', ('cancelled', reservation_id))
        conn.commit()
        
        # 如果预订已确认，则将桌位状态改回可用
        if reservation['status'] == 'confirmed':
            cursor.execute('UPDATE tables SET status = %s WHERE table_id = %s', ('available', reservation['table_id']))
            conn.commit()
        
        return jsonify({'success': True, 'message': '预订已成功取消'})
    except mysql.connector.Error as err:
        return jsonify({'success': False, 'message': f'取消失败: {err}'})
    finally:
        cursor.close()
        conn.close()

# 用于Jinja2模板的辅助函数，获取订单详情
def get_order_details(bulk_order_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # 查询订单项详情
        cursor.execute('''
            SELECT od.*, d.name as dish_name
            FROM order_details od
            JOIN dishes d ON od.dish_id = d.dish_id
            WHERE od.bulk_order_id = %s
        ''', (bulk_order_id,))
        
        details = cursor.fetchall()
        
        # 计算每个订单项的总额
        for item in details:
            item['amount'] = Decimal(item['price']) * item['quantity']
            
        return details
    except Exception as e:
        print(f"获取订单详情错误: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

# 注册辅助函数供Jinja2模板使用
app.jinja_env.globals.update(get_order_details=get_order_details)

# 管理员评论管理页面
@app.route('/admin/reviews')
@admin_required
def admin_reviews():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 获取页码参数，默认为1
    page = request.args.get('page', 1, type=int)
    per_page = 10  # 每页显示的评论数
    offset = (page - 1) * per_page
    
    # 获取总评论数
    cursor.execute('SELECT COUNT(*) as count FROM reviews')
    total_reviews = cursor.fetchone()['count']
    total_pages = (total_reviews + per_page - 1) // per_page
    
    # 获取所有评论，带上用户名
    cursor.execute('''
        SELECT r.*, u.username 
        FROM reviews r 
        JOIN users u ON r.user_id = u.user_id 
        ORDER BY r.review_time DESC
        LIMIT %s OFFSET %s
    ''', (per_page, offset))
    
    reviews = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('admin/reviews.html', reviews=reviews, current_page=page, total_pages=total_pages)

# 管理员删除评论
@app.route('/admin/reviews/<int:review_id>/delete', methods=['POST'])
@admin_required
def admin_delete_review(review_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # 删除评论
        cursor.execute('DELETE FROM reviews WHERE review_id = %s', (review_id,))
        conn.commit()
        flash('评论删除成功', 'success')
    except Exception as e:
        print(f"删除评论失败: {e}")
        flash('删除评论失败', 'error')
        conn.rollback()
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('admin_reviews'))

if __name__ == '__main__':
    # 数据库初始化已通过restaurant_db_complete.sql完成
    app.run(debug=True) 