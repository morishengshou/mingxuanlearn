*Thinking...*

> 用户想在一台Windows电脑上运行多个Flask进程，每个进程通过ADB控制一个Android设备，但遇到了多个Flask进程抢占同一个ADB服务的问题。他尝试过用不同的ANDROID_ADB_SERVER_PORT，但多个ADB进程之间还是有冲突。
> 
> 这是一个典型的多进程并发控制问题。主要问题是：
> 1. 多个Flask进程共享同一个ADB服务会造成阻塞
> 2. 启动多个ADB服务会互相冲突
> 
> 解决方案：
> 1. 使用一个共享的ADB服务，但在Flask中实现适当的并发控制
> 2. 为每个设备创建独立的ADB环境
> 3. 使用锁机制或队列来管理ADB命令的执行
> 
> 最佳实践应该是：
> - 保持一个ADB服务实例
> - 在Flask中使用锁或队列来管理对ADB的访问
> - 为每个设备分配独立的标识符
> - 使用设备序列号来确保命令发送到正确的设备

这个问题的核心在于ADB的并发访问管理。我建议采用以下方案来解决：

## 方案一：共享ADB服务 + 并发控制（推荐）

保持单一ADB服务实例，在Flask应用层面实现并发控制：

```python
# adb_manager.py
import threading
import subprocess
import queue
import time
from contextlib import contextmanager

class ADBManager:
    def __init__(self):
        self.lock = threading.Lock()
        self.device_locks = {}  # 为每个设备创建独立的锁
        
    def get_device_lock(self, device_serial):
        """获取特定设备的锁"""
        if device_serial not in self.device_locks:
            self.device_locks[device_serial] = threading.Lock()
        return self.device_locks[device_serial]
    
    @contextmanager
    def device_operation(self, device_serial):
        """设备操作上下文管理器"""
        lock = self.get_device_lock(device_serial)
        lock.acquire()
        try:
            yield
        finally:
            lock.release()
    
    def execute_command(self, device_serial, command):
        """执行ADB命令"""
        with self.device_operation(device_serial):
            cmd = f"adb -s {device_serial} {command}"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return result.stdout, result.stderr

# 单例模式
adb_manager = ADBManager()
```

在Flask应用中使用：

```python
# app.py
from flask import Flask, jsonify, request
from adb_manager import adb_manager
import os

app = Flask(__name__)

# 从环境变量获取设备序列号
DEVICE_SERIAL = os.environ.get('DEVICE_SERIAL')
FLASK_PORT = int(os.environ.get('FLASK_PORT', 5000))

@app.route('/execute', methods=['POST'])
def execute_adb_command():
    command = request.json.get('command')
    if not command or not DEVICE_SERIAL:
        return jsonify({'error': 'Invalid request'}), 400
    
    stdout, stderr = adb_manager.execute_command(DEVICE_SERIAL, command)
    return jsonify({
        'stdout': stdout,
        'stderr': stderr,
        'device': DEVICE_SERIAL
    })

@app.route('/device/info')
def get_device_info():
    stdout, stderr = adb_manager.execute_command(DEVICE_SERIAL, "shell getprop ro.product.model")
    return jsonify({
        'device_serial': DEVICE_SERIAL,
        'model': stdout.strip(),
        'port': FLASK_PORT
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=FLASK_PORT)
```

## 方案二：使用队列系统

创建一个ADB命令队列处理器：

```python
# adb_queue_manager.py
import threading
import queue
import subprocess
import time

class ADBQueueManager:
    def __init__(self):
        self.command_queue = queue.Queue()
        self.results = {}
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.worker_thread.start()
    
    def _worker(self):
        """后台工作线程，顺序处理ADB命令"""
        while True:
            try:
                task_id, device_serial, command = self.command_queue.get(timeout=1)
                cmd = f"adb -s {device_serial} {command}"
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                self.results[task_id] = (result.stdout, result.stderr)
            except queue.Empty:
                continue
            except Exception as e:
                self.results[task_id] = ("", str(e))
    
    def execute_command_async(self, device_serial, command):
        """异步执行命令"""
        task_id = f"{device_serial}_{time.time()}"
        self.command_queue.put((task_id, device_serial, command))
        
        # 等待结果
        timeout = 30  # 30秒超时
        start_time = time.time()
        while task_id not in self.results:
            if time.time() - start_time > timeout:
                return "", "Command timeout"
            time.sleep(0.1)
        
        result = self.results.pop(task_id)
        return result

queue_manager = ADBQueueManager()
```

## 方案三：进程间通信架构

创建一个主ADB服务进程和多个Flask客户端：

```python
# adb_service.py - 主ADB服务
from flask import Flask, request, jsonify
import subprocess
import threading

app = Flask(__name__)
device_locks = {}

def get_device_lock(device_serial):
    if device_serial not in device_locks:
        device_locks[device_serial] = threading.Lock()
    return device_locks[device_serial]

@app.route('/adb/execute', methods=['POST'])
def execute_adb():
    data = request.json
    device_serial = data.get('device_serial')
    command = data.get('command')
    
    lock = get_device_lock(device_serial)
    with lock:
        cmd = f"adb -s {device_serial} {command}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    return jsonify({
        'stdout': result.stdout,
        'stderr': result.stderr
    })

if __name__ == '__main__':
    app.run(port=9999)  # ADB服务端口
```

Flask客户端调用：

```python
# flask_client.py
import requests
import os

class ADBClient:
    def __init__(self, device_serial):
        self.device_serial = device_serial
        self.adb_service_url = "http://localhost:9999"
    
    def execute_command(self, command):
        response = requests.post(
            f"{self.adb_service_url}/adb/execute",
            json={
                'device_serial': self.device_serial,
                'command': command
            }
        )
        return response.json()
```

## Windows服务配置

为每个Flask实例创建独立的winsw配置：

```xml
<!-- flask_device1.xml -->
<service>
  <id>FlaskDevice1</id>
  <name>Flask ADB Agent - Device 1</name>
  <description>Flask service for Android device 1</description>
  <executable>python</executable>
  <arguments>C:\path\to\app.py</arguments>
  <env name="DEVICE_SERIAL" value="device_serial_1"/>
  <env name="FLASK_PORT" value="5001"/>
  <logpath>C:\logs\device1</logpath>
</service>
```

## 最佳实践建议

1. **使用设备序列号**：始终通过 `-s` 参数指定设备序列号，避免命令发送到错误设备

2. **连接管理**：在启动时验证设备连接：
```python
def verify_device_connection(device_serial):
    cmd = f"adb -s {device_serial} get-state"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return "device" in result.stdout
```

3. **错误处理**：添加重试机制和错误恢复：
```python
def execute_with_retry(device_serial, command, max_retries=3):
    for i in range(max_retries):
        try:
            return adb_manager.execute_command(device_serial, command)
        except Exception as e:
            if i == max_retries - 1:
                raise
            time.sleep(1)
```

4. **监控和日志**：添加详细的日志记录和监控。

推荐使用方案一（共享ADB服务 + 并发控制），这是最简单且最稳定的方案。它避免了多个ADB服务实例的冲突，同时通过锁机制确保命令的顺序执行。