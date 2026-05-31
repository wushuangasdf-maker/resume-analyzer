from app.utils.logg import logger
from functools import wraps
def trace(func):
    @wraps(func)
    def wrapper(*args,**kwargs):
      try:
        logger.info(f"进入函数是：{func.__name__}")
        result = func(*args,**kwargs)
        logger.info(f"退出函数: {func.__name__}")
        return result
      except Exception as e:
          logger.exception(
              f"{func.__name__}执行失败:{e}"
          )
          raise
    return wrapper