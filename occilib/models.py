"""

    models.py

        Simple data models validating data structures across the codebase and with input and output
        Most important models are implemented as classes and have their own file: Script, Param

"""


from enum import Enum
from typing import Any, List

from pydantic import BaseModel

#### VALUE ENUMS  ####

# type enum for Parameter
class ParamType(str,Enum):
    number = 'number'
    text = 'text'
    # TODO: more param types

class ModelUnits(str, Enum):
    mm = 'mm'
    cm = 'cm'
    dm = 'dm'
    m = 'm'
    inch = 'inch'
    foot = 'foot'
    mile = 'mile'

class ScriptCadLanguage(str,Enum):
    cadquery = 'cadquery'
    archiyou = 'archiyou'
    openscad = 'openscad'

class ModelFormat(str,Enum):
    step = 'step'
    gltf = 'gltf'
    stl = 'stl'

class ModelQuality(str,Enum):
    low = 'low'
    medium = 'medium'
    high = 'high'

class RequestResultFormat(str,Enum):
    full ='full'
    model = 'model'

#### IO MODELS ####

class ModelRequestInput(BaseModel):
    """ Used to handle input from API
        This is model is extended on runtime to include specific parameter names:
        ie: bracket?width=100
        Is is then turned into a generic ModelRequest
    """
    script_name:str = None # script name
    format: ModelFormat = 'step'
    return_format:RequestResultFormat = 'full' # either return full CadScript instance or only specific model


class ModelResult(BaseModel):
    id:str = None # name + param hash = instance hash
    request_id:str = None
    models:dict = {} # TODO Output models by format
    errors:List[Any] = []# TODO
    messages:List[Any] = [] # TODO
    tables:Any = [] # TODO
    duration:int = None # in ms