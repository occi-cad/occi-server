"""

    CadScript.py 

        Script Class containing script data and related methods
        We use pydantic for strict validation

"""

from datetime import datetime
from typing import List, Any, Dict
from pydantic import BaseModel

from .models import ScriptCodeCadLanguage, ModelFormat,ModelQuality
from .Param import ParamBase,ParamNumber

class CadScriptRequest(BaseModel):
    """
        Request to execute CadScript with given params and output form
    """
    id:str # runtime instance id
    params: List[ParamBase]
    format: ModelFormat # requested output format of the model
    quality: ModelQuality
    meta: dict # TODO


class CadScript(BaseModel):
    """ 
    A script containing a CAD component with information on inputs and code cad language
    the different steps of CADScript handling: parsing, compute request, compute and results

    """
    id:str = None # runtime instance id
    name:str
    author:str = None
    org:str = None
    description:str = None 
    created_at:datetime = datetime.now()
    updated_at:datetime = datetime.now()
    version:str = None
    prev_version:str = None
    safe:bool = False # if validated as safe code
    published:bool = True # if available to the public
    params:Dict[(str, ParamBase | ParamNumber)] = {} # list of param definitions
    code: str  = None# the code of the CAD component
    codecad_language:ScriptCodeCadLanguage = None # cadquery, archiyou or openscad (and many more may follow)
    codecad_version:str = None # not used currently
    request:CadScriptRequest = None
    meta:dict = None # TODO: Remove? Generate tag for FastAPI on the fly


class CadExecution(BaseModel):
    request_id:str # refers back to CadScriptRequest instance
    models:dict # TODO Output models by format
    errors:List[Any] = []# TODO
    messages:List[Any] = [] # TODO
    tables:Any # TODO
    duration:int # in ms
    






    


    

