"""
Custom JSON encoders for the API
"""
import json
from datetime import datetime, date
from typing import Any


class DateTimeEncoder(json.JSONEncoder):
    """
    Custom JSON encoder for datetime objects
    
    This encoder converts datetime objects to ISO format strings
    when serializing to JSON.
    """
    def default(self, obj: Any) -> Any:
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)
