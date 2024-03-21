# -*- coding: utf-8 -*-
#
# Copyright (c) 2023, Development_Practices_Team
# All rights reserved.
#

from typing import List, Optional

from pydantic import BaseModel, validator

class Marketplace(BaseModel):
    id: str
    name: str
    description: str
    icon: Optional[str]

    @validator('icon')
    def set_icon(cls, icon):
        return icon or '/static/images/mkp.svg'


class Settings(BaseModel):
    marketplaces: List[Marketplace] = []


class Tier(BaseModel):
    id: str
    version: int
    name: str
    type: str
    db: str
    external_uid: str
    parent: dict
    owner: dict
    scopes: List[str]
    hub: dict
    events: dict
    environment: Optional[str]

class Asset(BaseModel):
    id: str
    status: str
    external_id: str
    external_uid: str
    product: dict
    connection: dict
    events: dict
    items: List[dict]
    params: List[dict]
    tiers: dict
    template: dict
    pending_request: dict
    marketplace: dict
    contract: dict
    configuration: dict
    environment: Optional[str]

class CreatedEvent(BaseModel):
    at: str

class Events(BaseModel):
    created: CreatedEvent
    updated: CreatedEvent

class Requests(BaseModel):
    id: str
    status: str
    created: str
    #asset: Asset
    #events: Events
    #asset_environment: Optional[str]


class Details(BaseModel):
    request_pr: List[Requests] = []


class Conversations(BaseModel):
    id: str
    type:str
    topic: str

class Details_comments(BaseModel):
    conversations: List[Conversations] = []

class Creator(BaseModel):
    id: str
    name: str

class CreatedEvent(BaseModel):
    at: str
    by: Creator

class Events(BaseModel):
    created: CreatedEvent

class Messages(BaseModel):
    id: str
    type: str
    text: str
    events : Events

class Details_messages(BaseModel):
    messages: List[Messages] = []