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
print_lock = threading.Lock()

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
# 线程安全的打印函数
# =============================
def safe_print(message):
    with print_lock:
        print(message)

# =============================
# 内存控制模块
# =============================
def memory_keeper():
    global memory_block
    try:
        total_mem = psutil.virtual_memory().total
        target_bytes = int(total_mem * TARGET_MEM / 100)
        safe_print(f"[MEM] Total: {total_mem/1024/1024/1024:.2f} GB, Target: {target_bytes/1024/1024:.2f} MB")
        
        # 计算系统基础内存使用（不包含我们分配的内存）
        base_mem = psutil.virtual_memory().used
        
        # 需要分配的内存 = 目标内存 - 系统基础内存
        allocate_size = max(0, target_bytes - base_mem)
        
        if allocate_size > 0:
            try:
                memory_block = bytearray(allocate_size)
                safe_print(f"[MEM] Allocated {allocate_size/1024/1024:.2f} MB")
            except MemoryError:
                # 如果分配失败，尝试分配80%
                allocate_size = int(allocate_size * 0.8)
                try:
                    memory_block = bytearray(allocate_size)
                    safe_print(f"[MEM] Allocated reduced to {allocate_size/1024/1024:.2f} MB")
                except MemoryError:
                    safe_print("[ERROR] Memory allocation failed completely")
                    memory_block = None
        
        page_size = 4096
        last_print = time.time()
        
        while not stop_event.is_set():
            # 触摸内存页面保持驻留
            if memory_block is not None:
                total_pages = len(memory_block) // page_size
                if total_pages > 0:
                    # 每次随机触摸部分页面
                    pages_to_touch = min(50, total_pages)
                    for _ in range(pages_to_touch):
                        if stop_event.is_set():
                            break
                        page_idx = random.randint(0, total_pages - 1)
                        byte_idx = page_idx * page_size
                        if byte_idx < len(memory_block):
                            memory_block[byte_idx] = (memory_block[byte_idx] + 1) % 256
            
            # 每5秒打印一次内存使用率
            current_time = time.time()
            if current_time - last_print >= 5:
                current_percent = psutil.virtual_memory().percent
                safe_print(f"[MEM] Usage: {current_percent:.1f}% (Target: {TARGET_MEM}%)")
                last_print = current_time
            
            # 分段等待，便于响应停止事件
            for _ in range(10):
                if stop_event.is_set():
                    break
                time.sleep(0.3)
                
    except Exception as e:
        safe_print(f"[ERROR] Memory keeper error: {e}")
    finally:
        memory_block = None
        safe_print("[MEM] Memory keeper stopped")

# =============================
# CPU控制模块
# =============================
def cpu_keeper():
    # 初始参数
    busy_time = TARGET_CPU / 100.0 * 0.5  # 基于目标CPU的初始值
    idle_time = 0.5 - busy_time
    last_adjust = time.time()
    last_print = time.time()
    
    # 平滑滤波参数
    cpu_readings = []
    SMOOTHING_WINDOW = 3
    
    try:
        while not stop_event.is_set():
            # 忙碌循环
            start_time = time.time()
            while time.time() - start_time < busy_time:
                if stop_event.is_set():
                    return
                # 简单的CPU占用循环
                pass
            
            # 空闲等待
            sleep_end = time.time() + idle_time
            while time.time() < sleep_end:
                if stop_event.is_set():
                    return
                time.sleep(0.01)
            
            current_time = time.time()
            
            # 调整busy/idle时间
            if current_time - last_adjust >= ADJUST_INTERVAL:
                # 获取CPU使用率
                current_cpu = psutil.cpu_percent(interval=0.5)
                
                # 平滑滤波
                cpu_readings.append(current_cpu)
                if len(cpu_readings) > SMOOTHING_WINDOW:
                    cpu_readings.pop(0)
                smoothed_cpu = sum(cpu_readings) / len(cpu_readings)
                
                # 计算误差
                error = TARGET_CPU - smoothed_cpu
                
                # 使用更保守的调节策略
                if abs(error) > 3:  # 增加死区范围
                    # 根据误差大小调整步长
                    if abs(error) > 20:
                        adjust_factor = 0.01
                    elif abs(error) > 10:
                        adjust_factor = 0.005
                    else:
                        adjust_factor = 0.002
                    
                    # 根据误差方向调整
                    adjust = error * adjust_factor
                    
                    # 调整时间参数
                    new_busy = max(0.02, min(0.8, busy_time + adjust))
                    new_idle = max(0.02, min(1.5, idle_time - adjust))
                    
                    # 保持总周期合理
                    total_cycle = new_busy + new_idle
                    if total_cycle > 2.0:
                        scale = 2.0 / total_cycle
                        new_busy *= scale
                        new_idle *= scale
                    
                    busy_time, idle_time = new_busy, new_idle
                
                last_adjust = current_time
            
            # 每5秒打印一次状态
            if current_time - last_print >= 5:
                safe_print(f"[CPU] Current: {smoothed_cpu:.1f}%, Busy: {busy_time:.3f}s, Idle: {idle_time:.3f}s")
                last_print = current_time
                
    except Exception as e:
        safe_print(f"[ERROR] CPU keeper error: {e}")
    finally:
        safe_print("[CPU] CPU keeper stopped")

# =============================
# 系统监控模块
# =============================
def system_monitor():
    last_print = time.time()
    try:
        while not stop_event.is_set():
            current_time = time.time()
            
            # 每10秒打印一次详细监控信息
            if current_time - last_print >= 10:
                cpu = psutil.cpu_percent(interval=1)
                mem = psutil.virtual_memory()
                safe_print(f"[MONITOR] CPU: {cpu:.1f}%, Mem: {mem.percent:.1f}% ({mem.used//1024//1024}MB/{mem.total//1024//1024}MB)")
                
                if mem.percent > 90:
                    safe_print("[WARN] Memory critically high!")
                if cpu > 90:
                    safe_print("[WARN] CPU critically high!")
                
                last_print = current_time
            
            # 分段睡眠便于响应停止事件
            for _ in range(10):
                if stop_event.is_set():
                    break
                time.sleep(1)
                
    except Exception as e:
        safe_print(f"[ERROR] System monitor error: {e}")
    finally:
        safe_print("[MONITOR] System monitor stopped")

# =============================
# 主函数
# =============================
def main():
    try:
        validate_environment()
        safe_print(f"=== Resource Keeper Started ===")
        safe_print(f"Target CPU: {TARGET_CPU}%")
        safe_print(f"Target Memory: {TARGET_MEM}%")
        safe_print("Press Ctrl+C to stop")
        safe_print("=" * 40)
        
        # 注册信号处理
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # 创建并启动线程（设置为守护线程）
        threads = [
            threading.Thread(target=memory_keeper, daemon=True),
            threading.Thread(target=cpu_keeper, daemon=True),
            threading.Thread(target=system_monitor, daemon=True)
        ]
        
        for t in threads:
            t.start()
        
        # 主线程等待停止事件
        while not stop_event.is_set():
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        safe_print("\n[INFO] Interrupted by user")
    except Exception as e:
        safe_print(f"[ERROR] Main process error: {e}")
    finally:
        stop_event.set()
        # 等待一段时间让线程结束
        time.sleep(1)
        safe_print("=== Resource Keeper Stopped ===")

if __name__ == "__main__":
    main()
