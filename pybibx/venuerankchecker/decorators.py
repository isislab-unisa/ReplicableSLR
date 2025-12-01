from functools import wraps
import time

def log_call(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        cls_name = args[0].__class__.__name__
        print(f"📥 [{cls_name}] Calling {func.__name__} with args={args[1:]}, kwargs={kwargs}")
        result = func(*args, **kwargs)
        print(f"📤 [{cls_name}] Completed {func.__name__}")
        return result
    return wrapper
