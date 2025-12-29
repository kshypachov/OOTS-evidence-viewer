import redis
import json
import logging


logger = logging.getLogger(__name__)

def conn_to_redis(redis_url):
    try:
        logger.info(f"Connecting to Redis at {redis_url}")
        redis_client = redis.Redis.from_url(redis_url)

        # check connection
        redis_client.ping()

        return redis_client
    except redis.ConnectionError as e:
        logger.critical(f"Error connecting to Redis: {e}")
        redis_client = None
        return redis_client




def get_data_from_redis(message_uuid, redis_client):
    """Get data from Redis by message_uuid"""
    if redis_client is None:
        print("Redis client is not connected. Aborting.")
        return None

    redis_key = f"oots:message:response:evidence:{message_uuid}"

    print(f"Get data from Redis by id: {redis_key}")

    try:
        # Get dara from Redis
        data = redis_client.get(redis_key)

        if data is None:
            print(f"Key {redis_key} is not found in Redis")
            return None

        print(f"Data got from Redis: {data[:100] if len(data) > 100 else data}...")

        # Parse JSON data if it's JSON'
        try:
            json_data = json.loads(data)
            return json_data
        except json.JSONDecodeError:
            # if not JSON, return as is
            return data

    except redis.RedisError as e:
        print(f"Redis error while getting data: {e}")
        return None
    except Exception as e:
        print(f"Unexpected Redis erro: {e}")
        return None


def parse_xml_to_dict(element):
    """Преобразует XML-элемент в словарь."""
    node = {}
    if element.text and element.text.strip():
        node["__text"] = element.text.strip()
    for child in element:
        if child.tag not in node:
            node[child.tag] = []
        node[child.tag].append(parse_xml_to_dict(child))
    return node