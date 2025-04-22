# import time
# from concurrent.futures import ProcessPoolExecutor
# from multiprocessing import cpu_count

# import logging

# log_format = "%(asctime)s [%(levelname)s] - %(name)s - %(funcName)s(%(lineno)d) - %(message)s"

# stream_handler = logging.StreamHandler()
# stream_handler.setLevel(logging.DEBUG)
# stream_handler.setFormatter(logging.Formatter(log_format))


# def get_logger(name):
#     logger = logging.getLogger(name)
#     logger.setLevel(logging.DEBUG)
#     logger.addHandler(stream_handler)
#     return logger


# # time_start = time()

# CPU_COUNT = cpu_count()
# executor = ProcessPoolExecutor(2 * CPU_COUNT + 1)

# range_ = 10**5

# def print_numb(i):
#     time.sleep(1)
#     log = get_logger(__name__)
#     log.error(f'{i=}')
#     # log.log(level=0, msg=f'{i=}')
#     # print(f"{i=}")


# def main1():
#     for i in range(range_):
#         # log = get_logger('print')
#         # log.log(level=0, msg=f'{i=}')
#         print_numb(i)

# def main():
#     # with ProcessPoolExecutor(2 * CPU_COUNT + 1) as executor:
#     for i in range(range_):
#         executor.submit(print_numb, i)

#     executor.shutdown()


# if __name__ == "__main__":
#     main()
    # print(time() - time_start)

# ------------------------------------------------------------------

from pydantic import BaseModel, Field, validator, root_validator, field_validator, model_validator, BeforeValidator, EmailStr, AfterValidator
from typing import List, Optional, Annotated
import re
from datetime import datetime


# def validate_participants(v):
#     if not re.match(r"^\w+([\.-]?\w+)*@\w+([\.-]?\w+)*(.\w{2,3})+$", v):
#         raise ValueError('Кожен учасник має мати валідну електронну адресу')
#     return v


# class Event(BaseModel):
#     title: str = Field(..., description="Назва події", min_length=5, max_length=100)
#     description: Optional[str] = Field(None, description="Опис події", max_length=500)
#     start_time: datetime = Field(..., description="Час початку події")
#     participants: List[Annotated[str, BeforeValidator(validate_participants)]] = Field(..., description="Список учасників події")

#     @model_validator(mode='after')
#     def check_dates(cls, values: "Event"):
#         start_time = values.start_time
#         print(f"{start_time = }")
#         if start_time and start_time < datetime.now():
#             raise ValueError('Час початку події не може бути в минулому')
#         return values

#     class Config:
#         json_schema_extra = {
#             "example": {
#                 "title": "Міжнародна конференція з програмування",
#                 "description": "Конференція для розробників",
#                 "start_time": "2023-09-01T10:00:00",
#                 "participants": ["janedoe@example.com", "johndoe@example.com"]
#             }
#         }
# event_data = {
#     "title": "Міжнародна конференція з програмування",
#     "start_time": "2025-09-01T10:00:00",
#     "participants": ["janedoe@example.com", "johndoe@example.com"]
# }

# event = Event(**event_data)
# print(event.model_dump_json(indent=2))



# -----------------------------------------------------

# from pydantic import BaseModel, Field, validator, EmailStr
# from typing import List, Optional
# from datetime import datetime
# from uuid import uuid4

# class EventModel(BaseModel):
#     id: Annotated[str, Field(default_factory=uuid4)]
#     name: str = Field(..., example="Annual Tech Conference")
#     description: Annotated[str, Field(..., examples=["A conference about the latest in technology"])]
#     start_datetime: datetime = Field(..., examples=["2023-12-25T09:00:00Z"])
#     emails: List[EmailStr] = Field(..., examples=[["example@example.com"]])

#     @field_validator('start_datetime')
#     def start_datetime_cannot_be_in_the_past(cls, v):
#         if v < datetime.now():
#             raise ValueError('start_datetime must be in the future')
#         return v

#     @model_validator(mode='after')
#     def validate_after(cls, values: "EventModel"):
#         if len(values.name) < len(values.description):
#             raise ValueError('name must be longer than description')

#     class Config:
#         str_min_length = 1
#         str_max_length = 255
#         # error_msg_templates = {
#         #     'value_error.missing': 'field required',
#         #     'value_error.any_str.min_length': 'ensure this value has at least {limit_value} characters',
#         #     'value_error.any_str.max_length': 'ensure this value has no more than {limit_value} characters',
#         #     'value_error.datetime': 'incorrect datetime format, use YYYY-MM-DDTHH:MM:SS format',
#         # }

# event = EventModel(
#     name="Ann",
#     description="4565",
#     start_datetime="2025-12-01",
#     emails=["example@example.com"]
# )
# event1 = EventModel(
#     name="Annual Tech Conference",
#     description="4565",
#     start_datetime="2025-12-01",
#     emails=["example@example.com"]
# )

# print(event.model_dump_json(indent=2))
# print(event1.model_dump_json(indent=2))


# from pydantic import BaseModel, EmailStr, ValidationError

# class Country(BaseModel):
#     name: str
#     code: str

# class City(BaseModel):
#     name: str
#     country: Country

# class Address(BaseModel):
#     street: str
#     city: City
#     postal_code: str

# class User(BaseModel):
#     name: str
#     email: EmailStr
#     address: Address

# # Тестування моделі
# try:
#     user = dict(
#         name="Alex",
#         email="alex@example.com",
#         address=dict(
#             street="Main Street 123",
#             city=dict(
#                 name="Springfield",
#                 country=dict(
#                     name="Fictional Land",
#                     code="FL"
#                 )
#             ),
#             postal_code="12345"
#         )
#     )
#     print("User model is valid:", user)
# except ValidationError as e:
#     print("Validation error:", e)

class User(BaseModel):
    name: str
    email: EmailStr
    signup_ts: datetime = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.strftime('%Y-%m-%d HULULU %H:%M:%S')
        }


user = User(name='Alex', email='alex@example.com', signup_ts=datetime.now())
serialized_user = user.model_dump_json()
print(serialized_user)
