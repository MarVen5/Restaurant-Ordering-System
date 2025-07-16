-- 餐厅管理系统完整数据库脚本
-- 包含所有表创建、初始数据和更新操作

-- 创建数据库（如果需要）
CREATE DATABASE IF NOT EXISTS restaurant_db;
USE restaurant_db;

-- =====================================================
-- 表结构创建
-- =====================================================

-- 创建用户表
CREATE TABLE IF NOT EXISTS users (
  user_id INT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(50) NOT NULL UNIQUE,
  password VARCHAR(255) NOT NULL,
  phone VARCHAR(20),
  address VARCHAR(255),
  is_admin BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建菜品表
CREATE TABLE IF NOT EXISTS dishes (
    dish_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    category VARCHAR(50) NOT NULL DEFAULT '其他',
    price DECIMAL(10, 2) NOT NULL,
    description TEXT,
    image_url VARCHAR(255),
    sort_order INT DEFAULT 0
);

-- 创建订单表 (单个菜品订单，保留向后兼容)
CREATE TABLE IF NOT EXISTS orders (
    order_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    dish_name VARCHAR(100) NOT NULL,
    quantity INT NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    status VARCHAR(20) NOT NULL,
    order_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (dish_name) REFERENCES dishes(name)
);

-- 创建批量订单表（购物车结算）
CREATE TABLE IF NOT EXISTS bulk_orders (
    bulk_order_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    total_amount DECIMAL(10, 2) NOT NULL,
    address VARCHAR(255) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    payment_method VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    order_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    dining_type VARCHAR(20) NOT NULL DEFAULT 'dine-in',
    table_id INT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- 创建订单详情表
CREATE TABLE IF NOT EXISTS order_details (
    detail_id INT AUTO_INCREMENT PRIMARY KEY,
    bulk_order_id INT NOT NULL,
    dish_id INT NOT NULL,
    dish_name VARCHAR(100) NOT NULL,
    quantity INT NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    FOREIGN KEY (bulk_order_id) REFERENCES bulk_orders(bulk_order_id),
    FOREIGN KEY (dish_id) REFERENCES dishes(dish_id)
);

-- 创建餐桌表
CREATE TABLE IF NOT EXISTS tables (
    table_id INT AUTO_INCREMENT PRIMARY KEY,
    table_name VARCHAR(50) NOT NULL UNIQUE,
    seats INT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'available' -- available, occupied, reserved
);

-- 创建桌位预订表
CREATE TABLE IF NOT EXISTS table_reservations (
    reservation_id INT AUTO_INCREMENT PRIMARY KEY,
    table_id INT NOT NULL,
    user_id INT NOT NULL,
    reservation_time DATETIME NOT NULL,
    duration INT NOT NULL DEFAULT 120, -- 默认预定时长（分钟）
    status VARCHAR(20) NOT NULL DEFAULT 'pending', -- pending, confirmed, cancelled, completed
    notes TEXT,
    people_count INT NOT NULL DEFAULT 2,
    FOREIGN KEY (table_id) REFERENCES tables(table_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- 创建评论表
CREATE TABLE IF NOT EXISTS reviews (
    review_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    bulk_order_id INT NULL,
    rating INT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    food_rating INT DEFAULT 5,
    service_rating INT DEFAULT 5,
    environment_rating INT DEFAULT 5,
    content TEXT NOT NULL,
    review_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- =====================================================
-- 初始数据插入
-- =====================================================

-- 插入示例菜品数据
INSERT INTO dishes (name, price, description, image_url, category, sort_order) VALUES 
-- 主食类
('玛格丽特披萨', 68.00, '经典意式披萨，配以新鲜番茄酱、马苏里拉奶酪、罗勒叶和特级初榨橄榄油。', '/static/images/dish4.png', '主食', 1),
('意式肉酱面', 58.00, '意大利传统肉酱面，选用上等牛肉和猪肉混合慢炖，搭配新鲜番茄和香料，浇在手工制作的意面上。', '/static/images/dish1.png', '主食', 2),
('海鲜烩饭', 78.00, '西班牙风味海鲜烩饭，精选新鲜虾、贻贝、鱿鱼等海鲜，配以番红花米饭，口感鲜美。', '/static/images/dish3.png', '主食', 3),
('黑椒牛排', 128.00, '精选澳洲进口牛排，搭配黑椒汁，口感鲜嫩多汁，配以时令蔬菜和土豆泥。', '/static/images/dish5.png', '主食', 4),
('泰式炒河粉', 48.00, '泰国风味炒河粉，配以鲜虾、豆芽、葱花和花生碎，酸甜可口。', '/static/images/dish2.png', '主食', 5),

-- 小食类
('薯条', 28.00, '精选优质土豆，切条后油炸至金黄酥脆，搭配番茄酱和蒜香蛋黄酱。', '/static/images/dish10.png', '小食', 1),
('炸鸡翅', 42.00, '选用新鲜鸡翅，经过特制香料腌制，油炸至外酥里嫩，搭配特制酱料。', '/static/images/dish7.png', '小食', 2),
('芝士焗蘑菇', 38.00, '新鲜蘑菇填充香浓芝士，烤至金黄，外酥内软，奶香四溢。', '/static/images/dish8.png', '小食', 3),
('蒜香面包', 22.00, '法式面包涂抹大蒜黄油，烤至金黄，外酥内软，蒜香浓郁。', '/static/images/dish9.png', '小食', 4),
('洋葱圈', 26.00, '新鲜洋葱切片，裹以特制面糊，炸至金黄酥脆，搭配蒜香酱。', '/static/images/dish6.png', '小食', 5),

-- 饮品类
('鲜榨橙汁', 22.00, '使用新鲜橙子现场压榨，不添加任何糖分和防腐剂，保留水果的原始风味。', '/static/images/dish25.png', '饮品', 1),
('卡布奇诺', 25.00, '意式浓缩咖啡与蒸汽牛奶的完美结合，顶部撒有可可粉。', '/static/images/dish21.png', '饮品', 2),
('草莓奶昔', 28.00, '新鲜草莓与优质冰淇淋混合制成，口感丝滑，香甜可口。', '/static/images/dish24.png', '饮品', 3),
('柠檬冰茶', 18.00, '精选红茶搭配新鲜柠檬片和蜂蜜，冰镇后清爽解渴。', '/static/images/dish22.png', '饮品', 4),
('芒果冰沙', 26.00, '新鲜芒果打成冰沙，加入少量蜂蜜调味，口感顺滑，芒果香气浓郁。', '/static/images/dish23.png', '饮品', 5),

-- 沙拉类
('凯撒沙拉', 42.00, '新鲜罗马生菜，配以自制凯撒酱、帕玛森奶酪、香脆面包丁和烤鸡肉。', '/static/images/dish11.png', '沙拉', 1),
('希腊沙拉', 38.00, '新鲜番茄、黄瓜、红洋葱、橄榄和菲达奶酪，搭配特制橄榄油醋汁。', '/static/images/dish12.png', '沙拉', 2),
('水果沙拉', 36.00, '时令水果混合，搭配酸奶和蜂蜜，清新爽口。', '/static/images/dish13.png', '沙拉', 3),
('鲜虾牛油果沙拉', 58.00, '新鲜虾仁、牛油果、樱桃番茄和混合生菜，搭配柠檬汁和橄榄油。', '/static/images/dish15.png', '沙拉', 4),
('烟熏三文鱼沙拉', 62.00, '挪威烟熏三文鱼，搭配混合生菜、小番茄、红洋葱和酸豆，淋上特制酱汁。', '/static/images/dish14.png', '沙拉', 5),

-- 甜点类
('提拉米苏', 36.00, '经典意式甜点，由手指饼干浸泡咖啡酒，层叠马斯卡彭奶酪霜和可可粉制成。', '/static/images/dish17.png', '甜点', 1),
('芝士蛋糕', 32.00, '浓郁细腻的芝士蛋糕，底层为酥脆饼干，表面淋上新鲜水果酱。', '/static/images/dish20.png', '甜点', 2),
('巧克力熔岩蛋糕', 38.00, '外层松软，内含热熔巧克力，搭配香草冰淇淋，口感丰富。', '/static/images/dish16.png', '甜点', 3),
('焦糖布丁', 28.00, '细腻顺滑的焦糖布丁，表面覆盖一层香甜焦糖，入口即化。', '/static/images/dish19.png', '甜点', 4),
('水果塔', 34.00, '酥脆塔皮，填充香滑奶油，表面装饰时令水果，清新美味。', '/static/images/dish18.png', '甜点', 5);

-- 插入管理员用户，使用简单明文密码
INSERT INTO users (username, password, phone, is_admin) VALUES
('admin', '123456', '13800138000', TRUE);

-- 插入默认餐桌数据
INSERT INTO tables (table_name, seats, status) VALUES
('A-1', 2, 'available'),
('A-2', 2, 'available'),
('A-3', 2, 'available'),
('B-1', 4, 'available'),
('B-2', 4, 'available'),
('B-3', 4, 'available'),
('C-1', 6, 'available'),
('C-2', 6, 'available'),
('D-1', 8, 'available'),
('VIP-1', 10, 'available');
 