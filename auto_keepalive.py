import psutil
import os
import time
import threading
import random
import signal
import sys

TARGET_CPU = float(os.getenv("TARGET_CPU", "20"))  # target 20%
TARGET_MEM = float(os.getenv("TARGET_MEM", "20"))  # target 20%
ADJUST_INTERVAL = 3  # seconds

# 验证环境变量
def validate_environment():
    """验证环境变量值的有效性"""
    if TARGET_CPU <= 0 or TARGET_CPU > 100:
        raise ValueError(f"TARGET_CPU must be between 1-100, got {TARGET_CPU}")
    if TARGET_MEM <= 0 or TARGET_MEM > 80:  # 限制最大内存使用，避免系统崩溃
        raise ValueError(f"TARGET_MEM must be between 1-80, got {TARGET_MEM}")

# 全局变量用于资源清理
memory_block = None
stop_event = threading.Event()

# =============================
#  信号处理 - 优雅退出
# =============================
def signal_handler(sig, frame):
    """处理退出信号"""
    print("\n[INFO] Received interrupt signal, cleaning up...")
    stop_event.set()
    sys.exit(0)

# =============================
#   Memory keeping module
# =============================
def memory_keeper():
    """内存占用控制模块"""
    global memory_block
    
    try:
        # 获取系统内存信息
        total = psutil.virtual_memory().total
        target_bytes = int(total * TARGET_MEM / 100)
        
        print(f"[MEM] Total memory: {total/1024/1024/1024:.2f} GB")
        print(f"[MEM] Target memory: {target_bytes/1024/1024:.2f} MB")

        while not stop_event.is_set():
            # 获取当前内存使用情况
            current_used = psutil.virtual_memory().used
            
            # 计算需要分配的内存（考虑系统已有使用）
            allocate_size = max(0, target_bytes - current_used)
            
            if allocate_size > 0:
                # 释放之前的内存块（如果有）
                if memory_block:
                    memory_block = None
                
                # 分配新内存块
                try:
                    memory_block = bytearray(allocate_size)
                    print(f"[MEM] Allocated {allocate_size/1024/1024:.2f} MB")
                except MemoryError:
                    print(f"[WARN] Memory allocation failed: {allocate_size/1024/1024:.2f} MB too large")
                    allocate_size = int(allocate_size * 0.8)  # 尝试分配80%
                    continue
            
            # 触摸部分内存页面来保持驻留（优化性能）
            if memory_block:
                page_size = 4096
                total_pages = len(memory_block) // page_size
                pages_to_touch = min(50, total_pages)  # 限制处理的页面数量
                
                for _ in range(pages_to_touch):
                    if stop_event.is_set():
                        break
                    page_idx = random.randint(0, total_pages - 1)
                    byte_idx = page_idx * page_size
                    if byte_idx < len(memory_block):
                        memory_block[byte_idx] = (memory_block[byte_idx] + 1) % 256
            
            # 显示当前内存使用率
            current_mem_percent = psutil.virtual_memory().percent
            print(f"[MEM] Current memory usage: {current_mem_percent:.1f}% (Target: {TARGET_MEM}%)")
            
            # 等待下一次调整
            for _ in range(10):  # 分10次检查，便于快速响应停止信号
                if stop_event.is_set():
                    break
                time.sleep(0.3)
                
    except Exception as e:
        print(f"[ERROR] Memory keeper failed: {e}")
    finally:
        # 清理内存
        if memory_block:
            memory_block = None
        print("[MEM] Memory keeper stopped")

