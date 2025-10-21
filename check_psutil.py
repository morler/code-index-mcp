try:
    import psutil

    print("psutil available:", psutil.__version__)

    import time

    start = time.perf_counter()
    process = psutil.Process()
    memory_info = process.memory_info()
    system_memory = psutil.virtual_memory()
    end = time.perf_counter()
    print(f"psutil operations took {end - start:.3f}s")
    print(f"RSS: {memory_info.rss / 1024 / 1024:.1f}MB")

except ImportError as e:
    print("psutil not available:", e)
