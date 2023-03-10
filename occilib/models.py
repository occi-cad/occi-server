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
    boolean = 'boolean'
    text = 'text'
    options = 'options'
    

class EndpointStatus(str,Enum):
    success = 'success'
    working = 'working'
    error = 'error'

class ModelUnits(str, Enum):
    mm = 'mm'
    cm = 'cm'
    dm = 'dm'
    m = 'm'
    inch = 'inch'
    foot = 'foot'
    mile = 'mile'


class ModelContentLicense(str, Enum):
    # see: https://library.macewan.ca/services/3d-printing/licensing-and-copyright-for-3d-prints
    copyright = 'copyright' # The script and model are copyrighted material. Don't reuse without an agreement from the creator
    trademarked = 'trademarked' # The script and model are copyrighted and trademarked material. Don't reuse without an agreement from the creator
    CC_BY = 'CC_BY' # This license allows reusers to distribute, remix, adapt, and build upon the material in any medium or format, so long as attribution is given to the creator. The license allows for commercial use.',
    CC_BY_SA = 'CC_BY_SA' # This license allows reusers to distribute, remix, adapt, and build upon the material in any medium or format, so long as attribution is given to the creator. The license allows for commercial use. If you remix, adapt, or build upon the material, you must license the modified material under identical terms.',
    CC_BY_NC = 'CC_BY_NC' # This license allows reusers to distribute, remix, adapt, and build upon the material in any medium or format for noncommercial purposes only, and only so long as attribution is given to the creator.',
    CC_BY_NC_SA = 'CC_BY_NC_SA' # 'This license allows reusers to distribute, remix, adapt, and build upon the material in any medium or format for noncommercial purposes only, and only so long as attribution is given to the creator. If you remix, adapt, or build upon the material, you must license the modified material under identical terms.',
    CC_BY_ND = 'CC_BY_ND' # 'This license allows reusers to copy and distribute the material in any medium or format in unadapted form only, and only so long as attribution is given to the creator. The license allows for commercial use.',
    CC_BY_NC_ND = 'CC_BY_NC_ND' # 'This license allows reusers to copy and distribute the material in any medium or format in unadapted form only, for noncommercial purposes only, and only so long as attribution is given to the creator.',
    CC0 = 'CC0' # (aka CC Zero) is a public dedication tool, which allows creators to give up their copyright and put their works into the worldwide public domain. CC0 allows reusers to distribute, remix, adapt, and build upon the material in any medium or format, with no conditions.',


class ScriptCadLanguage(str,Enum):
    cadquery = 'cadquery'
    archiyou = 'archiyou'
    openscad = 'openscad' # Not yet supported

class ModelFormat(str,Enum):
    """ Also the extension """
    step = 'step'
    gltf = 'gltf'
    stl = 'stl'

class ModelQuality(str,Enum): # TODO: not yet used
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
    script_org:str = None # always lowercase
    script_name:str = None # always lowercase
    script_version:str = None
    script_special_requested_entity:str = None # requested entity: None=script, versions, params, presets
    format: ModelFormat = 'step'
    output:RequestResultFormat = 'model' # The way to output. Either just a model (default) or the full CadScriptResult with the specific format
    # params:dict = {} # { param_name: value } NOTE: only used now for pre-calculating cache - but can also be used in API later
    # !!! params are added on runtime by name !!!

    def get_param_query_string(self) -> str:

        query_key_vals = []
        for k,v in self.dict().items():
            if 'script_' not in k: # a hacky way to avoid the internal properties
                query_key_vals.append(f'{k}={v}')
        
        return '?' + '&'.join(query_key_vals)


class ModelResult(BaseModel):
    id:str = None # name + param hash = instance hash
    success:bool = False
    task_id:str = None # set id of Celery task here
    request_id:str = None
    models:dict = {} # TODO Output models by format
    errors:List[Any] = []# TODO
    messages:List[Any] = [] # TODO
    tables:Any = [] # TODO
    duration:int = None # in ms

class SearchQueryInput(BaseModel):
    q:str = None