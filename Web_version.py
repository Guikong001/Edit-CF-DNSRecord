from flask import Flask, render_template_string, request, session
import requests
import tldextract
from datetime import timedelta

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # 请确保在生产环境中使用安全的随机密钥
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)  # 会话过期时间

# Cloudflare API基础URL
API_BASE_URL = "https://api.cloudflare.com/client/v4"

# 更新后的HTML模板，包含“是否保存API密钥”的选项
HTML_TEMPLATE = '''
<!doctype html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <title>Cloudflare DNS管理</title>
    <!-- 引入Bootstrap CSS -->
    <link rel="stylesheet" href="https://cdn.bootcdn.net/ajax/libs/twitter-bootstrap/4.6.2/css/bootstrap.min.css">
</head>
<body>
<div class="container">
    <h1 class="mt-5">Cloudflare DNS管理</h1>
    <form method="post" action="/" class="mt-4">
        {% if api_token_exists %}
        <div class="alert alert-success" role="alert">
            已检测到存储的API密钥，将使用该密钥进行操作。
        </div>
        {% else %}
        <div class="form-group">
            <label for="api_token">API密钥（Token）：</label>
            <input type="password" class="form-control" id="api_token" name="api_token" required>
        </div>
        <div class="form-group form-check">
            <input type="checkbox" class="form-check-input" id="remember_token" name="remember_token" value="yes">
            <label class="form-check-label" for="remember_token">是否保存API密钥？</label>
        </div>
        {% endif %}
        <div class="form-group">
            <label for="action">选择操作：</label>
            <select class="form-control" id="action" name="action">
                <option value="add">增加DNS记录</option>
                <option value="update">修改DNS记录</option>
                <option value="delete">删除DNS记录</option>
            </select>
        </div>
        <div class="form-group">
            <label for="domain">域名（例如：sub.example.com）：</label>
            <input type="text" class="form-control" id="domain" name="domain" required>
        </div>
        <div class="form-group">
            <label for="ip">IP地址（删除操作可留空）：</label>
            <input type="text" class="form-control" id="ip" name="ip">
        </div>
        <div class="form-group">
            <label for="proxied">是否启用Cloudflare代理：</label>
            <select class="form-control" id="proxied" name="proxied">
                <option value="true">是</option>
                <option value="false">否</option>
            </select>
        </div>
        <button type="submit" class="btn btn-primary">提交</button>
        {% if api_token_exists %}
        <a href="/logout" class="btn btn-secondary ml-2">清除已保存的API密钥</a>
        {% endif %}
    </form>
    {% if message %}
    <div class="alert alert-info mt-4" role="alert">
        {{ message }}
    </div>
    {% endif %}
    <div>
    <p>获取CloudFlare DNS编辑密钥请访问<a href="https://dash.cloudflare.com/profile/api-tokens" target="_blank">创建令牌 -> 编辑区域 DNS (使用模板)</a></p>
    <p>本站不会以任何形式泄漏或传播用户保存的密钥信息。但为安全起见，我们不建议在任何非个人私密位置保存重要的密钥！</p>
    </div>
</div>
<!-- 引入Bootstrap JS和依赖 -->
<script src="https://cdn.bootcdn.net/ajax/libs/jquery/3.6.4/jquery.min.js"></script>
<script src="https://cdn.bootcdn.net/ajax/libs/popper.js/1.16.1/umd/popper.min.js"></script>
<script src="https://cdn.bootcdn.net/ajax/libs/twitter-bootstrap/4.6.2/js/bootstrap.min.js"></script>
</body>
</html>
'''

def get_headers(api_token):
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    return headers

def get_base_domain(domain):
    ext = tldextract.extract(domain)
    base_domain = ext.registered_domain
    return base_domain

def get_zone_id(base_domain, headers):
    params = {"name": base_domain}
    response = requests.get(f"{API_BASE_URL}/zones", headers=headers, params=params)
    data = response.json()
    if data["success"] and data["result"]:
        return data["result"][0]["id"]
    else:
        return None

