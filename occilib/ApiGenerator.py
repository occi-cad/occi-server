'''
    ApiGenerator.py
        Creates an endpoint for every given script

'''

from typing import List, Any
from enum import Enum

from fastapi import FastAPI, Depends
from pydantic import create_model, conint, constr
import logging

from .CadScript import CadScript
from .CadLibrary import CadLibrary
from .ModelRequestHandler import ModelRequestHandler
from .Param import ParamConfigBase, ParamConfigNumber, ParamConfigText, ParamConfigBoolean, ParamConfigOptions

from .models import ModelRequestInput

from .settings import params as PARAM_SETTINGS

class ApiGenerator:

    library = None
    request_handler:ModelRequestHandler = None
    script:List[CadScript] = []
    api = None
    api_tags = [] # open API tags
    

    def __init__(self, library:CadLibrary):

        self.library = library

        if isinstance(self.library, CadLibrary):
            self.request_handler = ModelRequestHandler(self.library)
        else:
            self.error('ApiGenerator::__init__(library): Please supply a library instance to this ApiGenerator')


    def get_api_tags(self, scripts:List[CadScript]):
        
        # generate endpoints per script model
        if scripts:
            for script in scripts:
                self._add_api_tags(script)
        
        return self.api_tags


    def generate_endpoints(self, api:FastAPI, scripts:List[CadScript]):

        self.api = api
        self.scripts = scripts

        # generate endpoints per script model

        if scripts:
            for script in scripts:
                self._generate_endpoint(script)


    def _generate_endpoint(self,script:dict):

        api = self.api

        # we generate specific input models that handle param names: bracket?width=10
        SpecificEndpointInputModel = self._generate_endpoint_input_model(script)
        
        # GET
        @api.get(f'/{script.org}/{script.name}', tags=[script.name])
        async def get_model_get(req:SpecificEndpointInputModel=Depends()): # see: https://github.com/tiangolo/fastapi/issues/318
            req.script_org = script.org
            req.script_name = script.name # this is important to identify the requested script
            return await self.request_handler.handle(req)

        @api.get(f'/{script.org}/{script.name}/versions', tags=[script.name]) # IMPORTANT: this route needs to be before '/{script.name}/{{version}}'
        async def get_model_get_versions(req:SpecificEndpointInputModel=Depends()): # see: https://github.com/tiangolo/fastapi/issues/318
            req.script_org = script.org
            req.script_name = script.name
            req.script_special_requested_entity = 'versions'
            return await self.request_handler.handle(req)

        @api.get(f'/{script.org}/{script.name}/{{version}}', tags=[script.name])
        async def get_model_get_version(version:str, req:SpecificEndpointInputModel=Depends()): # see: https://github.com/tiangolo/fastapi/issues/318
            req.script_org = script.org
            req.script_name = script.name
            req.script_version = version
            return await self.request_handler.handle(req)

    
        @api.get(f'/{script.org}/{script.name}/{{version}}/params', tags=[script.name])
        async def get_model_get_params(version:str, req:SpecificEndpointInputModel=Depends()): # see: https://github.com/tiangolo/fastapi/issues/318
            req.script_org = script.org
            req.script_name = script.name
            req.script_version = version
            req.script_special_requested_entity = 'params'
            return await self.request_handler.handle(req)

        @api.get(f'/{script.org}/{script.name}/{{version}}/presets', tags=[script.name])
        async def get_model_get_presets(version:str, req:SpecificEndpointInputModel=Depends()): # see: https://github.com/tiangolo/fastapi/issues/318
            req.script_org = script.org
            req.script_name = script.name
            req.script_version = version
            req.script_special_requested_entity = 'presets'
            return await self.request_handler.handle(req)

        # NOTE: Don't add copies of the above endpoints in POST for now. For clarity
        '''
        @api.post(f'/{script.name}', tags=[script.name])
        async def get_model_post(req:SpecificEndpointInputModel): # NOTE: POST needs no Depends()
            req.script_name = script.name # this is important to identify the requested script
            return await self.request_handler.handle(req)
        '''
            


    def _parse_script_dict(self, script:dict) -> CadScript:

        parsed_script = CadScript(**script)
        return parsed_script
    
    def _generate_endpoint_input_model(self, script:CadScript):

        """ 
            Dynamically generate a Pydantic Input model that is used to generate API endpoint 
            It extends the Base ModelRequestInput with flat Parameters defined in the Script instance
            In the defintion of the parameter query parameters type tests and default values are applied
        """

        BASE_EXEC_REQUEST = ModelRequestInput # this is the basic model for a Script exec request
        PARAM_TYPE_TO_PYTHON_TYPE = {
            'number' : float,
            'text' : str,
            'options' : str,
            'boolean' : bool,
        }
        
        fields = {} # dynamic pydantic field definitions

        for param in script.params.values():
            
            field_type = PARAM_TYPE_TO_PYTHON_TYPE.get(param.type)

            if field_type:
                field_def = self._param_to_field_def(param)
                fields[param.name] = (field_def, self._get_param_default(param) ) # here we plug the default value too

        # now make the Pydantic Input model definition
        EndpointInputModel = create_model(
            f'{script.name}Inputs', # for example BracketInputs
            **fields,
            __base__ = BASE_EXEC_REQUEST,
        )

        return EndpointInputModel
    
    def _get_param_default(self,param:ParamConfigBase) -> Any:
        """
            Get default value (if not given) for a specific type of param
        """
        if param.default is not None:
            return param.default
        
        # do some effort per param type
        if param.type == 'number':
            return param.start
        elif param.type == 'boolean':
            return False
        elif param.type == 'text':
            return 'mytext'
        elif param.type == 'options':
            return param.options[0]
        
        return None
        
    
    def _parse_param_dict(self, param:dict=None) -> ParamConfigBase:

        # NOTE: There is almost the same method in CadLibrary class - TODO: move method into utils

        PARAM_TYPE_TO_PYDANTIC_MODEL = {
            'number' : ParamConfigNumber,
            'text' : ParamConfigText,
            'boolean' : ParamConfigBoolean,
            'options' : ParamConfigOptions,
        }

        if param:
            PydanticModel = PARAM_TYPE_TO_PYDANTIC_MODEL.get(param.type)
            if PydanticModel:
                # parse dict with model
                return PydanticModel(**param)

        return None
        
    def _param_to_field_def(self, param:ParamConfigNumber|ParamConfigText): # TODO: typing
        """
            Convert Param to Pydantic Field Type for dynamic parameters
            See: https://docs.pydantic.dev/usage/types
        """
        if param.type == 'number':
            return conint(ge=param.start, le=param.end, multiple_of=param.step)
        elif param.type == 'text':
            return constr(strip_whitespace=True, 
                            strict=True, 
                            min_length=PARAM_SETTINGS['PARAM_INPUT_TEXT_MINLENGTH'], 
                            max_length=PARAM_SETTINGS['PARAM_INPUT_TEXT_MAXLENGTH'])
        elif param.type == 'boolean':
            return bool
        elif param.type == 'options':
            # create dynamic enum
            enum_kv = zip(param.options, param.options)
            class TempEnum(str, Enum):
                pass
            TypeEnum = TempEnum("TypeEnum", enum_kv)

            return TypeEnum
        

    def _add_api_tags(self, script:dict):

        self.api_tags.append({ 'name': script.name, **script.meta })

    def _setup_logger(self):

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(level=logging.INFO)

        try:
            handler = logging.StreamHandler()
            handler.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s %(name)s %(levelname)-4s %(message)s')
            handler.setFormatter(formatter)

            if (self.logger.hasHandlers()):  # see: http://tiny.cc/v5w6gz
                self.logger.handlers.clear()

            self.logger.addHandler(handler)

        except Exception as e:
            self.logger.error(e)

    


    
        
        



