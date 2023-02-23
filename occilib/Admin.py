'''
    Admin.py
        Extends OCCI api with administration functions like:
        - publish/unpublish
        - basic edits for example of description, author, name, params

    Entities:
     - PublishRequest: The request for publication of a given CadScript. Return status and reference to new CadScript and PublicationJob
     - PublishJob: the process of publication including pre-calculation of which the user can ask the status and progress

    Endpoints:
    - /admin/publish - main endpoint to publish a script
    - /admin/publish/{{PublicationJob ID}} - status of PublicationJob
    - /admin/unpublish/{{CadScript ID}} -  
        
'''

import logging
import uuid
from datetime import datetime
from enum import Enum

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .CadScript import CadScript
from .ApiGenerator import ApiGenerator

#### ADMIN MODELS ####

class PublishRequest(BaseModel):
    pre_calculate:bool=False # request a pre-compute of all models
    script:CadScript=None # the script you want to publish

class JobStatus(str,Enum):
    success = 'success'
    error = 'error'

class PublishJob(BaseModel):
    id:str = uuid.uuid4()
    created_at:datetime = datetime.now()
    updated_at:datetime = datetime.now()
    script:CadScript
    status:JobStatus = None
    pre_calculated:int = 0
    pre_calculation_total:int = None


#### ADMIN CLASS ####

class Admin:

    #### SETTINGS ####
    SCRIPT_ORG_MIN_CHARS = 4
    SCRIPT_NAME_MIN_CHARS = 4
    SCRIPT_CODE_MIN_CHARS = 10

    #### END SETTINGS ####

    api:FastAPI = None # reference to FastAPI app instance

    def __init__(self, api:FastAPI=None, api_generator:ApiGenerator=None):

        self._setup_logger()

        if not isinstance(api, FastAPI):
            self.logger.error('Please supply a reference to FastAPI app instance!')
        elif not isinstance(api_generator, ApiGenerator):
            self.logger.error('Please supply a reference to OCCI ApiGenerator!')
        else:
            self.api = api
            self._add_admin_endpoints()

        
    def _add_admin_endpoints(self):

        if self.api is None:
            self.logger.error('Cannot add admin endpoints without reference to FastAPI app!')
        else:
            api = self.api
            # /admin/publish
            @api.post('/admin/publish')
            async def publish(req:PublishRequest):
                self._handle_publish_request(req)
                return req
            # /admin/publish/{job_id}
            @api.get('/admin/publish/{job_id}')
            async def get_pub_job(job_id:int):
                return job_id
            # /admin/unpublish
            @api.post('/admin/unpublish/{script_id:int}')
            async def unpublish(script_id:int):
                return script_id
    
    def _handle_publish_request(self, req:PublishRequest) -> PublishJob:
        """ 
            Handles a request to publish a given script

            1. Do the needed checks around unique namespaces
            2. Save the script in OCCI library on disk
            3. Report back to the API user about the PublishJob
            4. If needed (and possible) start pre-calculation of models into cache

        """

        if self._check_publish_request(req):
            pass
        


    def _check_publish_request(self, req:PublishRequest) -> bool: # or None if everything checks out

        if req is None:
            raise HTTPException(status_code=400, detail="Compute task not found or in error state. Please go back to original request url!")
        if req.script is None: 
            raise HTTPException(status_code=400, detail='Please supply a script to be published')
        if req.script.get_namespace() is None:
            raise HTTPException(status_code=400, detail='Make sure your script has a valid namespace. Set "org" and "name" fields!')
        if len(req.script.org) < self.SCRIPT_ORG_MIN_CHARS:
            raise HTTPException(status_code=400, detail=f'The "org" field of your script is too short. Minimum is {self.SCRIPT_ORG_MIN_CHARS}')
        if len(req.script.name) < self.SCRIPT_NAME_MIN_CHARS:
            raise HTTPException(status_code=400, detail=f'The "name" field of your script is too short. Minimum is {self.SCRIPT_NAME_MIN_CHARS}')
        if req.script.code is None or len(req.script.code) < self.SCRIPT_CODE_MIN_CHARS:
            raise HTTPException(status_code=400, detail=f'Your script contains no field "code" or too little code. Is this a real model? Minimum is {self.SCRIPT_CODE_MIN_CHARS}')
        
        # fill in some data
        req.script.namespace = req.script.get_namespace()
        
        return True


    #### CLASS UTILS ####
        
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