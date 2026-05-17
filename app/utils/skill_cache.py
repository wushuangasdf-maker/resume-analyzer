import json

CACHE_PATH="app/config/skill_cache.json"
def load_cache():
    try:
        with open(CACHE_PATH,"r",encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}
def save_cache(cache):
    with open(CACHE_PATH,"w",encoding="utf-8") as f:
        json.dump(
            cache,
            f,
            ensure_ascii=False,
            indent=2
        )