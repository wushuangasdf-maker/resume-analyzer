import json
import logging
import os
CACHE_PATH=os.path.join(os.path.dirname(__file__),"config","skill_cache.json")
def load_cache():
    try:
        with open(CACHE_PATH,"r",encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}
    except Exception:
        return {}
def save_cache(cache):
    try:
        os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
        with open(CACHE_PATH,"w",encoding="utf-8") as f:
             json.dump(
                 cache,
                 f,
                 ensure_ascii=False,
                 indent=2
             )
        return True
    except TypeError as e:
        logging.error(f"Cache数据无法JSON序列化: {e}")
        return False
    except PermissionError as e:
        logging.error(f"无权限写入缓存文件: {e}")
        return False
    except Exception as e:
        logging.error(f"未知缓存保存错误: {e}")
        return False