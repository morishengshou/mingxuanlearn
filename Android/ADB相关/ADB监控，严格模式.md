*Thinking...*

> 用户想要添加一个新功能：
> 1. 监控每个端口的ADB server
> 2. 如果发现连接了不在配置文件中的设备（且是IP地址连接的），就断开这些设备
> 3. 确保每个ADB server只连接配置文件中指定的设备
> 
> 这需要：
> 1. 定期检查每个端口上的所有连接设备
> 2. 比对实际连接的设备和配置中的设备
> 3. 断开未授权的设备（仅限IP地址连接的）
> 4. 可能需要区分USB连接和网络连接的设备
> 
> 我需要在现有代码基础上添加这个功能。

我来帮你添加这个设备白名单功能，确保每个ADB server只连接配置中指定的设备。

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import subprocess
import time
import threading
import logging
from datetime import datetime
import os
import sys
import signal
import argparse
from typing import Dict, List, Tuple, Set
import queue
import re

# 配置日志
class ColoredFormatter(logging.Formatter):
    """带颜色的日志格式化器"""
    
    COLORS = {
        'DEBUG': '\033[36m',    # 青色
        'INFO': '\033[32m',     # 绿色
        'WARNING': '\033[33m',  # 黄色
        'ERROR': '\033[31m',    # 红色
        'CRITICAL': '\033[35m', # 紫色
    }
    RESET = '\033[0m'
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)


