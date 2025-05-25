import re
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import uuid
import json
from pydantic import ValidationError


def validate_uuid(value: str) -> bool:
    """Validate if a string is a valid UUID"""
    try:
        uuid_obj = uuid.UUID(value)
        return str(uuid_obj) == value
    except (ValueError, AttributeError, TypeError):
        return False


def validate_odoo_domain(domain: List) -> bool:
    """Validate if a list is a valid Odoo domain"""
    if not isinstance(domain, list):
        return False
    
    # Empty domain is valid
    if not domain:
        return True
    
    # Check if domain is a list of tuples/lists with 3 elements
    for condition in domain:
        if not isinstance(condition, (list, tuple)):
            # Check for '&', '|', '!' operators
            if condition not in ['&', '|', '!']:
                return False
            continue
        
        # Check if condition has 3 elements: (field, operator, value)
        if len(condition) != 3:
            return False
        
        # Check if field is a string
        if not isinstance(condition[0], str):
            return False
        
        # Check if operator is a string
        if not isinstance(condition[1], str):
            return False
        
        # Check if operator is valid
        valid_operators = [
            '=', '!=', '>', '>=', '<', '<=', 'like', 'ilike', 
            'not like', 'not ilike', 'in', 'not in', 'child_of', 
            'parent_of', '=?', '=like', '=ilike'
        ]
        if condition[1] not in valid_operators:
            return False
    
    return True


def validate_odoo_fields(fields: Union[List[str], Dict[str, List[str]]]) -> bool:
    """Validate if fields parameter is valid for Odoo API calls"""
    # Fields can be a list of strings
    if isinstance(fields, list):
        return all(isinstance(field, str) for field in fields)
    
    # Or a dict with field names as keys and subfields as values
    if isinstance(fields, dict):
        for field, subfields in fields.items():
            if not isinstance(field, str):
                return False
            if not isinstance(subfields, list) or not all(isinstance(sf, str) for sf in subfields):
                return False
        return True
    
    return False


def validate_json(value: str) -> bool:
    """Validate if a string is valid JSON"""
    try:
        json.loads(value)
        return True
    except (json.JSONDecodeError, TypeError):
        return False


def validate_iso_date(value: str) -> bool:
    """Validate if a string is a valid ISO date format"""
    iso_regex = r'^(-?(?:[1-9][0-9]*)?[0-9]{4})-(1[0-2]|0[1-9])-(3[01]|0[1-9]|[12][0-9])T(2[0-3]|[01][0-9]):([0-5][0-9]):([0-5][0-9])(\.[0-9]+)?(Z|[+-](?:2[0-3]|[01][0-9]):[0-5][0-9])?$'
    match_iso = re.compile(iso_regex).match
    try:
        if match_iso(value) is not None:
            return True
    except:
        pass
    return False


def validate_email(value: str) -> bool:
    """Validate if a string is a valid email address"""
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(email_regex, value))


def validate_url(value: str) -> bool:
    """Validate if a string is a valid URL"""
    url_regex = r'^(https?|ftp):\/\/[^\s/$.?#].[^\s]*$'
    return bool(re.match(url_regex, value))


def sanitize_input(value: str) -> str:
    """Sanitize input string to prevent injection attacks"""
    # Remove any control characters
    value = re.sub(r'[\x00-\x1F\x7F]', '', value)
    
    # Escape HTML entities
    value = value.replace('&', '&amp;')
    value = value.replace('<', '&lt;')
    value = value.replace('>', '&gt;')
    value = value.replace('"', '&quot;')
    value = value.replace("'", '&#x27;')
    
    return value


def validate_model(model_instance: Any) -> Dict[str, List[str]]:
    """Validate a Pydantic model instance and return validation errors"""
    try:
        model_instance.validate({})
        return {}
    except ValidationError as e:
        errors = {}
        for error in e.errors():
            field = error["loc"][0]
            message = error["msg"]
            if field not in errors:
                errors[field] = []
            errors[field].append(message)
        return errors
