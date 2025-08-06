from typing import Optional, List
from enum import Enum, auto


class Request:
    def __init__(self, url, use=None, force_charset=None, max_age=None):...


class Session:
    def queue(self, request: Request, func, context):...


class Person:
    def __init__(self, name: str, ssid: str, profile_url: Optional[str] = None):...


class Grade:
    def __init__(self, value: float, best: float, name: Optional[str] = None, type: Optional[str] = None):...


class Review:
    type: str = "pro"
    title: str
    url: str
    ssid: str
    date: str
    authors: List[Person] = []
    grades: List[Grade] = []

    def add_property(self, type: str, value: str|dict):...


class Product:
    name: str
    url: str
    ssid: str
    sku: Optional[str] = None
    category: str
    mpn: Optional[str] = None
    ean: Optional[str] = None
    reviews: List[Review] = []



session = Session()