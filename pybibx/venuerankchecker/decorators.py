from functools import wraps
import time

def log_call(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        cls_name = args[0].__class__.__name__
        print(f"📥 [{cls_name}] Chiamata a {func.__name__} con args={args[1:]}, kwargs={kwargs}")
        result = func(*args, **kwargs)
        print(f"📤 [{cls_name}] Completata {func.__name__}")
        return result
    return wrapper
