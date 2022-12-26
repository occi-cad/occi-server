"""

    models.py

        Simple data models validating data structures across the codebase and with input and output
        Most important models are implemented as classes and have their own file: Script, Param

"""


import uuid
import datetime
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

class ScriptCodeCadLanguage(str,Enum):
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

#### IO MODELS ####

class InputScriptBase(BaseModel):
    format: str = 'step' # TODO: typing: step, stl, gltf etc.

