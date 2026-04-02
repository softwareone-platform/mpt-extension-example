import json
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from app.utils import get_instance_external_id


class BaseSchema(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
        populate_by_name=True,
    )


class AuthContext(BaseSchema):
    account_id: str
    account_type: str
    installation_id: str | None = None
    user_id: str | None = None
    token_id: str | None = None


class ExtensionContext(BaseSchema):
    extension_id: str
    instance_id: str
    account_id: str
    domain: str

    @classmethod
    def from_identity_file(cls) -> ExtensionContext:
        external_id = get_instance_external_id()
        identity_file = Path(__file__).parent.parent.parent.resolve() / f"{external_id}_identity.json"
        data = json.load(open(identity_file))
        return cls(
            extension_id=data["mrok"]["extension"],
            instance_id=data["mrok"]["instance"],
            account_id=data["mrok"]["tags"]["accountId"],
            domain=data["mrok"]["domain"],
        )

class Object(BaseSchema):
    id: Annotated[
        str,
        Field(
            description="Unique object ID, maps to the platform object ID property.",
        )
    ]
    name: Annotated[
        str,
        Field(
            description="Object name, maps to the platform object name property.",
        )
    ]
    object_type: Annotated[
        str,
        Field(
            alias="objectType",
            description=(
                "The object's type, maps to the “routing.entity” "
                "property of the EventMessage."
            ),
        )
    ]

class Task(BaseSchema):
    id: Annotated[
        str,
        Field(
            description=(
                "Unique platform task ID, maps to the ID of "
                "the task created by the Task Orchestrator."
            ),
        )
    ]

class Details(BaseSchema):
    event_type: Annotated[
        str,
        Field(
            alias="eventType",
            description=(
                "The type of the event. Maps to the “routing.event” property of the EventMessage."
            ),
        )
    ]
    enqueue_time: Annotated[
        datetime,
        Field(
            alias="enqueueTime",
            description=(
                "The date/time the platform became aware of this event. "
                "Maps to the “timestamp” property of EventMessage."
            ),
        )
    ]
    delivery_time: Annotated[
        datetime,
        Field(
            alias="deliveryTime",
            description=(
                "The date/time the platform is delivering this event to the extension. "
                "Defaults to current date/time on the server."
            )
        )
    ]

class Event(BaseSchema):
    id: Annotated[
        str,
        Field(
            description="Unique message ID, can be used to correlate with platform logs.",
        )
    ]
    object: Annotated[
        Object,
        Field(
            description=(
                "Information about the event's related object. Maps to the first object "
                "of category “CurrentEntity” in the “objects” property of the EventMessage."
            ),
        )
    ]
    details: Annotated[
        Details,
        Field(
            description=(
                "Information about this event. Maps to the “routing” property of the EventMessage."
            ),
        )
    ]
    task: Annotated[
        Task | None,
        Field(
            description=(
                "Information about the event's related task. "
                "Maps to the task created by Task Orchestrator."
            ),
        )
    ] = None


class EventResponse(BaseSchema):
    response: Literal["OK", "Delay", "Cancel"]
    delay: Annotated[
        int | None,
        Field(
            description=(
                "The minimum delay the Extensions Service "
                "must wait before sending the event again."
            )
        )
    ] = None

    @classmethod
    def ok(cls):
        return cls(response="OK")

    @classmethod
    def cancel(cls):
        return cls(response="Cancel")

    @classmethod
    def reschedule(cls, seconds: int | None = None):
        return cls(response="Delay", delay=seconds)
