"""

    CadScript.py 

        Script Class containing script data and related methods
        We use pydantic for strict validation

"""

from datetime import datetime
from typing import List, Any, Dict, Tuple, Iterator
from pydantic import BaseModel
import hashlib
import base64
import json
import itertools

from .models import ScriptCadLanguage, ModelContentLicense, ModelResult, ModelFormat, ModelQuality, RequestResultFormat, ModelUnits, EndpointStatus
from .Param import ParamConfigBase, ParamConfigNumber, ParamConfigText, ParamInstance


class ModelRequest(BaseModel):
    """
        Request to execute CadScript with given params and output form
    """
    created_at:datetime = datetime.now()
    hash:str = None # name+param+values hash id
    params: Dict[str, ParamInstance] = {}
    format: ModelFormat = 'step' # requested output format of the model
    output: RequestResultFormat = None
    quality: ModelQuality = 'high' # TODO
    batch_id: str = None # some id to group requests 
    meta: dict = {} # TODO
    

    def get_param_query_string(self) -> str:
        '''
            Generate the GET parameters string 
            example: ?format=step&output=full&width=100
        '''
        query_param_values = []
        for param_name, param_instance in self.params.items():
            query_param_values.append = f'{param_name}={param_instance.value}'

        query_param_values_string = '&' + '&'.join(query_param_values) if len(query_param_values) > 0 else ''

        return f'?format={self.format}&output={self.output or "model"}{query_param_values_string}'



class CadScript(BaseModel):
    """ 
    A script containing a CAD component with information on inputs and code cad language
    the different steps of CADScript handling: parsing, compute request, compute and results

    """
    id:str = None # unique id for this script {org}/{name}/{version}
    namespace:str = None # unique endpoint namespace {org}/{name}
    status:EndpointStatus = 'success'
    org:str = None
    name:str # always lowercase
    author:str = None
    license:ModelContentLicense = None
    version:str = None
    url:str = None # url of the endpoint where the script can be found
    description:str = None 
    created_at:datetime = datetime.now()
    updated_at:datetime = datetime.now()
    prev_version:str = None
    safe:bool = False # if validated as safe code
    published:bool = True # if available to the public
    units:ModelUnits = None
    params:Dict[str, ParamConfigBase | ParamConfigNumber | ParamConfigText] = {} # list of param definitions - TODO: combine ParamTypes
    param_presets:Dict[str, dict] = {} # TODO: presets of parameters by name and then a { param_name: value } dict
    code: str  = None# the code of the CAD script
    script_cad_language:ScriptCadLanguage = None # cadquery, archiyou or openscad (and many more may follow)
    script_cad_version:str = None # not used currently
    script_cad_engine_config:dict = None # plug all kind of specific script cad engine config in here
    meta:dict = {} # TODO: Remove? Generate tag for FastAPI on the fly

    def hash(self, params: Dict[str, ParamInstance]=None) -> str:
        """
            Hash a given dict of ParamInstance parameters. 
            If not given we check if self is a CadScriptRequest and has request.params and use that
        """
        
        # if params is not given we try to get is from the script.request
        if params is None:
            if not hasattr(self, 'request'):
                self.logger.error('CadScript::hash(): Cannot get script hash because it has no request with parameter values yet!')
                return None
            if self.request is None:
                self.logger.error('CadLibrary::hash(script): This CadScript is not an instance. We need request attribute too!')
                return None

            params = self.request.params

        # NOTE: params can be None if no parameters
        params_str = ''
        if params and len(params.keys()) > 0:
            for name,param in params.items():
                params_str += f'{name}={json.dumps(dict(param))}&'
        
        hash = self._hash(self.name + params_str)
        
        # set hash on request too (if available)
        if hasattr(self, 'request'):
            self.request.hash = hash

        return hash


    def _hash(self, inp:str) -> str:
        # TODO: research this hash function!
        HASH_LENGTH_TRUNCATE = 11
        return base64.urlsafe_b64encode(hashlib.md5(inp.encode()).digest())[:HASH_LENGTH_TRUNCATE].decode("utf-8")

    def is_cachable(self) -> bool:
        """
            Return if the script is cachable by assessing its parameter configuration
        """
        for name,param in self.params.items():
            if param.iterable is False:
                return False
        return True

    
    def all_possible_model_params_dicts(self) -> Dict[str,dict]: # dict[model_hash, dict]
        """
            Get the parameter sets (in {'param_name':value} format) of all possible parametric models
            Also return the model hash in key
            Resulting return data: { 'hash1' : { param_name: value, {..} }, 'hash2' : {...}}
            !!!! IMPORTANT: Can be slow !!!!
        """

        if self.is_cachable() is False:
            return {}

        all_values_per_parameter = []
        for param in self.params.values():
            all_values_per_parameter.append(param.values())

        all_combinations = list(itertools.product(*all_values_per_parameter))
        """ the combinations are generated from the starting value 
            and then iterated from the last list to the first
            
            Example: 
            - param1: [1,2,3,4,5]
            - param2: [10,11,12]
            combinations:
                [[1,10],[1,11],[1,12],[2,10],[2,11],[2,12] etc] 
        """

        all_model_param_sets = {}

        for combination in all_combinations:
            param_values = {}
            for index,value in enumerate(combination):
                param_name = list(self.params.values())[index].name
                param_values[param_name] = value

            # place with hash 
            # convert to Dict[ParamInstance] # TODO: remove this in between step eventually
            param_set:Dict[Dict[ParamInstance]] = {}
            for k,v in param_values.items():
                param_set[k] = ParamInstance(value=v)

            param_set_hash = self.hash(param_set)
            all_model_param_sets[param_set_hash] = param_values

        return all_model_param_sets
                    
    
    def iterate_possible_model_params_dicts(self) -> Iterator[Tuple[str, dict]]: # hash, { param1: { value: x }}

        '''
            Iterator over all combinations of param values
        '''

        all_values_per_parameter = []
        for param in self.params.values():
            all_values_per_parameter.append(param.values())

        for combination in itertools.product(*all_values_per_parameter):
            param_values = {}
            for index,value in enumerate(combination):
                param_name = list(self.params.values())[index].name
                param_values[param_name] = value

            # convert to Dict[ParamInstance] # TODO: remove this in between step eventually
            param_set:Dict[Dict[ParamInstance]] = {}
            for k,v in param_values.items():
                param_set[k] = ParamInstance(value=v)

            param_set_hash = self.hash(param_set)
            yield param_set_hash, param_values

    def get_num_variants(self) -> int:

        '''
            Get total number of variants for this script:
            All possible values of every parameter (NVP..NVPn)
            num variants = NVP1 * NVP2 * ... NVPN
        '''

        num_combinations = 1
        for param_obj in self.params.values():
            num_combinations *= len(param_obj.values())

        return num_combinations

        

class CadScriptRequest(CadScript):
    """
        CadScript that is used to make a request
    """
    
    request:ModelRequest = ModelRequest() # just make an empty ModelRequest instance

    def get_param_values_dict(self) -> dict:
        """
             Convert param values to Dict
             request.params is in { name: { value: 'some value' }} format
        """
        if self.request and type(self.request.params) is dict:
            
            param_values:dict = {}
            for k,v in self.request.params.items():
                param_values[k] = v.value

            return param_values


class ModelComputeJob(BaseModel):
    status:EndpointStatus = 'working'
    celery_task_id:str = None
    celery_task_status:str = None
    script:CadScriptRequest = None
    elapsed_time:int = None # in seconds


class CadScriptResult(CadScriptRequest):
    """
        CadScript that has been through compute and has results
    """
    results:ModelResult = ModelResult()
    




