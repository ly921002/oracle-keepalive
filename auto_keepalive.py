import psutil
import os
import time
import threading
import random
import signal
import sys

TARGET_CPU = os.getenv("TARGET_CPU", "20")
TARGET_MEM = os.getenv("TARGET_MEM", "20")
ADJUST_INTERVAL = 3  # seconds

# 全局变量
memory_block = None
stop_event = threading.Event()

# =============================
# 验证环境变量
# =============================
def validate_environment():
    global TARGET_CPU, TARGET_MEM
    try:
        TARGET_CPU = float(TARGET_CPU)
        TARGET_MEM = float(TARGET_MEM)
    except ValueError:
        raise ValueError("TARGET_CPU and TARGET_MEM must be numeric")
    
    if not (0 < TARGET_CPU <= 100):
        raise ValueError(f"TARGET_CPU must be 1-100, got {TARGET_CPU}")
    if not (0 < TARGET_MEM <= 80):
        raise ValueError(f"TARGET_MEM must be 1-80, got {TARGET_MEM}")

# =============================
# 信号处理
# =============================
def signal_handler(sig, frame):
    print("\n[INFO] Received interrupt signal, stopping threads...")
    stop_event.set()

# =============================
# 内存控制模块
# =============================
def memory_keeper():
    global memory_block
    try:
        total = psutil.virtual_memory().total
        target_bytes = int(total * TARGET_MEM / 100)
        print(f"[MEM] Total: {total/1024/1024/1024:.2f} GB, Target: {target_bytes/1024/1024:.2f} MB")
        
        # 一次性分配内存块
        try:
            memory_block = bytearray(target_bytes)
        except MemoryError:
            memory_block = bytearray(int(target_bytes * 0.8))
            print("[WARN] Memory allocation reduced to 80% due to MemoryError")
        
        page_size = 4096
        total_pages = len(memory_block) // page_size
        while not stop_event.is_set():
            # 每次随机触摸50个页面
            for _ in range(min(50, total_pages)):
                page_idx = random.randint(0, total_pages - 1)
                memory_block[page_idx*page_size] = (memory_block[page_idx*page_size] + 1) % 256
            # 打印内存使用率，每3秒一次
            print(f"[MEM] Usage: {psutil.virtual_memory().percent:.1f}% (Target {TARGET_MEM}%)")
            time.sleep(3)
    finally:
        memory_block = None
        print("[MEM] Memory keeper stopped")

# =============================
# CPU控制模块
# =============================
def cpu_keeper():
    busy_time = 0.05
    idle_time = 0.2
    last_adjust = time.time()
    
    try:
        while not stop_event.is_set():
            start_time = time.time()
            while time.time() - start_time < busy_time:
                if stop_event.is_set():
                    return
                # 占用CPU
                x = 0
                for _ in range(1000):
                    x += 1
            
            # 空闲等待
            sleep_end = time.time() + idle_time
            while time.time() < sleep_end:
                if stop_event.is_set():
                    return
                time.sleep(0.01)
            
            # 调整busy/idle时间
            if time.time() - last_adjust >= ADJUST_INTERVAL:
                current_cpu = psutil.cpu_percent(interval=0.5)
                error = TARGET_CPU - current_cpu
                if abs(error) > 2:
                    adjust = error * 0.002
                    busy_time = max(0.01, min(1.0, busy_time + adjust))
                    idle_time = max(0.01, min(2.0, idle_time - adjust))
                    # 限制总周期
                    total_cycle = busy_time + idle_time
                    if total_cycle > 3.0:
                        scale = 3.0 / total_cycle
                        busy_time *= scale
                        idle_time *= scale
                    print(f"[CPU] Current: {current_cpu:.1f}%, Busy: {busy_time:.3f}s, Idle: {idle_time:.3f}s")
                last_adjust = time.time()
    finally:
        print("[CPU] CPU keeper stopped")

# =============================
# 系统监控模块
# =============================
def system_monitor():
    try:
        while not stop_event.is_set():
            cpu = psutil.cpu_percent(interval=1)
            mem = psutil.virtual_memory()
            print(f"[MONITOR] CPU: {cpu:.1f}%, Mem: {mem.percent:.1f}% ({mem.used//1024//1024}MB/{mem.total//1024//1024}MB)")
            if mem.percent > 90:
                print("[WARN] Memory critically high!")
            if cpu > 90:
                print("[WARN] CPU critically high!")
            for _ in range(6):
                if stop_event.is_set():
                    break
                time.sleep(5)
    finally:
        print("[MONITOR] System monitor stopped")

# =============================
# 主函数
# =============================
def main():
    validate_environment()
    print(f"=== Resource Keeper Started ===\nTarget CPU: {TARGET_CPU}%, Target Mem: {TARGET_MEM}%\nPress Ctrl+C to stop\n" + "="*40)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    threads = [
        threading.Thread(target=memory_keeper),
        threading.Thread(target=cpu_keeper),
        threading.Thread(target=system_monitor)
    ]
    
    for t in threads:
        t.start()
    
    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        stop_event.set()
    finally:
        stop_event.set()
        print("=== Resource Keeper Stopped ===")

if __name__ == "__main__":
    main()
