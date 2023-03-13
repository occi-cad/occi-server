"""

    Param.py 

        Param Class containing param data and related methods

"""

from typing import List, Any
from pydantic import BaseModel
import numpy

from .models import ParamType, ModelUnits

class ParamInstance(BaseModel): 
    """
        Instances of Params used in CadScript.request.params
        Will be outputted in dict with key:name and value the ParamInstance
    """
    value:Any = None # active value of param

class ParamConfigBase(BaseModel):
    """
        Base Param class
        Used in as config
    """
    name:str = None # can be later set from Dict
    label:str = None # optional: Clean name for name of parameter in configurator (Not yet supported in FreeCad plugin)
    type:ParamType = None # type of Param like int, float, string
    default:Any = None # default value
    description:str = None
    units:ModelUnits = None
    iterable:bool = True # if not, set in subclass


class ParamConfigNumber(ParamConfigBase):
    """
        A number Param
    """
    type:ParamType = 'number'
    start: float | int = 1
    end: float | int = 100
    step: float | int = 1

    # TODO: We can also define an iterator for less memory usage?
    def values(self) -> List[int|float]:
        return numpy.arange(self.start, self.end+self.step, self.step).tolist()
        
class ParamConfigBoolean(ParamConfigBase):
    """
        a boolean Param
    """
    type:ParamType = 'boolean'


class ParamConfigText(ParamConfigBase):
    """
        A text Param
    """
    type:ParamType = 'text'
    min_length:int = 0
    max_length:int = 255
    iterable = False

class ParamConfigOptions(ParamConfigBase):
    """
        A options Param which offers a list of strings for the user to choose from
    """
    type:ParamType = 'options'
    options:List[str] = []
    iterable = True
    
    def values(self) -> List[str]:
        return self.options
    


    


    

