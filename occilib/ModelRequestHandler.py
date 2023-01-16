""" 

    RequestHandler.py

    Handle a model request (with CadScriptRequest) from API:
    1. Checking file system cache 
    2. Submitting the request to compute queue (RMQ)

"""

import time
import logging
from fastapi import HTTPException
from fastapi.responses import RedirectResponse, JSONResponse, FileResponse

from typing import Dict, Any

import asyncio
from asgiref.sync import sync_to_async
import nest_asyncio # see:  https://github.com/erdewit/nest_asyncio
from contextlib import suppress

import celery
from celery.result import AsyncResult

from .models import ModelRequestInput
from .Param import ParamConfigBase, ParamInstance
from .CadScript import CadScriptRequest, CadScriptResult
from .CadLibrary import CadLibrary

from .cqworker import compute_job_cadquery
#from .aycomputetask import compute_job_archiyou

nest_asyncio.apply() # enables us to plug into running loop of FastApi

class ModelRequestHandler():

    #### SETTINGS ####
    WAIT_FOR_COMPUTE_RESULT_UNTILL_REDIRECT = 3
    REDIRECTING_COMPUTING_STATE = 'status'

    #### END SETTINGS

    library:CadLibrary
    celery_connected:bool = False

    def __init__(self, library:CadLibrary):
            
        self._setup_logger()
        self.library = library

        if not isinstance(self.library, CadLibrary):
            self.logger.error('ModelRequestHandler::__init__(library): Please supply library!') 

        if self.check_celery() is False:
            self.logger.error('ModelRequestHandler::__init__(library): Celery is not connected. We cannot send requests to compute! Check .env config.') 
        else:
            self.logger.info('ModelRequestHandler::__init__(library): Celery is connected to RMQ succesfully!')
            # self._set_celery_routing() # DEBUG FIRST!
        

    def check_celery(self) -> bool:

        try:
            celery.current_app.control.inspect().ping()
            self.celery_connected = True
            return self.celery_connected
        except Exception as e:
            return False

    def _set_celery_routing(self):

        celery.current_app.task_routes = ([
            {'cadquery.*': {'queue': 'cadquery'}},
            #{'archiyou.*': {'queue': 'archiyou'}}
        ])

    def get_celery_task_method(self, requested_script:CadScriptRequest) -> Any: # TODO: nice typing

        TASK_METHODS_BY_ENGINE = {
            'cadquery' : compute_job_cadquery, 
            #'archiyou' : compute_job_archiyou,
        }
        DEFAULT_ENGINE = 'cadquery'

        task_method = TASK_METHODS_BY_ENGINE.get(requested_script.script_cad_language)
        if task_method is None:
            self.logger.error(f'ModelRequestHandler::get_celery_task_method: Cannot get Celery task method: script_cad_language "{requested_script.script_cad_language}" is unknown! Defaulted to "cadquery"')
            task_method = TASK_METHODS_BY_ENGINE[DEFAULT_ENGINE]
        
        return task_method


    async def handle(self, req:ModelRequestInput) -> RedirectResponse | JSONResponse | FileResponse:
        """
            Handle request coming from API
            Prepare a CadScriptRequest instance with request in it
            and get from cache or submit to compute workers
        """

        if req is None or not isinstance(req, ModelRequestInput):
            m = 'ModelRequestHandler::handle(script): No request received'
            self.logger.error(m)
            raise HTTPException(500, detail=m) # raise http exception to give server error

        requested_script = self._req_to_script_request(req)
        requested_script.hash() # set hash based on params

        if self.library.is_cached(requested_script):
            self.logger.info(f'**** {requested_script.name}: CACHE HIT FOR REQUEST [format="{req.format}" output="{req.output}"] ****')
            # API user requested a full CadScriptResult response
            if requested_script.request.output == 'full':
                cached_script = self.library.get_cached_script(requested_script)
                return cached_script
            else:
                # only a specific format model as output (we skip loading the result.json and serve the model file directly)
                return self.library.get_cached_model(requested_script)


        else:
            # no cache - but already computing?
            self.logger.info(f'**** {requested_script.name}: COMPUTE ****')

            computing_task_id = self.library.check_script_model_is_computing(requested_script.name, requested_script.hash())
            if computing_task_id:
                # refer back to compute url
                return self.go_to_computing_url(requested_script,computing_task_id, set_compute_status=False)
            else:
                # no cache: submit to workers
                if self.celery_connected:
                    task:AsyncResult = self.get_celery_task_method(requested_script).apply_async(args=[], kwargs={ 'script' : requested_script.json() })
                    result_or_timeout = self.start_compute_wait_for_result_or_redirect(task)

                    # wait time is over before compute could finish:
                    if result_or_timeout is None:
                        return self.go_to_computing_url(requested_script, task.id)
                    else:
                        # we got a compute result in time to respond directly to the API client
                        script_result:CadScriptResult = result_or_timeout
                        if script_result.results.success is True:
                            return self.library.checkin_script_result_in_cache_and_return(script_result)
                        else:
                            errors_str = ','.join(script_result.results.errors)
                            raise HTTPException(status_code=404, 
                                detail=f"""Error executing the script '{script_result.name}':'{errors_str}'\nPlease notify the OCCI library administrator!""")
                else:
                    # local debug
                    self.logger.warn('ModelRequestHandler::handle(): Compute request without celery connection. You are probably debugging?')
                    return requested_script

    def start_compute_wait_for_result_or_redirect(self, task:AsyncResult, wait_time:int=None) -> CadScriptResult: # time in seconds
        """
            Async wait for a given number of seconds T
            if t < T return compute result directly to API client 
            otherwise redirect to computing url
            
            inspired by: https://stackoverflow.com/questions/53967281/what-would-be-promise-race-equivalent-in-python-asynchronous-code
        """

        wait_time = wait_time or self.WAIT_FOR_COMPUTE_RESULT_UNTILL_REDIRECT

        def coro_is_wait(coro):
            return '.wait' in str(coro) # TODO: not really robust, make this better

        # simple async waiting
        async def wait(t):
            await asyncio.sleep(t)
            self.logger.warn(f'ModelRequestHandler::start_compute_wait_for_result_or_redirect: Wait for direct compute result elapsed: {t} seconds!')
            return None

        loop = asyncio.get_running_loop()
        racing_tasks = set()
        racing_tasks.add(loop.create_task(wait(wait_time)))
        racing_tasks.add(loop.create_task(self.result_to_async(task)()))

        done_first, pending = loop.run_until_complete(asyncio.wait(racing_tasks, return_when=asyncio.FIRST_COMPLETED))
        
        """
            !!!
            TODO: DEBUG this message:
            RuntimeError: Cannot enter into task <Task pending name='Task-1' coro=<Server.serve() running at /usr/local/lib/python3.10/site-packages/uvicorn/server.py:80> wait_for=<Future finished result=None> cb=[_run_until_complete_cb() at /usr/local/lib/python3.10/asyncio/base_events.py:184, WorkerThread.stop()]> while another task <Task pending name='Task-4' coro=<RequestResponseCycle.run_asgi() running at /usr/local/lib/python3.10/site-packages/uvicorn/protocols/http/h11_impl.py:407> cb=[set.discard()]> is being executed.
            It mostly happens the first request
            The nested coroutine is blocking the main FastAPI loop? 
            This might mean that the API does block the period of waiting for compute result
        """
        result = None
        for coro in done_first: # in theory there could be more routines, but probably either wait or compute result
            try:
                # return the first
                result = coro.result()
            except TimeoutError:
                return None
        
        # continue the other task (can be the compute routine or the wait)
        for pending_coro in pending:
            if coro_is_wait(pending_coro): # TODO: not really robust, make this better
                # for the record: cancel the wait coroutine and block further errors
                pending_coro.cancel()
                with suppress(asyncio.CancelledError):
                    loop.run_until_complete(pending_coro)
            else:
                # continue the compute routine
                loop.run_until_complete(pending_coro) # this is needed to continue running the task for some reason
        
        if result is not None:
            script_result = CadScriptResult(**result) # convert dict result to CadScriptResult instance

        return script_result

    
    def result_to_async(self, task:AsyncResult): 
        """
            Current Celery (v5) does not support asyncio just yet. See: https://github.com/celery/celery/issues/6603
            We use asgiref.sync_to_async to turn AsyncResult.get() into a async method
            asgiref uses threads (see: https://github.com/django/asgiref/blob/main/asgiref/sync.py)
        """
        async def wrapper(*args, **kwargs):
            compute_result:CadScriptResult = await sync_to_async(task.get,thread_sensitive=True)() # includes results. thread_sensitive is needed!
            return compute_result
        return wrapper

    def go_to_computing_url(self, script:CadScriptRequest, task_id:str, set_compute_status:bool=True) -> RedirectResponse:
        """
            When compute result takes longer then WAIT_FOR_COMPUTE_RESULT_UNTILL_REDIRECT
            Redirect to compute status url which the user can query untill the compute task is done 
            and then automatically gets redirected
        """
        if set_compute_status:
            self.library.set_script_model_is_computing(script, task_id)

        return RedirectResponse(f'{script.name}/{script.hash()}/{self.REDIRECTING_COMPUTING_STATE}')


    def _req_to_script_request(self,req:ModelRequestInput) -> CadScriptRequest:

        if not isinstance(req, ModelRequestInput):
            raise HTTPException(500, detail='ModelRequestHandler::_req_to_script_request(req): No request given!') # raise http exception to give server error
        if not isinstance(self.library, CadLibrary):
            raise HTTPException(500, detail='ModelRequestHandler::_req_to_script_request(req): No library loaded. Cannot handle request!') # raise http exception to give server error

        script_request = self.library.get_script_request(req.script_name)

        if not script_request:
            raise HTTPException(500, detail=f'ModelRequestHandler::_req_to_script_request(req): Cannot get script "{req.script_name}" from library!')

        script_request.request.format = req.format
        script_request.request.output = req.output # set format in which to return to API (full=json, model return results.models[{format}])
        
        # in req are also the flattened requested param values
        # TODO: we will also enable using params={ name: val } in POST requests
        filled_params:Dict[str,ParamInstance] = {} 
        
        if script_request.params:
            for name, param in script_request.params.items():
                related_filled_param = getattr(req, name, None)
                if related_filled_param:
                    filled_params[name] = ParamInstance(value=related_filled_param)

            script_request.request.params = filled_params

        # NOTE: script can also have no parameters!    
        return script_request

    def param_dict_to_param_instance(self, param_dict:dict) -> ParamInstance:

        params:Dict[str,ParamInstance] = {}
        for k,v in param_dict.items():
            params[k] = ParamInstance(value=v)

        return params


    #### CACHE PRE-CALCULATION ####

    async def compute_script_request(self, script:CadScriptRequest) -> CadScriptResult:

        task:AsyncResult = self.get_celery_task_method(script).apply_async(args=[], kwargs={ 'script' : script.json() })
        result_script_dict = await self.result_to_async(task)()
        result_script = CadScriptResult(**result_script_dict)

        return result_script


    #### UTILS #### 
        
        
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
