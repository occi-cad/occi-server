"""

    Param.py 

        Param Class containing param data and related methods

"""

from datetime import datetime
from typing import List, Any
from pydantic import BaseModel

from .models import ParamType, ModelUnits


class ParamBase(BaseModel):
    """
        Base Param class
    """
    id:str = None # instance id
    name:str = None # can be later set from Dict
    type:ParamType = None # type of Param like int, float, string
    default:Any = None # default value
    value:Any = None # active value of param
    description:str = None
    units:ModelUnits = None


class ParamNumber(ParamBase):
    """
        A number Param
    """
    start: float | int = 1
    end: float | int = 100
    step: float | int = 1

class ParamText(ParamBase):
    """
        A text Param
    """
    min_length:int = 0
    max_length:int = 255
    



    


    

