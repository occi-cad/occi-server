'''
    ApiGenerator.py
        Creates an endpoint for every given script

'''

from typing import List
from fastapi import FastAPI, Depends
from pydantic import create_model, conint
import logging

from .CadScript import CadScript
from .CadLibrary import CadLibrary
from .ModelRequestHandler import ModelRequestHandler
from .Param import ParamConfigBase, ParamConfigNumber, ParamConfigText
from .models import ModelRequestInput


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
        
        # make both GET and POST endpoints
        @api.get(f'/{script.name}', tags=[script.name])
        async def get_model_get(req:SpecificEndpointInputModel=Depends()): # see: https://github.com/tiangolo/fastapi/issues/318
            
            # Main request handling
            req.script_name = script.name # this is important to identify the requested script
            req.return_format = 'model' # return model for GET requests
            
            result = await self.request_handler.handle(req)
            return result

        @api.post(f'/{script.name}', tags=[script.name])
        async def get_model_post(req:SpecificEndpointInputModel=Depends()):
            
            # Main request handling
            req.script_name = script.name # this is important to identify the requested script
            return self.request_handler.handle(req)

        



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
            'text' : str
            # TODO: more
        }
        
        fields = {} # dynamic pydantic field definitions

        for param in script.params.values():
            
            field_type = PARAM_TYPE_TO_PYTHON_TYPE.get(param.type)

            if field_type:
                field_def = self._param_to_field_def(param)
                fields[param.name] = (field_def, param.default or param.start ) # here we plug the default value too

        # now make the Pydantic Input model definition
        EndpointInputModel = create_model(
            f'{script.name}Inputs', # for example BracketInputs
            **fields,
            __base__ = BASE_EXEC_REQUEST,
        )

        return EndpointInputModel
    
    def _parse_param_dict(self, param:dict=None) -> ParamConfigBase:

        PARAM_TYPE_TO_PYDANTIC_MODEL = {
            'number' : ParamConfigNumber,
            'text' : ParamConfigText,
            # TODO: More types
        }

        if param:
            PydanticModel = PARAM_TYPE_TO_PYDANTIC_MODEL.get(param.type)
            if PydanticModel:
                # parse dict with model
                return PydanticModel(**param)

        return None
        
    def _param_to_field_def(self, param:ParamConfigNumber|ParamConfigText): # TODO: typing

        if param.type == 'number':
            return conint(ge=param.start, le=param.end, multiple_of=param.step)
        elif param.type == 'text':
            # TODO
            return None

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

    


    
        
        



