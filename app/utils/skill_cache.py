import json
import logging
import os

logger = logging.getLogger(__name__)

# 缓存文件放在 app/config/ 下，与其他配置文件统一管理
CACHE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "skill_cache.json")
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
        logger.error("Cache数据无法JSON序列化: %s", e)
        return False
    except PermissionError as e:
        logger.error("无权限写入缓存文件: %s", e)
        return False
    except Exception as e:
        logger.error("未知缓存保存错误: %s", e)
        return False