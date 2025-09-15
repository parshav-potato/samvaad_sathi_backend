import datetime
import typing

import pydantic

from src.utilities.formatters.datetime_formatter import format_datetime_into_isoformat
from src.utilities.formatters.field_formatter import format_dict_key_to_camel_case


class BaseSchemaModel(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(
        from_attributes=True,
        validate_assignment=True,
        populate_by_name=True,
        json_encoders={datetime.datetime: format_datetime_into_isoformat},
        alias_generator=format_dict_key_to_camel_case,
    )
