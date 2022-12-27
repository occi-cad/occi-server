""" 

    RequestHandler.py

    Handle a model request (with CadScript and CadScriptRequest) from API:
    1. Checking file system cache 
    2. Submitting the request to compute queue (RMQ)

"""

import logging
from fastapi import HTTPException
from typing import Dict
import celery

from .models import ModelRequestInput
from .Param import ParamConfigBase, ParamInstance
from .CadScript import CadScript
from .CadLibrary import CadLibrary

from .cqworker import compute_task



class ModelRequestHandler():

    library:CadLibrary
    cur_request:CadScript
    celery_connected:bool = False

    def __init__(self, library:CadLibrary):
            
        self._setup_logger()
        self.library = library

        if not isinstance(self.library, CadLibrary):
            self.logger.error('ModelRequestHandler::__init__(library): Please supply library!') 

        if self.check_celery() is False:
            self.logger.error('ModelRequestHandler::__init__(library): Celery is not connected. We cannot send requests to compute! Check .env config.') 
        

    def check_celery(self) -> bool:

        try:
            celery.current_app.control.inspect().ping()
            self.celery_connected = True
            return self.celery_connected
        except Exception as e:
            return False

    def handle(self, req:ModelRequestInput):
        """
            Handle request coming from API
            Prepare a full CadScript instance with request in it
            and get from cache or submit to compute workers
        """

        if req is None or not isinstance(req, ModelRequestInput):
            m = 'ModelRequestHandler::handle(script): No request received'
            self.logger.error(m)
            raise HTTPException(500, detail=m) # raise http exception to give server error

        requested_script = self._req_to_script_instance(req)
        requested_script.hash() # set hash based on params

        cached_script = self.library.get_cached(requested_script)
        if cached_script:
            # TODO: output_format: model or full
            return cached_script
        else:
            # no cache: submit to workers
            if self.celery_connected:
                compute_task.apply_async(script=requested_script)
            else:
                # local debug
                return requested_script
    

    def _req_to_script_instance(self,req:ModelRequestInput) -> CadScript:

        if not isinstance(req, ModelRequestInput):
            raise HTTPException(500, detail='ModelRequestHandler::_req_to_script_instance(req): No request given!') # raise http exception to give server error
        if not isinstance(self.library, CadLibrary):
            raise HTTPException(500, detail='ModelRequestHandler::_req_to_script_instance(req): No library loaded. Cannot handle request!') # raise http exception to give server error

        script = self.library.get_script(req.script_name)

        if not script:
            raise HTTPException(500, detail=f'ModelRequestHandler::_req_to_script_instance(req): Cannot get script "{req.script_name}" from library!')

        # in req are also the flattened requested param values
        filled_params:Dict[str,ParamInstance] = {} 
        
        if script.params:
            for name, param in script.params.items():
                related_filled_param = getattr(req, name, None)
                if related_filled_param:
                    filled_params[name] = ParamInstance(value=related_filled_param)

            script.request.params = filled_params
            
            return script

        return None

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
