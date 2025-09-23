module main

import os
import json
import time

// 用户状态枚举
enum UserStatus {
    active
    inactive
    suspended
}

// 用户接口
interface UserInterface {
    get_name() string
    is_active() bool
}

// 用户结构体
struct User {
    id       int
    name     string
    email    string
    age      int
    status   UserStatus
mut:
    last_login time.Time
}

// 用户管理器结构体
struct UserManager {
mut:
    users []User
    cache map[int]User
}

// 自定义类型
type UserId = int
type UserList = []User

// 创建新用户
fn create_user(name string, email string, age int) User {
    return User{
        id: generate_id(),
        name: name,
        email: email,
        age: age,
        status: .active,
        last_login: time.now()
    }
}

// 生成ID
fn generate_id() int {
    return int(time.now().unix())
}

// 用户方法 - 获取用户名
fn (u User) get_name() string {
    return u.name
}

// 用户方法 - 检查是否激活
fn (u User) is_active() bool {
    return u.status == .active
}

// 用户管理器方法 - 添加用户
fn (mut um UserManager) add_user(user User) {
    um.users << user
    um.cache[user.id] = user
}

// 用户管理器方法 - 获取用户
fn (um UserManager) get_user(id int) ?User {
    if user := um.cache[id] {
        return user
    }
    return error('User not found')
}

// 用户管理器方法 - 列出所有用户
fn (um UserManager) list_users() []User {
    return um.users
}

// 验证用户数据
fn validate_user(user User) !bool {
    if user.name.len == 0 {
        return error('Name cannot be empty')
    }
    if user.age < 0 {
        return error('Age cannot be negative')
    }
    return true
}

// 主函数
fn main() {
    println('V语言用户管理系统')

    mut manager := UserManager{
        users: []User{}
        cache: map[int]User{}
    }

    // 创建测试用户
    user1 := create_user('张三', 'zhangsan@example.com', 25)
    user2 := create_user('李四', 'lisi@example.com', 30)

    // 添加用户
    manager.add_user(user1)
    manager.add_user(user2)

    // 列出所有用户
    users := manager.list_users()
    println('用户列表:')
    for user in users {
        println('  ${user.name} (${user.email})')
    }
}