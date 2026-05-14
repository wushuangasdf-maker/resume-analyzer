import logging
from functools import wraps
def trace(func):
    @wraps(func)
    def wrapper(*args,**kwargs):
        logging.info(f"进入函数是：{func.__name__}")
        result = func(*args,**kwargs)
        logging.info(f"退出函数: {func.__name__}")
        return result
    return wrapper