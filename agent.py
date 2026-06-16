from typing import Optional, List, Dict, Union, Literal, Any
import sys


class Request:
    def __init__(self, url: str, use: Literal['curl', None] = None, force_charset: Literal['utf-8', None] = None, max_age: Optional[int] = None, options: Optional[str] = None):
        pass


class Session:
    sessionbreakers: List["SessionBreak"]

    def queue(self, request: Request, func: Any, context: Dict[str, Any]) -> None:
        pass
    def do(self, request: Request, func: Any, context: Dict[str, Any]) -> None:
        pass
    def emit(self, product: "Product") -> None:
        pass


class NodeSet:
    # returns another xpath nodeset
    def xpath(self, exp: str) -> "NodeSet":...
    # returns a string representation.
    # if the nodeset is alist, returns string representation of first element.
    # Both strip and normalize_space is default set to True.
    # normalize_space means that all sequences of whitespace (space, newline, tab) is replaced with a single space.
    # strip removes whitespace first and last in the string.
    # normalize_space also does strip. You need to switch off normalize_space if you extract written text or a list,
    # where newline characters are significant when interpreting the data!
    def string(self, strip: bool = True, normalize_space: bool = True, multiple: bool = False) -> str:...
    # if the nodeset is a list, joins together string representations of all elements with separator
    def join(self, seperator: str) -> str:...
    # returns a list of all string() values i nodeset list
    def strings(self) -> List[str]:...
    # pretty prints nodeset, used by debug feature,shouldn't be used in normal code
    def pretty(self, html_escape: bool = False, stream = sys.stdout, as_html: bool = True) -> None:...
    # if nodeset is list, returns first element. if empty list, returns default value
    def first(self, default=None) -> Optional[str]:...
    # opposite of first
    def last(self, default=None) -> Optional[str]:...

    def __iter__(self):
        return self

    def __next__(self):
        return self


class Response:
    response_url: str

    def xpath(self, exp: str) -> NodeSet:...
    def parse_fragment(self, html: str) -> NodeSet:...
    def content(self) -> str:...


class Person:
    def __init__(self, name: str, ssid: str, profile_url: Optional[str] = None): ...


class Grade:
    def __init__(self, value: float, best: float, name: Optional[str] = None, type: Optional[str] = None, description: Optional[str] = None): ...


class Review:
    type: Literal["pro", "user"] = "pro"
    title: str
    url: str
    ssid: str
    date: str
    authors: List[Person] = []
    grades: List[Grade] = []

    def add_property(self, type: Literal["pros", "cons", "is_recommended", "is_verified_buyer", "helpful_votes", "not_helpful_votes", "awards", "pages", "summary", "conclusion", "excerpt"], value: Union[str, dict, int, float]) -> None: ...
    def digest(self, text: Any = None) -> str: ...


class Product:
    name: str
    url: str
    ssid: str
    sku: Optional[str] = None
    category: str
    manufacturer: Optional[str] = None
    reviews: List[Review] = []

    def add_property(self, type: Literal["id.manufacturer", "id.ean"], value: str) -> None: ...


class SessionBreak:
    def __init__(self, max_requests):...


# session = Session()