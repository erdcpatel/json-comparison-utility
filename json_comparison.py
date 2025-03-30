import json
from collections import defaultdict
from typing import Dict, List, Set, Optional, Union


def flatten_json(nested_json: Union[Dict, List], prefix: str = '', separator: str = '.') -> Dict:
    """Flatten a nested JSON object"""
    flattened = {}

    if isinstance(nested_json, dict):
        for key, value in nested_json.items():
            new_key = f"{prefix}{separator}{key}" if prefix else key
            if isinstance(value, (dict, list)):
                flattened.update(flatten_json(value, new_key, separator))
            else:
                flattened[new_key] = value
    elif isinstance(nested_json, list):
        for i, item in enumerate(nested_json):
            new_key = f"{prefix}[{i}]" if prefix else f"[{i}]"
            if isinstance(item, (dict, list)):
                flattened.update(flatten_json(item, new_key, separator))
            else:
                flattened[new_key] = item

    return flattened


def get_all_keys(data: Union[Dict, List], prefix: str = '', separator: str = '.') -> Set[str]:
    """Get all keys from a JSON object recursively"""
    keys = set()

    if isinstance(data, dict):
        for key, value in data.items():
            new_key = f"{prefix}{separator}{key}" if prefix else key
            if isinstance(value, (dict, list)):
                keys.update(get_all_keys(value, new_key, separator))
            else:
                keys.add(new_key)
    elif isinstance(data, list):
        for i, item in enumerate(data):
            new_key = f"{prefix}[{i}]" if prefix else f"[{i}]"
            if isinstance(item, (dict, list)):
                keys.update(get_all_keys(item, new_key, separator))
            else:
                keys.add(new_key)

    return keys


def get_potential_join_keys(left_data: Union[Dict, List], right_data: Union[Dict, List], sample_size: int = 5) -> List[
    str]:
    """
    Get potential join keys by analyzing the structure of both JSONs
    Returns keys that exist in both structures and have consistent values
    """

    def get_keys_from_sample(data: Union[Dict, List]) -> Set[str]:
        """Get keys from a sample of objects"""
        if isinstance(data, dict):
            return set(data.keys())
        elif isinstance(data, list) and data and isinstance(data[0], dict):
            # Sample first few items to find common keys
            sample = data[:sample_size]
            common_keys = set(sample[0].keys()) if sample else set()
            for item in sample[1:]:
                common_keys.intersection_update(item.keys())
            return common_keys
        return set()

    left_keys = get_keys_from_sample(left_data)
    right_keys = get_keys_from_sample(right_data)

    # Only return keys that exist in both structures
    potential_keys = list(left_keys & right_keys)

    # Sort keys by likelihood of being a good join key
    priority_keys = ['id', 'name', 'key', 'code', 'uuid']
    return sorted(potential_keys, key=lambda x: (x not in priority_keys, x))


def compare_json_objects(obj1: Dict, obj2: Dict) -> List[Dict]:
    """Compare two JSON objects and return differences"""
    flat1 = flatten_json(obj1)
    flat2 = flatten_json(obj2)

    all_keys = set(flat1.keys()).union(set(flat2.keys()))
    differences = []

    for key in sorted(all_keys):
        val1 = flat1.get(key, None)
        val2 = flat2.get(key, None)

        if val1 != val2:
            differences.append({
                'key': key,
                'left_value': val1,
                'right_value': val2,
                'status': 'different' if key in flat1 and key in flat2 else
                'left_only' if key in flat1 else 'right_only'
            })

    return differences


def compare_json_lists(list1: List[Dict], list2: List[Dict], join_key: str) -> List[Dict]:
    """Compare two lists of JSON objects using a join key"""
    if not list1 or not list2:
        return []

    # Create lookup dictionaries
    dict1 = {str(item.get(join_key)): item for item in list1 if join_key in item}
    dict2 = {str(item.get(join_key)): item for item in list2 if join_key in item}

    all_keys = set(dict1.keys()).union(set(dict2.keys()))
    differences = []

    for key in sorted(all_keys):
        obj1 = dict1.get(key)
        obj2 = dict2.get(key)

        if obj1 is None or obj2 is None:
            status = 'left_only' if obj2 is None else 'right_only'
            differences.append({
                'key': join_key,
                join_key: key,
                'left_value': obj1,
                'right_value': obj2,
                'status': status
            })
        else:
            obj_diff = compare_json_objects(obj1, obj2)
            for diff in obj_diff:
                diff[join_key] = key
                differences.append(diff)

    return differences


def is_json_list_of_objects(data: Union[Dict, List]) -> bool:
    """Check if JSON is a list of objects"""
    return isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict)