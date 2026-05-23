from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class CreateUserRequest(BaseModel):
    username: str
    password: str
    role_name: str
    email: str 


class UpdateRoleRequest(BaseModel):
    role_name: str


class DeviceInput(BaseModel):
    id: Optional[int] = None
    hostname: str
    ip: str
    username: Optional[str] = None
    password: Optional[str] = None
    secret: Optional[str] = None
    role: str


class UserPolicy(BaseModel):
    source_zone: str
    destination_zone: str
    service: str
    action: str = "permit"


class ACLRequest(BaseModel):
    devices: List[DeviceInput]
    policies: List[UserPolicy]
    zones: Dict[str, List[str]]
    services: Dict[str, Dict[str, Any]]
    user_id: int = 1

class VLSMRequirement(BaseModel):
    zone_name:str
    required_hosts: int 


class VLSMInput(BaseModel):
    user_id: int
    report: Dict[str, Any]
    base_network: str
    requirements: List[VLSMRequirement]

class VLANRequestItem(BaseModel):
    zone_name: str
    vlan_name: str | None = None 
    required_hosts: int = 0

class VLANRequestInput(BaseModel):
    report: Dict[str, Any]
    requested_zones: List[VLANRequestItem]

class ACLPolicyInput(BaseModel):
    operation: str
    acl_name: Optional[str] = None
    source_site: Optional[str] = None
    destination_site: Optional[str] = None
    source_zone: Optional[str] = None
    destination_zone: Optional[str] = None
    protocol: Optional[str] = "any"
    port: Optional[int] = None
    action: Optional[str] = "deny"

class ACLRequestInput(BaseModel):
    report: Dict[str, Any]
    policies: List[ACLPolicyInput]




class SeedDeviceInput(BaseModel):
    hostname: Optional[str] = None
    ip: str
    username: str
    password: str
    secret: Optional[str] = None
    model: Optional[str] = ""

class SiteDiscoveryRequest(BaseModel):
    site_name: str = "SITE"
    seed_device: SeedDeviceInput



class AIReportRequest(BaseModel):
    user_id: int 
    user_input_text: str
    discovery_report: Dict[str, Any]
    

class Notification(BaseModel):
    id: int
    message: str
    is_read: bool
    created_at: datetime


class ScoreItem(BaseModel):
    score: int
    timestamp: datetime


class ScoreHistoryResponse(BaseModel):
    user_id: int
    history: List[ScoreItem]


class NetworkRenderInput(BaseModel):
    report: Dict[str, Any]
    base_network: str
    requested_zones: List[VLANRequestItem]
    requirements: List[VLSMRequirement]
    final_plan: Optional[list[dict]] = None



class DeployDeviceInput(BaseModel):
    hostname: str
    ip: str
    username: str
    password: str
    enable_password: Optional[str] = None


class DeployRequest(BaseModel):
    devices: List[DeployDeviceInput]    


