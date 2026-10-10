-- Active: 1791554738496@@127.0.0.1@3306@lost_and_found
-- Active: 1791554738496@@127.0.0.1@3306@mysql
-- ============================================================
-- 基于原生HTTP的宿舍园区失物信息登记系统 - 数据库初始化脚本
-- 数据库: lost_and_found
-- ============================================================

DROP DATABASE IF EXISTS lost_and_found;
CREATE DATABASE lost_and_found DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE lost_and_found;

-- ------------------------------------------------------------
-- 1. 用户表
-- ------------------------------------------------------------
CREATE TABLE users (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    username      VARCHAR(50)  NOT NULL UNIQUE COMMENT '登录账号',
    password_hash VARCHAR(255) NOT NULL       COMMENT '密码哈希值',
    real_name     VARCHAR(50)                 COMMENT '真实姓名',
    role          ENUM('user','admin') NOT NULL DEFAULT 'user' COMMENT '角色:普通用户/管理员',
    phone         VARCHAR(20)                 COMMENT '联系电话',
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';

-- ------------------------------------------------------------
-- 2. 失物/寻物登记表 (失主发布:我丢了东西)
-- ------------------------------------------------------------
CREATE TABLE lost_items (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    user_id       INT NOT NULL                COMMENT '发布者用户ID',
    title         VARCHAR(100) NOT NULL       COMMENT '物品标题',
    description   TEXT                        COMMENT '物品描述/特征',
    category      VARCHAR(50) DEFAULT '其他'  COMMENT '分类:证件/电子设备/钥匙/衣物/书籍/其他',
    location_lost VARCHAR(100)                COMMENT '丢失地点',
    time_lost     DATETIME                    COMMENT '丢失时间',
    contact       VARCHAR(100)                COMMENT '联系方式',
    status        ENUM('pending','approved','rejected','claimed') NOT NULL DEFAULT 'pending'
                  COMMENT '状态:待审核/已通过/已驳回/已找回',
    image_url     VARCHAR(255) DEFAULT NULL  COMMENT '物品图片路径',
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='失物寻物登记表';

-- ------------------------------------------------------------
-- 3. 招领信息表 (拾到者发布:我捡到了东西)
-- ------------------------------------------------------------
CREATE TABLE found_items (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    user_id       INT NOT NULL                COMMENT '发布者用户ID',
    title         VARCHAR(100) NOT NULL       COMMENT '物品标题',
    description   TEXT                        COMMENT '物品描述/特征',
    category      VARCHAR(50) DEFAULT '其他'  COMMENT '分类',
    location_found VARCHAR(100)               COMMENT '捡拾地点',
    time_found    DATETIME                    COMMENT '捡拾时间',
    contact       VARCHAR(100)                COMMENT '联系方式',
    status        ENUM('pending','approved','rejected','claimed') NOT NULL DEFAULT 'pending'
                  COMMENT '状态:待审核/已通过/已驳回/已招领',
    image_url     VARCHAR(255) DEFAULT NULL  COMMENT '物品图片路径',
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='招领信息表';

-- ------------------------------------------------------------
-- 4. 认领记录表
-- ------------------------------------------------------------
CREATE TABLE claim_records (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    claimer_id    INT NOT NULL                COMMENT '认领申请人用户ID',
    item_type     ENUM('lost','found') NOT NULL COMMENT '认领对象类型',
    item_id       INT NOT NULL                COMMENT '被认领物品ID',
    claim_reason  TEXT NOT NULL               COMMENT '认领理由/物品特征说明',
    status        ENUM('pending','approved','rejected') NOT NULL DEFAULT 'pending'
                  COMMENT '审核状态:待审核/已通过/已驳回',
    admin_id      INT                         COMMENT '处理管理员ID',
    processed_at  DATETIME                    COMMENT '处理时间',
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (claimer_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (admin_id)   REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='认领记录表';

-- ------------------------------------------------------------
-- 初始化测试账号
-- 密码均为 123456 的 SHA-256 哈希
-- admin / admin123 (管理员)
-- user1 / 123456 (普通用户)
-- ------------------------------------------------------------
-- SHA-256('123456') = 8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92
-- SHA-256('admin123') = 240be518fabd2724ddb6f04e455150c9e79e167e1725f07c0817421140aa3e98
INSERT INTO users (username, password_hash, real_name, role, phone) VALUES
('admin', '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9', '系统管理员', 'admin', '13800000000'),
('user1', '8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92', '张同学',     'user',  '13800000001'),
('user2', '8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92', '李同学',     'user',  '13800000002');