# =============================
#   CPU auto-adjust module
# =============================
def cpu_keeper():
    """CPU占用控制模块"""
    try:
        busy_time = 0.05  # 初始忙碌时间
        idle_time = 0.2   # 初始空闲时间
        last_adjust = time.time()
        
        print(f"[CPU] Auto regulating CPU → {TARGET_CPU}%")

        while not stop_event.is_set():
            # 忙碌循环
            start_time = time.time()
            while time.time() - start_time < busy_time:
                if stop_event.is_set():
                    return
                pass  # 空循环占用CPU

            # 空闲等待
            sleep_end = time.time() + idle_time
            while time.time() < sleep_end:
                if stop_event.is_set():
                    return
                time.sleep(0.01)  # 小间隔睡眠便于响应停止信号

            # 定期调整参数（避免频繁调整导致震荡）
            current_time = time.time()
            if current_time - last_adjust >= ADJUST_INTERVAL:
                # 采样实际CPU使用率
                current_cpu = psutil.cpu_percent(interval=0.5)
                
                # 计算与目标的偏差
                error = TARGET_CPU - current_cpu
                
                # 死区控制：只有偏差较大时才调整
                if abs(error) > 2:
                    # 比例调节：偏差越大调整幅度越大
                    adjust_factor = error * 0.002
                    
                    # 调整时间参数
                    busy_time = max(0.01, min(1.0, busy_time + adjust_factor))
                    idle_time = max(0.01, min(2.0, idle_time - adjust_factor))
                    
                    # 保持总周期时间合理
                    total_cycle = busy_time + idle_time
                    if total_cycle > 3.0:
                        scale_factor = 3.0 / total_cycle
                        busy_time *= scale_factor
                        idle_time *= scale_factor
                    
                    print(f"[CPU] Current: {current_cpu:.1f}%, Target: {TARGET_CPU}%, "
                          f"Busy: {busy_time:.3f}s, Idle: {idle_time:.3f}s")
                
                last_adjust = current_time
                
    except Exception as e:
        print(f"[ERROR] CPU keeper failed: {e}")
    finally:
        print("[CPU] CPU keeper stopped")

# =============================
#  系统监控模块
# =============================
def system_monitor():
    """系统资源监控"""
    try:
        while not stop_event.is_set():
            # 获取系统信息
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            print(f"[MONITOR] CPU: {cpu_percent:.1f}% | "
                  f"Memory: {memory_percent:.1f}% | "
                  f"Used: {memory.used/1024/1024:.0f}MB / {memory.total/1024/1024:.0f}MB")
            
            # 检查系统状态
            if memory_percent > 90:
                print("[WARN] Memory usage critically high!")
            if cpu_percent > 90:
                print("[WARN] CPU usage critically high!")
                
            # 等待下一次监控
            for _ in range(6):
                if stop_event.is_set():
                    break
                time.sleep(5)  # 每30秒监控一次
                
    except Exception as e:
        print(f"[ERROR] System monitor failed: {e}")
    finally:
        print("[MONITOR] System monitor stopped")

def main():
    """主函数"""
    try:
        # 验证环境变量
        validate_environment()
        
        print(f"=== Resource Keeper Started ===")
        print(f"Target CPU: {TARGET_CPU}%")
        print(f"Target Memory: {TARGET_MEM}%")
        print(f"Press Ctrl+C to stop")
        print("=" * 40)
        
        # 注册信号处理
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # 启动各个模块
        threads = []
        
        # 内存控制线程
        mem_thread = threading.Thread(target=memory_keeper, daemon=True)
        mem_thread.start()
        threads.append(mem_thread)
        
        # CPU控制线程
        cpu_thread = threading.Thread(target=cpu_keeper, daemon=True)
        cpu_thread.start()
        threads.append(cpu_thread)
        
        # 系统监控线程
        monitor_thread = threading.Thread(target=system_monitor, daemon=True)
        monitor_thread.start()
        threads.append(monitor_thread)
        
        # 等待所有线程（实际上会被信号中断）
        for thread in threads:
            thread.join()
            
    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user")
    except Exception as e:
        print(f"[ERROR] Main process failed: {e}")
    finally:
        stop_event.set()
        print("=== Resource Keeper Stopped ===")

if __name__ == "__main__":
    main()
