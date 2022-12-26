'''
    ApiGenerator.py
        Creates an endpoint for every given script

'''

from ast import parse
from typing import List
from fastapi import FastAPI, Depends
from .CadScript import CadScript
from .Param import ParamBase, ParamNumber, ParamText
from .models import InputScriptBase
from pydantic import create_model, conint

class ApiGenerator:

    def __init__(self):

        self.api = None
        self.scripts = None
        self.api_tags = [] # open API tags

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

        EndpointInputModel = self._generate_endpoint_input_model(script)
        
        # make both GET and POST endpoints
        @api.get(f'/{script.name}', tags=[script.name])
        async def get_component_get(params:EndpointInputModel=Depends()): # see: https://github.com/tiangolo/fastapi/issues/318
            return {
                'status' : 'FAKE EXECUTED',
                'script' : dict(script),
                'format': params.format
            }

        @api.post(f'/{script.name}', tags=[script.name])
        async def get_component_post(params:EndpointInputModel):
            return {
                'status' : 'FAKE EXECUTED',
                'script' : dict(script),
            }



    def _parse_script_dict(self, script:dict) -> CadScript:

        parsed_script = CadScript(**script)
        return parsed_script
    
    """ Dynamically generate a Pydantic Input model that is used to generate API endpoint 
            It extends the Base ScriptExecRequest with Parameters defined in the Script instance
    """
    def _generate_endpoint_input_model(self, script:CadScript):

        PARAM_TYPE_TO_PYTHON_TYPE = {
            'number' : float,
            'text' : str
            # TODO: more
        }
        BASE_EXEC_REQUEST = InputScriptBase
    
        fields = {} # dynamic pydantic field definitions

        for param in script.params.values():
            
            field_type = PARAM_TYPE_TO_PYTHON_TYPE.get(param.type)

            if field_type:
                field_def = self._param_to_field_def(param)
                fields[param.name] = (field_def, param.default )

        # now make the Pydantic Input model definition
        EndpointInputModel = create_model(
            f'{script.name}Inputs', # for example BracketInputs
            **fields,
            __base__ = InputScriptBase,
        )

        return EndpointInputModel
    
    def _parse_param_dict(self, param:dict=None) -> ParamBase:

        PARAM_TYPE_TO_PYDANTIC_MODEL = {
            'number' : ParamNumber,
            'text' : ParamText,
            # TODO: More types
        }

        if param:
            PydanticModel = PARAM_TYPE_TO_PYDANTIC_MODEL.get(param.type)
            if PydanticModel:
                # parse dict with model
                return PydanticModel(**param)

        return None
        
    def _param_to_field_def(self, param:ParamNumber|ParamText): # TODO: typing

        if param.type == 'number':
            return conint(ge=param.start, le=param.end, multiple_of=param.step)
        elif param.type == 'text':
            # TODO
            return None

    def _add_api_tags(self, script:dict):

        self.api_tags.append({ 'name': script.name, **script.meta })


    


    
        
        



