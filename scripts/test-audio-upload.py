#!/usr/bin/env python3
"""
音频上传测试脚本

功能：
1. 登录获取 JWT Token
2. 注册测试设备 (如果不存在)
3. 上传音频文件进行测试

用法：
    python scripts/test-audio-upload.py --audio /path/to/your/audio.wav

环境变量 (可选)：
    SERVER_URL  后端服务地址 (默认 http://localhost:8000)
"""

import argparse
import json
import os
import sys
from pathlib import Path

import requests


def get_server_url():
    """获取服务器地址"""
    return os.getenv("SERVER_URL", "http://localhost:8000")


def login(server_url: str, username: str = "admin", password: str = "admin123") -> str:
    """登录获取 JWT Token"""
    print(f"[*] 正在登录: {username}")

    response = requests.post(
        f"{server_url}/api/auth/login",
        json={"username": username, "password": password},
        timeout=10,
    )

    if response.status_code != 200:
        print(f"[!] 登录失败: {response.status_code}")
        print(f"    响应: {response.text}")
        sys.exit(1)

    token = response.json()["access_token"]
    print(f"[+] 登录成功，Token: {token[:20]}...")
    return token


def register_device(server_url: str, token: str, device_code: str, device_name: str = 'unknow') -> dict:
    """注册测试设备"""
    print(f"[*] 正在注册设备: {device_code}")

    headers = {"Authorization": f"Bearer {token}"}
    data = {
        "device_code": device_code,
        "name": device_name or f"测试设备 {device_code}",
        "location": "测试环境",
        "firmware_version": "test-1.0.0",
    }

    response = requests.post(
        f"{server_url}/api/device/register",
        json=data,
        headers=headers,
        timeout=10,
    )

    if response.status_code == 200:
        device = response.json()
        print(f"[+] 设备注册成功: ID={device['id']}, Code={device['device_code']}")
        return device
    elif response.status_code == 400 and "already registered" in response.text:
        print(f"[!] 设备已存在，跳过注册")
        # 获取设备信息
        response = requests.get(
            f"{server_url}/api/device/list",
            headers=headers,
            timeout=10,
        )
        if response.status_code == 200:
            devices = response.json()
            for d in devices:
                if d["device_code"] == device_code:
                    return d
        return {"device_code": device_code}
    else:
        print(f"[!] 设备注册失败: {response.status_code}")
        print(f"    响应: {response.text}")
        sys.exit(1)


def upload_audio(server_url: str, device_code: str, audio_path: str) -> dict:
    """上传音频文件"""
    print(f"[*] 正在上传音频: {audio_path}")

    if not Path(audio_path).exists():
        print(f"[!] 文件不存在: {audio_path}")
        sys.exit(1)

    file_size = Path(audio_path).stat().st_size
    print(f"    文件大小: {file_size / 1024:.2f} KB")

    with open(audio_path, "rb") as f:
        files = {"file": (Path(audio_path).name, f, "audio/wav")}
        response = requests.post(
            f"{server_url}/api/audio/upload",
            params={"device_code": device_code},
            files=files,
            timeout=60,
        )

    if response.status_code != 200:
        print(f"[!] 上传失败: {response.status_code}")
        print(f"    响应: {response.text}")
        sys.exit(1)

    result = response.json()
    print(f"[+] 上传成功!")
    print(f"    音频 ID: {result['id']}")
    print(f"    文件路径: {result['file_path']}")
    print(f"    状态: {result['status']}")
    return result


def check_inference_status(server_url: str, token: str, audio_id: int, max_retries: int = 30):
    """检查推理状态"""
    print(f"[*] 等待推理完成 (音频 ID: {audio_id})...")

    headers = {"Authorization": f"Bearer {token}"}

    import time
    for i in range(max_retries):
        response = requests.get(
            f"{server_url}/api/audio/{audio_id}",
            headers=headers,
            timeout=10,
        )

        if response.status_code == 200:
            audio = response.json()
            status = audio.get("inference_status", "unknown")
            print(f"    [{i+1}/{max_retries}] 推理状态: {status}")

            if status == "completed":
                print(f"[+] 推理完成!")
                # 获取转写结果
                get_transcript(server_url, token, audio_id)
                return True
            elif status == "failed":
                print(f"[!] 推理失败")
                return False

        time.sleep(2)

    print(f"[!] 推理超时，请稍后手动查询")
    return False


def get_transcript(server_url: str, token: str, audio_id: int):
    """获取转写结果"""
    print(f"[*] 获取转写结果...")

    headers = {"Authorization": f"Bearer {token}"}

    response = requests.get(
        f"{server_url}/api/result/transcript/{audio_id}",
        headers=headers,
        timeout=10,
    )

    if response.status_code == 200:
        result = response.json()
        print(f"[+] 转写结果:")
        print(f"    文本: {result.get('text', 'N/A')}")
        print(f"    语言: {result.get('language', 'N/A')}")
        print(f"    置信度: {result.get('confidence', 'N/A')}")
    else:
        print(f"[!] 获取转写结果失败: {response.status_code}")


def main():
    parser = argparse.ArgumentParser(description="音频上传测试脚本")
    parser.add_argument(
        "--audio",
        required=True,
        help="音频文件路径 (支持 wav, mp3, opus 等格式)"
    )
    parser.add_argument(
        "--device",
        default="TEST_DEVICE_001",
        help="测试设备编码 (默认: TEST_DEVICE_001)"
    )
    parser.add_argument(
        "--device-name",
        default=None,
        help="设备名称 (默认: 测试设备 + 编码)"
    )
    parser.add_argument(
        "--server",
        default=None,
        help="服务器地址 (默认: http://localhost:8000)"
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="等待推理完成并显示结果"
    )
    parser.add_argument(
        "--username",
        default="admin",
        help="登录用户名 (默认: admin)"
    )
    parser.add_argument(
        "--password",
        default="admin123",
        help="登录密码 (默认: admin123)"
    )

    args = parser.parse_args()

    # 获取服务器地址
    server_url = args.server or get_server_url()
    print(f"[*] 服务器地址: {server_url}")

    # 1. 登录
    token = login(server_url, args.username, args.password)

    # 2. 注册设备
    device = register_device(server_url, token, args.device, args.device_name)

    # 3. 上传音频
    result = upload_audio(server_url, args.device, args.audio)

    # 4. 等待推理 (可选)
    if args.wait:
        check_inference_status(server_url, token, result["id"])

    print(f"\n[✓] 测试完成!")
    print(f"    后续可访问前端页面查看结果: {server_url}")


if __name__ == "__main__":
    main()
