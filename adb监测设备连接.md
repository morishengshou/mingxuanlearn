*Thinking...*

> 用户需要一个Python服务程序，用于监控多个ADB server的连接状态，并在连接断开时自动重连。主要需求：
> 
> 1. 监听多个端口上的ADB server
> 2. 每个ADB server连接不同的Android设备
> 3. 设备重启时需要自动重连
> 4. 重连失败时需要间隔重试
> 5. 端口和设备的对应关系使用JSON配置
> 
> 我需要设计一个程序包含：
> - JSON配置文件读取
> - 多线程/异步监控多个ADB server
> - 执行adb命令检查连接状态
> - 自动重连机制
> - 重试机制

我来帮你写一个Python服务程序，用于监控多个ADB server的连接状态并自动重连。

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

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('adb_monitor.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('ADB_Monitor')


class ADBMonitor:
    def __init__(self, config_file='adb_config.json'):
        self.config_file = config_file
        self.config = {}
        self.monitor_threads = []
        self.running = True
        self.load_config()
        
    def load_config(self):
        """加载配置文件"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            logger.info(f"成功加载配置文件: {self.config_file}")
            logger.info(f"监控配置: {json.dumps(self.config, indent=2, ensure_ascii=False)}")
        except FileNotFoundError:
            logger.error(f"配置文件 {self.config_file} 不存在")
            # 创建示例配置文件
            self.create_sample_config()
            sys.exit(1)
        except json.JSONDecodeError as e:
            logger.error(f"配置文件格式错误: {e}")
            sys.exit(1)
            
    def create_sample_config(self):
        """创建示例配置文件"""
        sample_config = {
            "servers": [
                {
                    "port": 5037,
                    "device": "192.168.1.100:5555",
                    "retry_interval": 10,
                    "max_retries": 5
                },
                {
                    "port": 5038,
                    "device": "192.168.1.101:5555",
                    "retry_interval": 15,
                    "max_retries": 5
                }
            ],
            "check_interval": 5
        }
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(sample_config, f, indent=2, ensure_ascii=False)
        logger.info(f"已创建示例配置文件: {self.config_file}")
        
    def run_adb_command(self, port, command):
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
            logger.error(f"命令超时: {cmd}")
            return False, "", "Command timeout"
        except Exception as e:
            logger.error(f"执行命令失败 {cmd}: {e}")
            return False, "", str(e)
            
    def check_device_connection(self, port, device):
        """检查设备连接状态"""
        success, stdout, stderr = self.run_adb_command(port, "devices")
        if success:
            # 解析输出，检查目标设备是否在线
            lines = stdout.strip().split('\n')
            for line in lines[1:]:  # 跳过第一行 "List of devices attached"
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 2:
                        device_id = parts[0]
                        status = parts[1]
                        if device_id == device and status == "device":
                            return True
        return False
        
    def connect_device(self, port, device, retry_interval, max_retries):
        """连接设备，包含重试机制"""
        retry_count = 0
        
        while retry_count < max_retries and self.running:
            logger.info(f"尝试连接设备 {device} 到端口 {port} (尝试 {retry_count + 1}/{max_retries})")
            
            success, stdout, stderr = self.run_adb_command(port, f"connect {device}")
            
            if success and "connected" in stdout.lower():
                logger.info(f"成功连接设备 {device} 到端口 {port}")
                return True
            else:
                logger.warning(f"连接失败: {stdout} {stderr}")
                retry_count += 1
                
                if retry_count < max_retries:
                    logger.info(f"等待 {retry_interval} 秒后重试...")
                    time.sleep(retry_interval)
                    
        logger.error(f"无法连接设备 {device} 到端口 {port}，已达到最大重试次数")
        return False
        
    def monitor_server(self, server_config):
        """监控单个ADB server"""
        port = server_config['port']
        device = server_config['device']
        retry_interval = server_config.get('retry_interval', 10)
        max_retries = server_config.get('max_retries', 5)
        check_interval = self.config.get('check_interval', 5)
        
        logger.info(f"开始监控端口 {port} 上的设备 {device}")
        
        # 首次连接
        if not self.check_device_connection(port, device):
            self.connect_device(port, device, retry_interval, max_retries)
        
        # 持续监控
        while self.running:
            try:
                if not self.check_device_connection(port, device):
                    logger.warning(f"检测到设备 {device} 在端口 {port} 上断开连接")
                    self.connect_device(port, device, retry_interval, max_retries)
                else:
                    logger.debug(f"设备 {device} 在端口 {port} 上连接正常")
                    
                time.sleep(check_interval)
                
            except Exception as e:
                logger.error(f"监控端口 {port} 时发生错误: {e}")
                time.sleep(check_interval)
                
    def start(self):
        """启动监控服务"""
        logger.info("启动ADB监控服务")
        
        # 为每个server创建监控线程
        for server in self.config.get('servers', []):
            thread = threading.Thread(
                target=self.monitor_server,
                args=(server,),
                daemon=True
            )
            thread.start()
            self.monitor_threads.append(thread)
            
        logger.info(f"已启动 {len(self.monitor_threads)} 个监控线程")
        
        # 主线程等待
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("收到退出信号")
            self.stop()
            
    def stop(self):
        """停止监控服务"""
        logger.info("正在停止ADB监控服务...")
        self.running = False
        
        # 等待所有线程结束
        for thread in self.monitor_threads:
            thread.join(timeout=5)
            
        logger.info("ADB监控服务已停止")


def main():
    """主函数"""
    # 检查是否有配置文件参数
    config_file = 'adb_config.json'
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
        
    # 创建并启动监控器
    monitor = ADBMonitor(config_file)
    monitor.start()


if __name__ == "__main__":
    main()
```

配置文件示例（adb_config.json）：

```json
{
  "servers": [
    {
      "port": 5037,
      "device": "192.168.1.100:5555",
      "retry_interval": 10,
      "max_retries": 5
    },
    {
      "port": 5038,
      "device": "192.168.1.101:5555",
      "retry_interval": 15,
      "max_retries": 5
    },
    {
      "port": 5039,
      "device": "192.168.1.102:5555",
      "retry_interval": 10,
      "max_retries": 3
    }
  ],
  "check_interval": 5
}
```

此外，我还为你准备了一个增强版本，支持更多功能：

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
from typing import Dict, List, Tuple

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


class ADBMonitorEnhanced:
    def __init__(self, config_file='adb_config.json', log_level='INFO'):
        self.config_file = config_file
        self.config = {}
        self.monitor_threads = []
        self.running = True
        self.device_status = {}  # 存储设备状态
        self.status_lock = threading.Lock()
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
            self.validate_config()
        except FileNotFoundError:
            self.logger.error(f"配置文件 {self.config_file} 不存在")
            self.create_sample_config()
            sys.exit(1)
        except json.JSONDecodeError as e:
            self.logger.error(f"配置文件格式错误: {e}")
            sys.exit(1)
            
    def validate_config(self):
        """验证配置文件"""
        required_fields = ['servers']
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"配置文件缺少必需字段: {field}")
                
        for server in self.config['servers']:
            if 'port' not in server or 'device' not in server:
                raise ValueError("每个server配置必须包含port和device字段")
                
    def create_sample_config(self):
        """创建示例配置文件"""
        sample_config = {
            "servers": [
                {
                    "port": 5037,
                    "device": "192.168.1.100:5555",
                    "name": "测试设备1",
                    "retry_interval": 10,
                    "max_retries": 5
                },
                {
                    "port": 5038,
                    "device": "192.168.1.101:5555",
                    "name": "测试设备2",
                    "retry_interval": 15,
                    "max_retries": 5
                }
            ],
            "check_interval": 5,
            "notification": {
                "enabled": false,
                "webhook": "https://your-webhook-url"
            }
        }
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(sample_config, f, indent=2, ensure_ascii=False)
        self.logger.info(f"已创建示例配置文件: {self.config_file}")
        
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
        
    def connect_device(self, port: int, device: str, retry_interval: int, max_retries: int) -> bool:
        """连接设备，包含重试机制"""
        retry_count = 0
        
        while retry_count < max_retries and self.running:
            self.logger.info(f"尝试连接设备 {device} 到端口 {port} (尝试 {retry_count + 1}/{max_retries})")
            
            # 先尝试断开连接
            self.run_adb_command(port, f"disconnect {device}")
            time.sleep(1)
            
            # 尝试连接
            success, stdout, stderr = self.run_adb_command(port, f"connect {device}")
            
            if success and "connected" in stdout.lower():
                self.logger.info(f"成功连接设备 {device} 到端口 {port}")
                
                # 更新设备状态
                with self.status_lock:
                    self.device_status[f"{port}:{device}"] = {
                        'status': 'connected',
                        'last_connected': datetime.now().isoformat(),
                        'retry_count': retry_count
                    }
                
                # 发送通知（如果启用）
                self.send_notification(f"设备已连接: {device} (端口: {port})")
                return True
            else:
                self.logger.warning(f"连接失败: {stdout} {stderr}")
                retry_count += 1
                
                if retry_count < max_retries:
                    self.logger.info(f"等待 {retry_interval} 秒后重试...")
                    time.sleep(retry_interval)
                    
        self.logger.error(f"无法连接设备 {device} 到端口 {port}，已达到最大重试次数")
        
        # 更新设备状态
        with self.status_lock:
            self.device_status[f"{port}:{device}"] = {
                'status': 'disconnected',
                'last_attempted': datetime.now().isoformat(),
                'error': 'Max retries exceeded'
            }
            
        # 发送通知
        self.send_notification(f"设备连接失败: {device} (端口: {port})")
        return False
        
    def send_notification(self, message: str):
        """发送通知（可以扩展为webhook、邮件等）"""
        notification_config = self.config.get('notification', {})
        if notification_config.get('enabled', False):
            webhook_url = notification_config.get('webhook')
            if webhook_url:
                # 这里可以实现webhook通知
                self.logger.info(f"发送通知: {message}")
                
    def monitor_server(self, server_config: Dict):
        """监控单个ADB server"""
        port = server_config['port']
        device = server_config['device']
        name = server_config.get('name', device)
        retry_interval = server_config.get('retry_interval', 10)
        max_retries = server_config.get('max_retries', 5)
        check_interval = self.config.get('check_interval', 5)
        
        self.logger.info(f"开始监控 {name} - 端口: {port}, 设备: {device}")
        
        # 首次连接
        if not self.check_device_connection(port, device):
            self.connect_device(port, device, retry_interval, max_retries)
        else:
            # 获取设备信息
            device_info = self.get_device_info(port, device)
            self.logger.info(f"设备信息 {name}: {device_info}")
        
        # 持续监控
        consecutive_failures = 0
        while self.running:
            try:
                if not self.check_device_connection(port, device):
                    consecutive_failures += 1
                    self.logger.warning(
                        f"检测到设备 {name} ({device}) 在端口 {port} 上断开连接 "
                        f"(连续失败: {consecutive_failures})"
                    )
                    
                    if not self.connect_device(port, device, retry_interval, max_retries):
                        # 如果连续失败次数过多，增加检查间隔
                        extended_interval = check_interval * min(consecutive_failures, 10)
                        self.logger.info(f"延长检查间隔至 {extended_interval} 秒")
                        time.sleep(extended_interval)
                    else:
                        consecutive_failures = 0
                else:
                    if consecutive_failures > 0:
                        self.logger.info(f"设备 {name} 恢复正常连接")
                        consecutive_failures = 0
                        
                    self.logger.debug(f"设备 {name} ({device}) 在端口 {port} 上连接正常")
                    
                time.sleep(check_interval)
                
            except Exception as e:
                self.logger.error(f"监控端口 {port} 时发生错误: {e}", exc_info=True)
                time.sleep(check_interval)
                
    def get_status_report(self) -> str:
        """获取状态报告"""
        with self.status_lock:
            report = "=== ADB监控状态报告 ===\n"
            report += f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            
            for server in self.config['servers']:
                port = server['port']
                device = server['device']
                name = server.get('name', device)
                key = f"{port}:{device}"
                
                status = self.device_status.get(key, {'status': 'unknown'})
                report += f"设备: {name}\n"
                report += f"  端口: {port}\n"
                report += f"  地址: {device}\n"
                report += f"  状态: {status.get('status', 'unknown')}\n"
                
                if self.check_device_connection(port, device):
                    device_info = self.get_device_info(port, device)
                    report += f"  型号: {device_info['model']}\n"
                    report += f"  Android版本: {device_info['android_version']}\n"
                    report += f"  电池电量: {device_info['battery_level']}\n"
                    
                report += "\n"
                
            return report
            
    def start(self):
        """启动监控服务"""
        self.logger.info("启动ADB监控服务")
        
        # 注册信号处理
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # 为每个server创建监控线程
        for server in self.config.get('servers', []):
            thread = threading.Thread(
                target=self.monitor_server,
                args=(server,),
                daemon=True,
                name=f"Monitor-{server['port']}"
            )
            thread.start()
            self.monitor_threads.append(thread)
            
        self.logger.info(f"已启动 {len(self.monitor_threads)} 个监控线程")
        
        # 定期输出状态报告
        status_interval = self.config.get('status_report_interval', 300)  # 默认5分钟
        last_status_time = time.time()
        
        # 主线程等待
        try:
            while self.running:
                time.sleep(1)
                
                # 定期输出状态报告
                if time.time() - last_status_time >= status_interval:
                    self.logger.info("\n" + self.get_status_report())
                    last_status_time = time.time()
                    
        except KeyboardInterrupt:
            pass
            
    def signal_handler(self, signum, frame):
        """信号处理器"""
        self.logger.info(f"收到信号 {signum}")
        self.stop()
        
    def stop(self):
        """停止监控服务"""
        self.logger.info("正在停止ADB监控服务...")
        self.running = False
        
        # 输出最终状态报告
        self.logger.info("\n" + self.get_status_report())
        
        # 等待所有线程结束
        for thread in self.monitor_threads:
            thread.join(timeout=5)
            
        self.logger.info("ADB监控服务已停止")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='ADB设备连接监控服务')
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
    monitor = ADBMonitorEnhanced(args.config, args.log_level)
    
    if args.status:
        # 只输出状态
        print(monitor.get_status_report())
    else:
        # 启动监控服务
        monitor.start()


if __name__ == "__main__":
    main()
```

这个增强版本包含以下特性：

1. **彩色日志输出**：不同级别的日志用不同颜色显示
2. **设备信息获取**：可以获取设备型号、Android版本、电池电量等信息
3. **状态报告**：定期输出所有设备的状态报告
4. **命令行参数**：支持指定配置文件、日志级别等
5. **通知功能**：预留了webhook等通知接口
6. **优雅退出**：支持信号处理，确保程序正确关闭
7. **连续失败处理**：连续失败时自动延长检查间隔

使用方法：

```bash
# 基本使用
python adb_monitor.py

# 指定配置文件
python adb_monitor.py -c my_config.json

# 调试模式
python adb_monitor.py -l DEBUG

# 查看当前状态
python adb_monitor.py --status
```

程序会自动创建logs目录存储日志文件，并在控制台实时显示彩色日志。你可以根据实际需求调整配置文件中的参数。