class ADBMonitorMultiDevice:
    def __init__(self, config_file='adb_config.json', log_level='INFO'):
        self.config_file = config_file
        self.config = {}
        self.monitor_threads = []
        self.running = threading.Event()
        self.running.set()
        self.device_status = {}  # 存储设备状态
        self.status_lock = threading.Lock()
        self.command_queue = queue.Queue()  # 用于接收控制命令
        self.authorized_devices = {}  # 存储每个端口的授权设备列表
        self.setup_logging(log_level)
        self.load_config()
        
    def setup_logging(self, log_level):
        """设置日志系统"""
        # 创建logs目录
        if not os.path.exists('logs'):
            os.makedirs('logs')
            
        # 日志文件名包含日期
        log_file = f"logs/adb_monitor_{datetime.now().strftime('%Y%m%d')}.log"
        
        # 文件处理器
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        
        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(ColoredFormatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        
        # 配置logger
        self.logger = logging.getLogger('ADB_Monitor')
        self.logger.setLevel(getattr(logging, log_level.upper()))
        self.logger.handlers.clear()
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
    def load_config(self):
        """加载配置文件"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            self.logger.info(f"成功加载配置文件: {self.config_file}")
            self.validate_and_migrate_config()
            self.build_authorized_devices_map()
        except FileNotFoundError:
            self.logger.error(f"配置文件 {self.config_file} 不存在")
            self.create_sample_config()
            sys.exit(1)
        except json.JSONDecodeError as e:
            self.logger.error(f"配置文件格式错误: {e}")
            sys.exit(1)
            
    def build_authorized_devices_map(self):
        """构建每个端口的授权设备映射"""
        self.authorized_devices.clear()
        for server in self.config.get('servers', []):
            port = server['port']
            devices = set()
            for device_config in server.get('devices', []):
                devices.add(device_config['address'])
            self.authorized_devices[port] = devices
            self.logger.debug(f"端口 {port} 授权设备: {devices}")
            
    def validate_and_migrate_config(self):
        """验证并迁移配置文件格式"""
        # 检查是否需要迁移旧格式
        needs_migration = False
        for server in self.config.get('servers', []):
            if 'device' in server and not isinstance(server.get('devices'), list):
                needs_migration = True
                break
                
        if needs_migration:
            self.logger.info("检测到旧版配置格式，正在迁移...")
            self.migrate_config()
            
        # 验证配置
        required_fields = ['servers']
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"配置文件缺少必需字段: {field}")
                
        for server in self.config['servers']:
            if 'port' not in server:
                raise ValueError("每个server配置必须包含port字段")
            if 'devices' not in server or not isinstance(server['devices'], list):
                raise ValueError("每个server配置必须包含devices列表")
                
    def migrate_config(self):
        """迁移旧版配置到新格式"""
        for server in self.config.get('servers', []):
            if 'device' in server and not isinstance(server.get('devices'), list):
                # 将单个device转换为devices列表
                device_config = {
                    'address': server['device'],
                    'name': server.get('name', server['device'])
                }
                server['devices'] = [device_config]
                # 删除旧字段
                server.pop('device', None)
                server.pop('name', None)
                
        # 保存迁移后的配置
        backup_file = f"{self.config_file}.backup_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        os.rename(self.config_file, backup_file)
        self.logger.info(f"旧配置已备份至: {backup_file}")
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
        self.logger.info("配置文件已迁移到新格式")
        
    def create_sample_config(self):
        """创建示例配置文件"""
        sample_config = {
            "servers": [
                {
                    "port": 5037,
                    "devices": [
                        {
                            "address": "192.168.1.100:5555",
                            "name": "测试设备1-1"
                        },
                        {
                            "address": "192.168.1.101:5555",
                            "name": "测试设备1-2"
                        }
                    ],
                    "retry_interval": 10,
                    "max_retries": 5,
                    "strict_mode": true
                },
                {
                    "port": 5038,
                    "devices": [
                        {
                            "address": "192.168.1.102:5555",
                            "name": "测试设备2-1"
                        }
                    ],
                    "retry_interval": 15,
                    "max_retries": 5,
                    "strict_mode": true
                }
            ],
            "check_interval": 5,
            "unauthorized_check_interval": 10,
            "status_report_interval": 300,
            "notification": {
                "enabled": false,
                "webhook": "https://your-webhook-url"
            }
        }
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(sample_config, f, indent=2, ensure_ascii=False)
        self.logger.info(f"已创建示例配置文件: {self.config_file}")
        
    def is_ip_device(self, device_id: str) -> bool:
        """判断设备ID是否为IP地址连接方式"""
        # IP地址连接的设备ID通常是 IP:端口 格式
        ip_pattern = r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+$'
        return bool(re.match(ip_pattern, device_id))
        
    def run_adb_command(self, port: int, command: str) -> Tuple[bool, str, str]:
        """执行ADB命令"""
        cmd = f"adb -P {port} {command}"
        try:
            result = subprocess.run(
                cmd.split(),
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            self.logger.error(f"命令超时: {cmd}")
            return False, "", "Command timeout"
        except Exception as e:
            self.logger.error(f"执行命令失败 {cmd}: {e}")
            return False, "", str(e)
            
    def get_connected_devices(self, port: int) -> List[Tuple[str, str]]:
        """获取指定端口上所有连接的设备"""
        devices = []
        success, stdout, stderr = self.run_adb_command(port, "devices")
        if success:
            lines = stdout.strip().split('\n')
            for line in lines[1:]:  # 跳过第一行
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 2:
                        device_id = parts[0]
                        status = parts[1]
                        devices.append((device_id, status))
        return devices
        
    def disconnect_unauthorized_devices(self, port: int):
        """断开未授权的设备连接"""
        # 获取该端口的授权设备列表
        authorized = self.authorized_devices.get(port, set())
        if not authorized:
            return
            
        # 获取当前连接的所有设备
        connected_devices = self.get_connected_devices(port)
        
        for device_id, status in connected_devices:
            # 只处理已连接的设备
            if status != "device":
                continue
                
            # 只处理IP连接的设备
            if not self.is_ip_device(device_id):
                self.logger.debug(f"跳过非IP设备: {device_id}")
                continue
                
            # 检查是否在授权列表中
            if device_id not in authorized:
                self.logger.warning(f"发现未授权设备 {device_id} 连接到端口 {port}，正在断开...")
                
                # 断开未授权设备
                success, stdout, stderr = self.run_adb_command(port, f"disconnect {device_id}")
                if success:
                    self.logger.info(f"已断开未授权设备: {device_id}")
                    self.send_notification(f"已断开未授权设备: {device_id} (端口: {port})")
                else:
                    self.logger.error(f"断开设备失败 {device_id}: {stderr}")
                    
    def monitor_unauthorized_devices(self):
        """监控未授权设备的专用线程"""
        check_interval = self.config.get('unauthorized_check_interval', 10)
        self.logger.info(f"未授权设备监控线程已启动，检查间隔: {check_interval}秒")
        
        while self.running.is_set():
            try:
                for server in self.config.get('servers', []):
                    port = server['port']
                    # 检查是否启用严格模式
                    strict_mode = server.get('strict_mode', True)
                    if strict_mode:
                        self.disconnect_unauthorized_devices(port)
                        
                # 使用可中断的等待
                for _ in range(check_interval):
                    if not self.running.is_set():
                        break
                    time.sleep(1)
                    
            except Exception as e:
                self.logger.error(f"未授权设备监控出错: {e}", exc_info=True)
                time.sleep(check_interval)
                
        self.logger.info("未授权设备监控线程已停止")
        
    def get_device_info(self, port: int, device: str) -> Dict:
        """获取设备详细信息"""
        info = {
            'connected': False,
            'model': 'Unknown',
            'android_version': 'Unknown',
            'battery_level': 'Unknown'
        }
        
        if self.check_device_connection(port, device):
            info['connected'] = True
            
            # 获取设备型号
            success, stdout, _ = self.run_adb_command(
                port, f"-s {device} shell getprop ro.product.model"
            )
            if success:
                info['model'] = stdout.strip()
                
            # 获取Android版本
            success, stdout, _ = self.run_adb_command(
                port, f"-s {device} shell getprop ro.build.version.release"
            )
            if success:
                info['android_version'] = stdout.strip()
                
            # 获取电池电量
            success, stdout, _ = self.run_adb_command(
                port, f"-s {device} shell dumpsys battery | grep level"
            )
            if success and stdout:
                try:
                    battery_line = stdout.strip()
                    battery_level = battery_line.split(':')[1].strip()
                    info['battery_level'] = f"{battery_level}%"
                except:
                    pass
                    
        return info
        
    def check_device_connection(self, port: int, device: str) -> bool:
        """检查设备连接状态"""
        success, stdout, stderr = self.run_adb_command(port, "devices")
        if success:
            lines = stdout.strip().split('\n')
            for line in lines[1:]:
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 2:
                        device_id = parts[0]
                        status = parts[1]
                        if device_id == device and status == "device":
                            return True
        return False
        
    def connect_device(self, port: int, device: str, name: str, retry_interval: int, max_retries: int) -> bool:
        """连接设备，包含重试机制"""
        retry_count = 0
        
        while retry_count < max_retries and self.running.is_set():
            self.logger.info(f"尝试连接设备 {name} ({device}) 到端口 {port} (尝试 {retry_count + 1}/{max_retries})")
            
            # 先尝试断开连接
            self.run_adb_command(port, f"disconnect {device}")
            time.sleep(1)
            
            # 尝试连接
            success, stdout, stderr = self.run_adb_command(port, f"connect {device}")
            
            if success and "connected" in stdout.lower():
                self.logger.info(f"成功连接设备 {name} ({device}) 到端口 {port}")
                
                # 更新设备状态
                with self.status_lock:
                    self.device_status[f"{port}:{device}"] = {
                        'name': name,
                        'status': 'connected',
                        'last_connected': datetime.now().isoformat(),
                        'retry_count': retry_count
                    }
                
                # 发送通知
                self.send_notification(f"设备已连接: {name} ({device}) - 端口: {port}")
                return True
            else:
                self.logger.warning(f"连接失败: {stdout} {stderr}")
                retry_count += 1
                
                if retry_count < max_retries and self.running.is_set():
                    self.logger.info(f"等待 {retry_interval} 秒后重试...")
                    # 使用可中断的等待
                    for _ in range(retry_interval):
                        if not self.running.is_set():
                            return False
                        time.sleep(1)
                    
        self.logger.error(f"无法连接设备 {name} ({device}) 到端口 {port}")
        
        # 更新设备状态
        with self.status_lock:
            self.device_status[f"{port}:{device}"] = {
                'name': name,
                'status': 'disconnected',
                'last_attempted': datetime.now().isoformat(),
                'error': 'Max retries exceeded'
            }
            
        # 发送通知
        self.send_notification(f"设备连接失败: {name} ({device}) - 端口: {port}")
        return False
        
    def send_notification(self, message: str):
        """发送通知"""
        notification_config = self.config.get('notification', {})
        if notification_config.get('enabled', False):
            self.logger.info(f"[通知] {message}")
            # 这里可以添加webhook或其他通知方式
            
    def monitor_device(self, port: int, device_config: Dict, server_config: Dict):
        """监控单个设备"""
        device = device_config['address']
        name = device_config.get('name', device)
        retry_interval = server_config.get('retry_interval', 10)
        max_retries = server_config.get('max_retries', 5)
        check_interval = self.config.get('check_interval', 5)
        
        thread_name = threading.current_thread().name
        self.logger.info(f"[{thread_name}] 开始监控设备 {name} - 端口: {port}, 地址: {device}")
        
        # 首次连接
        if not self.check_device_connection(port, device):
            self.connect_device(port, device, name, retry_interval, max_retries)
        else:
            # 获取设备信息
            device_info = self.get_device_info(port, device)
            self.logger.info(f"设备信息 {name}: {device_info}")
            with self.status_lock:
                self.device_status[f"{port}:{device}"] = {
                    'name': name,
                    'status': 'connected',
                    'info': device_info
                }
        
        # 持续监控
        consecutive_failures = 0
        while self.running.is_set():
            try:
                if not self.check_device_connection(port, device):
                    consecutive_failures += 1
                    self.logger.warning(
                        f"[{thread_name}] 检测到设备 {name} ({device}) 在端口 {port} 上断开连接 "
                        f"(连续失败: {consecutive_failures})"
                    )
                    
                    if not self.connect_device(port, device, name, retry_interval, max_retries):
                        # 如果连续失败次数过多，增加检查间隔
                        extended_interval = check_interval * min(consecutive_failures, 10)
                        self.logger.info(f"[{thread_name}] 延长检查间隔至 {extended_interval} 秒")
                        # 使用可中断的等待
                        for _ in range(extended_interval):
                            if not self.running.is_set():
                                break
                            time.sleep(1)
                    else:
                        consecutive_failures = 0
                else:
                    if consecutive_failures > 0:
                        self.logger.info(f"[{thread_name}] 设备 {name} 恢复正常连接")
                        consecutive_failures = 0
                        
                    self.logger.debug(f"[{thread_name}] 设备 {name} ({device}) 在端口 {port} 上连接正常")
                    
                # 使用可中断的等待
                for _ in range(check_interval):
                    if not self.running.is_set():
                        break
                    time.sleep(1)
                
            except Exception as e:
                self.logger.error(f"[{thread_name}] 监控设备时发生错误: {e}", exc_info=True)
                time.sleep(check_interval)
                
        self.logger.info(f"[{thread_name}] 停止监控设备 {name}")
                
    def get_status_report(self) -> str:
        """获取状态报告"""
        with self.status_lock:
            report = "=== ADB监控状态报告 ===\n"
            report += f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            report += f"运行状态: {'运行中' if self.running.is_set() else '已停止'}\n"
            report += f"活跃线程数: {len([t for t in self.monitor_threads if t.is_alive()])}\n\n"
            
            # 按端口分组显示
            for server in self.config['servers']:
                port = server['port']
                strict_mode = server.get('strict_mode', True)
                report += f"端口 {port} (严格模式: {'开' if strict_mode else '关'}):\n"
                
                # 获取所有连接的设备
                all_connected = self.get_connected_devices(port)
                authorized = self.authorized_devices.get(port, set())
                
                # 显示授权设备状态
                report += "  授权设备:\n"
                for device_config in server['devices']:
                    device = device_config['address']
                    name = device_config.get('name', device)
                    is_connected = self.check_device_connection(port, device)
                    
                    report += f"    {name} ({device}): {'已连接' if is_connected else '未连接'}\n"
                    
                    if is_connected:
                        device_info = self.get_device_info(port, device)
                        report += f"      型号: {device_info.get('model', 'Unknown')}\n"
                        report += f"      Android版本: {device_info.get('android_version', 'Unknown')}\n"
                        report += f"      电池电量: {device_info.get('battery_level', 'Unknown')}\n"
                
                # 显示未授权设备
                unauthorized_devices = []
                for device_id, status in all_connected:
                    if status == "device" and device_id not in authorized and self.is_ip_device(device_id):
                        unauthorized_devices.append(device_id)
                        
                if unauthorized_devices:
                    report += "  未授权设备 (将被断开):\n"
                    for device_id in unauthorized_devices:
                        report += f"    {device_id}\n"
                        
                report += "\n"
                
            return report
            
    def command_listener(self):
        """监听控制命令的线程"""
        self.logger.info("控制命令监听器已启动 (输入 'help' 查看可用命令)")
        
        while self.running.is_set():
            try:
                # 非阻塞方式读取输入
                import select
                if sys.platform == 'win32':
                    # Windows平台
                    import msvcrt
                    if msvcrt.kbhit():
                        command = input().strip().lower()
                        self.process_command(command)
                else:
                    # Unix平台
                    rlist, _, _ = select.select([sys.stdin], [], [], 0.1)
                    if rlist:
                        command = sys.stdin.readline().strip().lower()
                        self.process_command(command)
                        
                time.sleep(0.1)
            except Exception as e:
                self.logger.error(f"命令监听器错误: {e}")
                
    def process_command(self, command: str):
        """处理控制命令"""
        if command == 'help':
            print("\n可用命令:")
            print("  status - 显示当前状态")
            print("  clean - 立即清理所有未授权设备")
            print("  reload - 重新加载配置文件")
            print("  stop/quit/exit - 停止服务")
            print("  help - 显示此帮助信息")
            print()
        elif command == 'status':
            print("\n" + self.get_status_report())
        elif command == 'clean':
            self.logger.info("手动触发清理未授权设备")
            for server in self.config.get('servers', []):
                if server.get('strict_mode', True):
                    self.disconnect_unauthorized_devices(server['port'])
        elif command == 'reload':
            self.logger.info("重新加载配置文件")
            try:
                self.load_config()
                self.logger.info("配置文件重新加载成功")
            except Exception as e:
                self.logger.error(f"重新加载配置文件失败: {e}")
        elif command in ['stop', 'quit', 'exit']:
            self.logger.info("收到停止命令")
            self.stop()
        else:
            print(f"未知命令: {command}")
            
    def start(self):
        """启动监控服务"""
        self.logger.info("启动ADB监控服务")
        
        # 注册信号处理
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        if sys.platform == 'win32':
            # Windows额外的信号
            signal.signal(signal.SIGBREAK, self.signal_handler)
        
        # 启动命令监听器线程
        command_thread = threading.Thread(
            target=self.command_listener,
            daemon=True,
            name="CommandListener"
        )
        command_thread.start()
        
        # 启动未授权设备监控线程
        unauthorized_monitor_thread = threading.Thread(
            target=self.monitor_unauthorized_devices,
            daemon=True,
            name="UnauthorizedMonitor"
        )
        unauthorized_monitor_thread.start()
        self.monitor_threads.append(unauthorized_monitor_thread)
        
        # 为每个设备创建监控线程
        thread_counter = 0
        for server in self.config.get('servers', []):
            port = server['port']
            for device_config in server['devices']:
                thread_counter += 1
                thread = threading.Thread(
                    target=self.monitor_device,
                    args=(port, device_config, server),
                    daemon=True,
                    name=f"Monitor-P{port}-D{thread_counter}"
                )
                thread.start()
                self.monitor_threads.append(thread)
                time.sleep(0.1)  # 避免同时启动太多线程
                
        self.logger.info(f"已启动 {len(self.monitor_threads)} 个监控线程")
        
        # 定期输出状态报告
        status_interval = self.config.get('status_report_interval', 300)  # 默认5分钟
        last_status_time = time.time()
        
        # 主线程等待
        try:
            while self.running.is_set():
                time.sleep(1)
                
                # 定期输出状态报告
                if time.time() - last_status_time >= status_interval:
                    self.logger.info("\n" + self.get_status_report())
                    last_status_time = time.time()
                    
                # 检查是否所有监控线程都还活着
                alive_threads = [t for t in self.monitor_threads if t.is_alive()]
                if len(alive_threads) < len(self.monitor_threads):
                    dead_count = len(self.monitor_threads) - len(alive_threads)
                    self.logger.warning(f"检测到 {dead_count} 个监控线程已停止")
                    
        except KeyboardInterrupt:
            self.logger.info("收到键盘中断信号 (Ctrl+C)")
            self.stop()
            
    def signal_handler(self, signum, frame):
        """信号处理器"""
        signal_names = {
            signal.SIGINT: 'SIGINT',
            signal.SIGTERM: 'SIGTERM',
        }
        if sys.platform == 'win32' and hasattr(signal, 'SIGBREAK'):
            signal_names[signal.SIGBREAK] = 'SIGBREAK'
            
        signal_name = signal_names.get(signum, f'Signal {signum}')
        self.logger.info(f"收到信号: {signal_name}")
        self.stop()
        
    def stop(self):
        """停止监控服务"""
        if not self.running.is_set():
            return
            
        self.logger.info("正在停止ADB监控服务...")
        
        # 设置停止标志
        self.running.clear()
        
        # 输出最终状态报告
        try:
            self.logger.info("\n" + self.get_status_report())
        except Exception as e:
            self.logger.error(f"生成最终报告时出错: {e}")
        
        # 等待所有线程结束
        self.logger.info("等待所有监控线程结束...")
        for thread in self.monitor_threads:
            if thread.is_alive():
                thread.join(timeout=5)
                if thread.is_alive():
                    self.logger.warning(f"线程 {thread.name} 未能在5秒内结束")
                    
        self.logger.info("ADB监控服务已停止")
        
        # 确保程序退出
        os._exit(0)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='ADB多设备连接监控服务（支持设备白名单）')
    parser.add_argument(
        '-c', '--config',
        default='adb_config.json',
        help='配置文件路径 (默认: adb_config.json)'
    )
    parser.add_argument(
        '-l', '--log-level',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='日志级别 (默认: INFO)'
    )
    parser.add_argument(
        '--status',
        action='store_true',
        help='输出当前状态并退出'
    )
    
    args = parser.parse_args()
    
    # 创建并启动监控器
    monitor = ADBMonitorMultiDevice(args.config, args.log_level)
    
    if args.status:
        # 只输出状态
        print(monitor.get_status_report())
    else:
        # 启动监控服务
        try:
            monitor.start()
        except Exception as e:
            monitor.logger.error(f"服务异常退出: {e}", exc_info=True)
            sys.exit(1)


if __name__ == "__main__":
    main()
```

更新后的配置文件示例（adb_config.json）：

```json
{
  "servers": [
    {
      "port": 5037,
      "devices": [
        {
          "address": "192.168.1.100:5555",
          "name": "测试手机1"
        },
        {
          "address": "192.168.1.101:5555",
          "name": "测试手机2"
        }
      ],
      "retry_interval": 10,
      "max_retries": 5,
      "strict_mode": true
    },
    {
      "port": 5038,
      "devices": [
        {
          "address": "192.168.1.102:5555",
          "name": "开发机1"
        }
      ],
      "retry_interval": 15,
      "max_retries": 5,
      "strict_mode": true
    },
    {
      "port": 5039,
      "devices": [
        {
          "address": "192.168.1.103:5555",
          "name": "测试平板"
        }
      ],
      "retry_interval": 20,
      "max_retries": 3,
      "strict_mode": false
    }
  ],
  "check_interval": 5,
  "unauthorized_check_interval": 10,
  "status_report_interval": 300,
  "notification": {
    "enabled": true,
    "webhook": "https://your-webhook-url"
  }
}
```

主要新增功能：

1. **设备白名单机制**：
   - 每个端口维护一个授权设备列表
   - 定期检查并断开未授权的IP连接设备
   - 只处理IP地址连接的设备，不影响USB连接

2. **严格模式控制**：
   - 每个server可以单独配置`strict_mode`
   - 开启时会自动断开未授权设备
   - 关闭时只监控不断开

3. **未授权设备监控**：
   - 独立的监控线程定期检查
   - 可配置检查间隔（`unauthorized_check_interval`）
   - 发现未授权设备时自动断开并记录

4. **增强的状态报告**：
   - 显示每个端口的严格模式状态
   - 列出所有授权设备及其连接状态
   - 显示检测到的未授权设备

5. **新增命令**：
   - `clean` - 手动触发清理所有未授权设备
   - `reload` - 重新加载配置文件（可以动态更新授权设备列表）

6. **安全特性**：
   - 只断开IP地址格式的设备（避免影响USB连接）
   - 使用正则表达式严格匹配IP:端口格式
   - 详细的日志记录所有断开操作

使用示例：

```bash
# 启动服务（默认开启严格模式）
python adb_monitor.py

# 调试模式查看详细信息
python adb_monitor.py -l DEBUG

# 运行时命令：
# clean - 立即清理未授权设备
# reload - 重新加载配置（可以更新设备白名单）
# status - 查看当前状态（包括未授权设备）
```

这个版本会确保每个ADB server只连接配置文件中指定的设备，自动断开任何未经授权的IP连接设备。