def get_dns_record_id(zone_id, record_name, headers):
    params = {"name": record_name}
    response = requests.get(f"{API_BASE_URL}/zones/{zone_id}/dns_records", headers=headers, params=params)
    data = response.json()
    if data["success"] and data["result"]:
        return data["result"][0]["id"]
    return None

def delete_dns_record(zone_id, record_id, headers):
    response = requests.delete(f"{API_BASE_URL}/zones/{zone_id}/dns_records/{record_id}", headers=headers)
    data = response.json()
    return data["success"], data.get("errors")

def add_dns_record(zone_id, record_name, ip, proxied, headers):
    payload = {
        "type": "A",
        "name": record_name,
        "content": ip,
        "ttl": 120,
        "proxied": proxied
    }
    response = requests.post(f"{API_BASE_URL}/zones/{zone_id}/dns_records", headers=headers, json=payload)
    data = response.json()
    return data["success"], data.get("errors")

def update_dns_record(zone_id, record_id, record_name, ip, proxied, headers):
    payload = {
        "type": "A",
        "name": record_name,
        "content": ip,
        "ttl": 120,
        "proxied": proxied
    }
    response = requests.put(f"{API_BASE_URL}/zones/{zone_id}/dns_records/{record_id}", headers=headers, json=payload)
    data = response.json()
    return data["success"], data.get("errors")

@app.route('/', methods=['GET', 'POST'])
def dns_manager():
    message = None
    api_token_exists = 'api_token' in session
    if request.method == 'POST':
        # 获取API密钥
        if api_token_exists:
            api_token = session['api_token']
        else:
            api_token = request.form.get('api_token')
            remember_token = request.form.get('remember_token')
            if remember_token == 'yes':
                session['api_token'] = api_token  # 将API密钥存储在会话中

        action = request.form.get('action')
        record_name = request.form.get('domain')
        ip = request.form.get('ip')
        proxied = request.form.get('proxied') == 'true'

        headers = get_headers(api_token)
        base_domain = get_base_domain(record_name)
        zone_id = get_zone_id(base_domain, headers)
        if not zone_id:
            message = "无法获取区域ID，请检查域名和API密钥是否正确。"
            return render_template_string(HTML_TEMPLATE, message=message, api_token_exists=api_token_exists)

        # 日志记录操作类型和域名
        print(f"用户操作：{action}, 域名：{record_name}")

        if action == 'delete':
            record_id = get_dns_record_id(zone_id, record_name, headers)
            if record_id:
                success, errors = delete_dns_record(zone_id, record_id, headers)
                if success:
                    message = "DNS记录已成功删除。"
                else:
                    message = f"删除DNS记录失败：{errors}"
            else:
                message = "未找到指定的DNS记录。"
        elif action == 'add':
            if not ip:
                message = "IP地址不能为空。"
                return render_template_string(HTML_TEMPLATE, message=message, api_token_exists=api_token_exists)
            success, errors = add_dns_record(zone_id, record_name, ip, proxied, headers)
            if success:
                message = "DNS记录已成功添加。"
            else:
                message = f"添加DNS记录失败：{errors}"
        elif action == 'update':
            if not ip:
                message = "IP地址不能为空。"
                return render_template_string(HTML_TEMPLATE, message=message, api_token_exists=api_token_exists)
            record_id = get_dns_record_id(zone_id, record_name, headers)
            if record_id:
                success, errors = update_dns_record(zone_id, record_id, record_name, ip, proxied, headers)
                if success:
                    message = "DNS记录已成功更新。"
                else:
                    message = f"更新DNS记录失败：{errors}"
            else:
                message = "未找到指定的DNS记录。"
    return render_template_string(HTML_TEMPLATE, message=message, api_token_exists='api_token' in session)

@app.route('/logout')
def logout():
    session.pop('api_token', None)
    message = "已清除保存的API密钥。"
    return render_template_string(HTML_TEMPLATE, message=message, api_token_exists=False)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10081)
