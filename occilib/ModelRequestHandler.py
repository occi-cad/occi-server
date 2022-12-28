""" 

    RequestHandler.py

    Handle a model request (with CadScript and CadScriptRequest) from API:
    1. Checking file system cache 
    2. Submitting the request to compute queue (RMQ)

"""

import logging
from fastapi import HTTPException
from starlette.responses import RedirectResponse
from typing import Dict

import asyncio
from asgiref.sync import sync_to_async
import nest_asyncio # see:  https://github.com/erdewit/nest_asyncio
from contextlib import suppress

import celery
from celery.result import AsyncResult

from .models import ModelRequestInput
from .Param import ParamConfigBase, ParamInstance
from .CadScript import CadScript
from .CadLibrary import CadLibrary

from .cqworker import compute_task

nest_asyncio.apply() # enables us to plug into running loop of FastApi

class ModelRequestHandler():

    #### SETTINGS ####
    WAIT_FOR_COMPUTE_RESULT_UNTILL_REDIRECT = 3
    REDIRECTING_COMPUTING_STATE = 'status'

    #### END SETTINGS

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
        else:
            self.logger.info('ModelRequestHandler::__init__(library): Celery is connected to RMQ succesfully!')
        

    def check_celery(self) -> bool:

        try:
            celery.current_app.control.inspect().ping()
            self.celery_connected = True
            return self.celery_connected
        except Exception as e:
            return False

    async def handle(self, req:ModelRequestInput):
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
            # no cache - but already computing?
            computing_task_id = self.library.check_cache_is_computing(requested_script.name, requested_script.hash())
            if computing_task_id:
                # refer back to compute url
                return self.go_to_computing_url(requested_script,computing_task_id, set_compute_status=False)
            else:
                # no cache: submit to workers
                if self.celery_connected:
                    task:AsyncResult = compute_task.apply_async(args=[], kwargs={ 'script' : requested_script.json() })
                    result_or_timeout = self.wait_time_or_return_compute_url(task)
                    if result_or_timeout == 'timeout':
                        return self.go_to_computing_url(requested_script, task.id)
                    else:
                        return result_or_timeout
                else:
                    # local debug
                    return requested_script

    def wait_time_or_return_compute_url(self, task:AsyncResult, time:int=None): # time in seconds
        """
            Async wait for a given number of seconds T
            if t < T return compute result directly to API client 
            otherwise redirect to computing url
            
            inspired by: https://stackoverflow.com/questions/53967281/what-would-be-promise-race-equivalent-in-python-asynchronous-code
        """

        time = time or self.WAIT_FOR_COMPUTE_RESULT_UNTILL_REDIRECT

        # simple async waiting
        async def wait(t):
            await asyncio.sleep(t)
            self.logger.warn(f'ModelRequestHandler::wait_time_or_return_compute_url: Wait for direct compute result elapsed: {time} seconds!')
            return 'timeout'

        loop = asyncio.get_running_loop()
        racing_tasks = set()
        racing_tasks.add(loop.create_task(wait(time)))
        racing_tasks.add(loop.create_task(self.result_to_async(task)()))

        done_first, pending = loop.run_until_complete(asyncio.wait(racing_tasks, return_when=asyncio.FIRST_COMPLETED))
        
        """
            TODO: DEBUG this message:
            RuntimeError: Cannot enter into task <Task pending name='Task-1' coro=<Server.serve() running at /usr/local/lib/python3.10/site-packages/uvicorn/server.py:80> wait_for=<Future finished result=None> cb=[_run_until_complete_cb() at /usr/local/lib/python3.10/asyncio/base_events.py:184, WorkerThread.stop()]> while another task <Task pending name='Task-4' coro=<RequestResponseCycle.run_asgi() running at /usr/local/lib/python3.10/site-packages/uvicorn/protocols/http/h11_impl.py:407> cb=[set.discard()]> is being executed.
        """
        result = None
        for coro in done_first:
            try:
                # return the first
                result = coro.result()
            except TimeoutError:
                return None

        # cancel pending tasks
        for p in pending:
            p.cancel()
            with suppress(asyncio.CancelledError):
                loop.run_until_complete(p)
                
        return result

    
    def result_to_async(self, task:AsyncResult): 
        """
            Current Celery (v5) does not support asyncio just yet. See: https://github.com/celery/celery/issues/6603
            We use asgiref.sync_to_async to turn AsyncResult.get() into a async method
            asgiref uses threads (see: https://github.com/django/asgiref/blob/main/asgiref/sync.py)
        """
        async def wrapper(*args, **kwargs):
            return await sync_to_async(task.get,thread_sensitive=False)()
        return wrapper

    def go_to_computing_url(self, script:CadScript, task_id:str, set_compute_status:bool=True) -> RedirectResponse:
        """
            When compute result takes longer then WAIT_FOR_COMPUTE_RESULT_UNTILL_REDIRECT
            Redirect to compute status url which the user can query untill the compute task is done 
            and then automatically gets redirected
        """
        if set_compute_status:
            self.library.set_cache_is_computing(script, task_id)

        return RedirectResponse(f'{script.name}/{script.hash()}/{self.REDIRECTING_COMPUTING_STATE}')


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
