"""

    CadScript.py 

        Script Class containing script data and related methods
        We use pydantic for strict validation

"""

from datetime import datetime
from typing import List, Any, Dict
from pydantic import BaseModel
import hashlib
import base64
import json

from .models import ScriptCadLanguage, ModelResult, ModelFormat, ModelQuality
from .Param import ParamConfigBase, ParamConfigNumber, ParamConfigText

class ModelRequest(BaseModel):
    """
        Request to execute CadScript with given params and output form
    """
    hash:str = None # name+param+values hash id
    params: Dict[str, ParamConfigBase] = {}
    format: ModelFormat = 'step' # requested output format of the model
    quality: ModelQuality = 'high'
    meta: dict = {} # TODO

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
    params:Dict[str, ParamConfigBase | ParamConfigNumber | ParamConfigText] = {} # list of param definitions - TODO: combine ParamTypes
    parameter_presets:Dict[str, Dict[str, ParamConfigNumber|ParamConfigText]] = {} # TODO: presets of parameters by variant name
    code: str  = None# the code of the CAD component
    script_cad_language:ScriptCadLanguage = None # cadquery, archiyou or openscad (and many more may follow)
    script_cad_version:str = None # not used currently
    meta:dict = None # TODO: Remove? Generate tag for FastAPI on the fly
    request:ModelRequest = ModelRequest() # just make an empty ModelRequest instance
    results:ModelResult = None

    def hash(self) -> str:

        if not self.request:
            self.logger.error('CadLibrary::hash(script): This CadScript is not an instance. We need request attribute too!')
            return None
        
        params_str = ''
        if self.request.params and len(self.request.params.keys()) > 0:
            for name,param in self.request.params.items():
                params_str += f'{name}={json.dumps(dict(param))}&'
        
        self.request.hash = self._hash(self.name + params_str)
        return self.request.hash

        
    def _hash(self, inp:str) -> str:
        # TODO: research this hash function!
        HASH_LENGTH_TRUNCATE = 11
        return base64.urlsafe_b64encode(hashlib.md5(inp.encode()).digest())[:HASH_LENGTH_TRUNCATE].decode("utf-8")










    


    

