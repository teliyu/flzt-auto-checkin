import os
import requests
import json
from dotenv import load_dotenv

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 Edg/128.0.0.0'
}

def load_env():
    """加载环境变量"""
    load_dotenv()
    return {
        'BASE_URL': os.getenv('BASE_URL'),
        'EMAIL': os.getenv('EMAIL'),
        'PASSWORD': os.getenv('PASSWORD'),
        'TELEGRAM_BOT_TOKEN': os.getenv('TELEGRAM_BOT_TOKEN'),
        'TELEGRAM_CHAT_ID': os.getenv('TELEGRAM_CHAT_ID')
    }

def send_telegram_message(bot_token, chat_id, message):
    """发送Telegram通知"""
    if not bot_token or not chat_id:
        print("缺少Telegram配置，跳过通知")
        return
    
    api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    try:
        response = requests.post(api_url, json=payload, timeout=10)
        if response.status_code == 200:
            print("Telegram通知发送成功")
        else:
            print(f"Telegram通知发送失败: {response.text}")
    except Exception as e:
        print(f"发送Telegram通知时出错: {str(e)}")

def login(url, email, password):
    """登录获取token"""
    data = {'email': email, 'passwd': password}
    try:
        response = requests.post(url=url, data=data, headers=headers, timeout=10)
        if response.status_code != 200:
            return None
        data = response.json()
        return data.get('token')
    except Exception as e:
        print(f'登录失败: {str(e)}')
        return None

def checkin(url, token):
    """执行签到"""
    headers['Access-Token'] = token
    try:
        response = requests.get(url=url, headers=headers, timeout=10)
        data = response.json()
        return data.get('result', '签到结果未知')
    except Exception as e:
        print(f'签到失败: {str(e)}')
        return f'签到失败: {str(e)}'
        
def get_user_info(url, token):
    """获取用户信息"""
    headers['Access-Token'] = token
    try:
        response = requests.get(url=url, headers=headers, timeout=10)
        data = response.json()
        # 获取用户流量（未使用流量）
        unused_traffic = data.get('result', {}).get('unusedTraffic', '未知流量')
        print(f"未使用流量: {unused_traffic}")  # 打印未使用流量，方便调试
        return data.get('result', {}).get('data', {}), unused_traffic  # 返回流量信息
    except Exception as e:
        print(f'获取用户信息失败: {str(e)}')
        return None, None



def convert_traffic(url, token, traffic):
    """转换流量"""
    headers['Access-Token'] = token
    params = {'traffic': str(traffic)}
    try:
        response = requests.get(url=url, headers=headers, params=params, timeout=10)
        data = response.json()
        return data.get('msg', '流量转换结果未知')
    except Exception as e:
        print(f'流量转换失败: {str(e)}')
        return f'流量转换失败: {str(e)}'

def format_message(email, checkin_msg, traffic, convert_msg, unused_traffic):
    """格式化Telegram消息"""
    return (
        f"**签到任务完成报告**\n\n"
        f"🔑 账户: `{email}`\n"
        f"✅ 签到结果: `{checkin_msg}`\n"
        f"📊 获得流量: `{traffic} MB`\n"
        f"🔄 转换结果: `{convert_msg}`\n"
        f"💾 用户未使用流量: `{unused_traffic}`\n\n" 
    )



def main():
    """主函数"""
    # 初始化消息内容
    result = "成功"
    checkin_msg = ""
    traffic = 0
    convert_msg = "无转换操作"
    unused_traffic = "未知流量"  # 默认值为未知流量
    
    try:
        # 加载配置
        env = load_env()
        if not all([env['BASE_URL'], env['EMAIL'], env['PASSWORD']]):
            error_msg = "❌ 环境变量配置不完整，请检查BASE_URL、EMAIL和PASSWORD"
            print(error_msg)
            send_telegram_message(env.get('TELEGRAM_BOT_TOKEN'), env.get('TELEGRAM_CHAT_ID'), error_msg)
            return
        
        # 构造API地址
        base_url = env['BASE_URL']
        login_url = f"{base_url}/api/token"
        checkin_url = f"{base_url}/api/user/checkin"
        user_info_url = f"{base_url}/api/user/info"
        convert_traffic_url = f"{base_url}/api/user/koukanntraffic"
        
        # 登录
        token = login(login_url, env['EMAIL'], env['PASSWORD'])
        if token is None:
            error_msg = f"❌ 登录失败 - 账户: {env['EMAIL']}"
            print(error_msg)
            send_telegram_message(env.get('TELEGRAM_BOT_TOKEN'), env.get('TELEGRAM_CHAT_ID'), error_msg)
            return
        
        # 签到
        checkin_msg = checkin(checkin_url, token)
        print(f'签到结果: {checkin_msg}')
        
        # 获取用户信息和未使用流量
        data, unused_traffic = get_user_info(user_info_url, token)
        if not data:
            result = "部分失败"
            error_msg = f"⚠️ 获取用户信息失败 - 账户: {env['EMAIL']}"
            print(error_msg)
            send_telegram_message(env.get('TELEGRAM_BOT_TOKEN'), env.get('TELEGRAM_CHAT_ID'), error_msg)
            return
        
        # 计算流量
        transfer_checkin = data.get('transfer_checkin', 0)
        if transfer_checkin:
            traffic = int(transfer_checkin) / (1024 * 1024)  # 字节转MB
            traffic = round(traffic, 2)
        print(f'签到获得的剩余流量: {traffic} MB')
        
        # 流量转换
        if traffic > 0:
            convert_msg = convert_traffic(convert_traffic_url, token, int(traffic))
            print(f'流量转换结果: {convert_msg}')
        else:
            convert_msg = "没有需要转换的流量"
            print(convert_msg)
        
    except Exception as e:
        result = "失败"
        error_msg = f"❌ 程序执行异常: {str(e)}"
        print(error_msg)
        send_telegram_message(env.get('TELEGRAM_BOT_TOKEN'), env.get('TELEGRAM_CHAT_ID'), error_msg)
    
    finally:
        # 发送汇总通知
        if 'env' in locals() and 'EMAIL' in env:
            message = format_message(
                env['EMAIL'], 
                checkin_msg, 
                traffic, 
                convert_msg,
                unused_traffic
            )
            send_telegram_message(env.get('TELEGRAM_BOT_TOKEN'), env.get('TELEGRAM_CHAT_ID'), message)

if __name__ == '__main__':
    main()
