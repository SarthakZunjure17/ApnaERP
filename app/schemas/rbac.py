import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class PermissionBase(BaseModel):
    """
    Base Permission properties.
    """
    name: str = Field(..., min_length=1, max_length=150, description="Permission name")
    code: str = Field(..., min_length=1, max_length=100, description="Permission code (e.g. users.create)")
    description: Optional[str] = Field(None, max_length=255, description="Permission description")
    module_name: str = Field(..., min_length=1, max_length=100, description="Module name (e.g. users, hr)")


class PermissionCreate(PermissionBase):
    """
    Schema for creating a Permission.
    """
    pass


class PermissionUpdate(BaseModel):
    """
    Schema for updating a Permission.
    """
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    description: Optional[str] = Field(None, max_length=255)
    module_name: Optional[str] = Field(None, min_length=1, max_length=100)


class PermissionResponse(PermissionBase):
    """
    Schema for Permission API response.
    """
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class RoleBase(BaseModel):
    """
    Base Role properties.
    """
    name: str = Field(..., min_length=1, max_length=100, description="Role title")
    description: Optional[str] = Field(None, max_length=255, description="Role description")


class RoleCreate(RoleBase):
    """
    Schema for creating a Role.
    """
    permission_ids: Optional[List[uuid.UUID]] = Field(default=[], description="Initial permission UUIDs to attach")


class RoleUpdate(BaseModel):
    """
    Schema for updating a Role.
    """
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=255)


class RoleResponse(RoleBase):
    """
    Schema for Role API response.
    """
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    permissions: List[PermissionResponse] = []
    created_at: datetime
    updated_at: datetime


class UserRoleAssign(BaseModel):
    """
    Schema for assigning a Role to a User.
    """
    role_id: uuid.UUID = Field(..., description="Role UUID to assign")


class RolePermissionAssign(BaseModel):
    """
    Schema for assigning a Permission to a Role.
    """
    permission_id: uuid.UUID = Field(..., description="Permission UUID to assign")
