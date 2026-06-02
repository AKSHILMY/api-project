from datetime import datetime
from typing import Optional
from models import Base

class Organization(Base):
    id : str
    name: str
    slug: str
    created_at : datetime    

class Project(Base):
    id : str
    org_id : str
    name: str
    slug: str
    description : Optional[str] = None
    created_at : datetime  
    # created_by
    # metadata

class Product(Base):
    id : str
    org_id : str
    project_id : Optional[str] = None
    name : str
    # created_by
    # metadata
    

