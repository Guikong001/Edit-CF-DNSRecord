import requests
import tldextract
import time
import threading

# Cloudflare API基础URL
API_BASE_URL = "https://api.cloudflare.com/client/v4"

def get_headers():
    # 从用户获取API令牌（为了安全，建议使用环境变量或配置文件）
    api_token = input("\n(获取密钥请访问: https://dash.cloudflare.com/profile/api-tokens ，创建令牌 -> 编辑区域 DNS)\n\n请输入您的Cloudflare API令牌: ")
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    return headers

def get_base_domain(domain):
    # 使用tldextract提取根域名
    ext = tldextract.extract(domain)
    base_domain = ext.registered_domain
    return base_domain

def get_zone_id(base_domain, headers):
    # 获取区域ID
    params = {"name": base_domain}
    response = requests.get(f"{API_BASE_URL}/zones", headers=headers, params=params)
    data = response.json()
    if data["success"] and data["result"]:
        return data["result"][0]["id"]
    else:
        print("无法获取区域ID，请检查域名是否正确。")
        return None

def get_dns_record_id(zone_id, record_name, headers):
    # 获取DNS记录ID
    params = {"name": record_name}
    response = requests.get(f"{API_BASE_URL}/zones/{zone_id}/dns_records", headers=headers, params=params)
    data = response.json()
    if data["success"]:
        for record in data["result"]:
            if record["name"] == record_name:
                return record["id"]
    print("未找到指定的DNS记录。")
    return None

def delete_dns_record(zone_id, record_id, headers):
    # 删除DNS记录
    response = requests.delete(f"{API_BASE_URL}/zones/{zone_id}/dns_records/{record_id}", headers=headers)
    data = response.json()
    if data["success"]:
        print("DNS记录已成功删除。")
    else:
        print("删除DNS记录失败。", data["errors"])

def add_dns_record(zone_id, record_name, ip, proxied, headers):
    # 添加DNS记录
    payload = {
        "type": "A",
        "name": record_name,
        "content": ip,
        "ttl": 120,
        "proxied": proxied
    }
    response = requests.post(f"{API_BASE_URL}/zones/{zone_id}/dns_records", headers=headers, json=payload)
    data = response.json()
    if data["success"]:
        print("DNS记录已成功添加。")
    else:
        print("添加DNS记录失败。", data["errors"])

def update_dns_record(zone_id, record_id, record_name, ip, proxied, headers):
    # 更新DNS记录
    payload = {
        "type": "A",
        "name": record_name,
        "content": ip,
        "ttl": 120,
        "proxied": proxied
    }
    response = requests.put(f"{API_BASE_URL}/zones/{zone_id}/dns_records/{record_id}", headers=headers, json=payload)
    data = response.json()
    if data["success"]:
        print("DNS记录已成功更新。")
    else:
        print("更新DNS记录失败。", data["errors"])

def get_public_ip():
    # 获取本机公网IP地址
    try:
        response = requests.get('http://ip.ustc.edu.cn/myip.php')
        data = response.json()
        ip = data.get("myip")
        if ip:
            return ip
        else:
            print("无法从响应中获取IP地址。")
            return None
    except Exception as e:
        print("获取公网IP地址失败。", e)
        return None

def ddns_update(zone_id, record_name, proxied, headers):
    # DDNS更新函数
    current_ip = get_public_ip()
    if current_ip is None:
        return

    # 检查DNS记录是否存在
    record_id = get_dns_record_id(zone_id, record_name, headers)
    if record_id:
        # 更新DNS记录
        update_dns_record(zone_id, record_id, record_name, current_ip, proxied, headers)
    else:
        # 添加DNS记录
        add_dns_record(zone_id, record_name, current_ip, proxied, headers)

    # 开始监测IP变化
    while True:
        time.sleep(120)  # 等待2分钟
        new_ip = get_public_ip()
        if new_ip is None:
            continue
        if new_ip != current_ip:
            print(f"检测到IP变化，旧IP：{current_ip}，新IP：{new_ip}")
            # 更新DNS记录
            record_id = get_dns_record_id(zone_id, record_name, headers)
            if record_id:
                update_dns_record(zone_id, record_id, record_name, new_ip, proxied, headers)
                current_ip = new_ip
            else:
                print("无法找到DNS记录，尝试重新添加。")
                add_dns_record(zone_id, record_name, new_ip, proxied, headers)
                current_ip = new_ip
        else:
            print("IP地址未发生变化。")

def main():
    headers = get_headers()
    action = input("\n请选择操作类型：\n1. 删除DNS\n2. 增加DNS\n3. 修改DNS记录\n4. 新增DDNS域名\n请输入数字选项：")

    if action in ['1', '2', '3', '4']:
        record_name = input("\n请输入完整的域名（例如：sub.example.com）：")
        base_domain = get_base_domain(record_name)
        zone_id = get_zone_id(base_domain, headers)
        if not zone_id:
            return

        if action == '1':
            record_id = get_dns_record_id(zone_id, record_name, headers)
            if record_id:
                delete_dns_record(zone_id, record_id, headers)
        elif action == '2':
            ip = input("\n请输入IP地址：")
            proxied_input = input("\n是否启用Cloudflare代理（y/n）：").lower()
            proxied = True if proxied_input == 'y' else False
            add_dns_record(zone_id, record_name, ip, proxied, headers)
        elif action == '3':
            record_id = get_dns_record_id(zone_id, record_name, headers)
            if record_id:
                ip = input("\n请输入新的IP地址：")
                proxied_input = input("\n是否启用Cloudflare代理（y/n）：").lower()
                proxied = True if proxied_input == 'y' else False
                update_dns_record(zone_id, record_id, record_name, ip, proxied, headers)
            else:
                print("无法找到需要修改的DNS记录。")
        elif action == '4':
            # 新增DDNS域名功能
            proxied_input = input("\n是否启用Cloudflare代理（y/n）：").lower()
            proxied = True if proxied_input == 'y' else False

            # 使用线程运行DDNS更新，以防止阻塞主线程
            ddns_thread = threading.Thread(target=ddns_update, args=(zone_id, record_name, proxied, headers))
            ddns_thread.daemon = True
            ddns_thread.start()

            print("DDNS服务已启动，按Ctrl+C停止。")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("DDNS服务已停止。")
    else:
        print("无效的选项，请输入1、2、3或4。")

if __name__ == "__main__":
    main()
