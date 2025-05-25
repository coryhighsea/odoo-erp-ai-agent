from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional
from enum import Enum


class OdooField(BaseModel):
    """Model for Odoo field information"""
    name: str = Field(..., description="Field name")
    type: str = Field(..., description="Field type")
    string: str = Field(..., description="Field label")
    required: bool = Field(False, description="Whether the field is required")
    readonly: bool = Field(False, description="Whether the field is readonly")
    relation: Optional[str] = Field(None, description="Related model for relational fields")
    relation_field: Optional[str] = Field(None, description="Related field for relational fields")
    selection: Optional[List[tuple]] = Field(None, description="Selection options for selection fields")
    help: Optional[str] = Field(None, description="Field help text")


class OdooModelSchema(BaseModel):
    """Model for Odoo model schema"""
    name: str = Field(..., description="Model name")
    description: Optional[str] = Field(None, description="Model description")
    is_transient: bool = Field(False, description="Whether the model is transient")
    fields: Dict[str, OdooField] = Field(..., description="Model fields")


class OdooRecord(BaseModel):
    """Model for Odoo record data"""
    id: int = Field(..., description="Record ID")
    display_name: Optional[str] = Field(None, description="Record display name")
    data: Dict[str, Any] = Field(..., description="Record data")


class OdooSearchDomain(BaseModel):
    """Model for Odoo search domain"""
    field: str = Field(..., description="Field name")
    operator: str = Field("=", description="Comparison operator")
    value: Any = Field(..., description="Comparison value")

    def to_tuple(self) -> tuple:
        """Convert to Odoo domain tuple format"""
        return (self.field, self.operator, self.value)


class OdooBatchResult(BaseModel):
    """Model for Odoo batch operation result"""
    index: int = Field(..., description="Operation index in batch")
    success: bool = Field(..., description="Whether the operation was successful")
    result: Optional[Any] = Field(None, description="Operation result if successful")
    error: Optional[str] = Field(None, description="Error message if operation failed")
    execution_time_ms: int = Field(..., description="Execution time in milliseconds")


class OdooContext(BaseModel):
    """Model for Odoo context"""
    lang: str = Field("en_US", description="Language code")
    tz: str = Field("UTC", description="Timezone")
    uid: Optional[int] = Field(None, description="User ID")
    allowed_company_ids: Optional[List[int]] = Field(None, description="Allowed company IDs")
    active_model: Optional[str] = Field(None, description="Active model")
    active_id: Optional[int] = Field(None, description="Active record ID")
    active_ids: Optional[List[int]] = Field(None, description="Active record IDs")
    additional: Optional[Dict[str, Any]] = Field(None, description="Additional context values")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Odoo API calls"""
        result = {
            "lang": self.lang,
            "tz": self.tz
        }
        
        if self.uid:
            result["uid"] = self.uid
            
        if self.allowed_company_ids:
            result["allowed_company_ids"] = self.allowed_company_ids
            
        if self.active_model:
            result["active_model"] = self.active_model
            
        if self.active_id:
            result["active_id"] = self.active_id
            
        if self.active_ids:
            result["active_ids"] = self.active_ids
            
        if self.additional:
            result.update(self.additional)
            
        return result
