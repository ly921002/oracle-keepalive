import psutil
import os
import time
import threading

TARGET_CPU = float(os.getenv("TARGET_CPU", 20))  # target 20%
TARGET_MEM = float(os.getenv("TARGET_MEM", 20))  # target 20%
ADJUST_INTERVAL = 3  # seconds

# =============================
#   Memory keeping module
# =============================
def memory_keeper():
    total = psutil.virtual_memory().total
    target = int(total * TARGET_MEM / 100)

    print(f"[MEM] Target memory: {target/1024/1024:.2f} MB")

    # Allocate main block
    block = bytearray(target)

    while True:
        # touch a few bytes to prevent optimization
        for i in range(0, len(block), 4096):
            block[i] = (block[i] + 1) % 256
        time.sleep(1)


# =============================
#   CPU auto-adjust module
# =============================
def cpu_keeper():
    busy = 0.05  # initial busy time
    idle = 0.2   # initial idle time

    print(f"[CPU] Auto regulating CPU → {TARGET_CPU}%")

    while True:
        # busy loop
        t0 = time.time()
        while time.time() - t0 < busy:
            pass

        # sleep
        time.sleep(idle)

        # sample actual CPU
        current_cpu = psutil.cpu_percent(interval=0.1)

        # auto adjust ratio
        if current_cpu < TARGET_CPU - 2:
            busy += 0.01
            idle = max(0.01, idle - 0.01)
        elif current_cpu > TARGET_CPU + 2:
            busy = max(0.01, busy - 0.01)
            idle += 0.01

        # keep ratio safe
        if busy < 0.01: busy = 0.01
        if idle < 0.01: idle = 0.01


def main():
    threading.Thread(target=memory_keeper, daemon=True).start()
    cpu_keeper()

if __name__ == "__main__":
    main()
