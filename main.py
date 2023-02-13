import os
import uvicorn as uvicorn
from starlette.responses import RedirectResponse
from fastapi import FastAPI, HTTPException, Depends, Response, status
from celery.result import AsyncResult

from typing import List, Dict

from occilib.CadLibrary import CadLibrary
from occilib.CadScript import CadScriptResult
from occilib.ApiGenerator import ApiGenerator
from occilib.models import SearchQueryInput

library = CadLibrary('./scriptlibrary')
scripts = library.scripts
api_generator = ApiGenerator(library)

#### CHECK CONNECTION TO RMQ ####

if api_generator.request_handler.check_celery() is False:
    raise Exception('*** RESTART API - No Celery connection and/or missing workers: Restart API ****') 

app = FastAPI(openapi_tags=api_generator.get_api_tags(scripts))
api_generator.generate_endpoints(api=app, scripts=scripts)

@app.get("/")
async def index():
    return {
        'library': os.environ.get('OCCI_LIBRARY_NAME', 'unnamed OCCI library. See settings in .env'),
        'maintainer': os.environ.get('OCCI_LIBRARY_MAINTAINER'),
        'maintainer_email': os.environ.get('OCCI_LIBRARY_MAINTAINER_EMAIL'),
    }

#### COMPUTING JOB STATUS ####

@app.get('/{script_org}/{script_name}/{script_instance_hash}/job/{celery_task_id}')
async def get_model_compute_task(script_name:str, script_instance_hash:str, celery_task_id:str, response: Response):
    """
        If a compute takes longer then a defined time (see ModelRequestHandler.WAIT_FOR_COMPUTE_RESULT_UNTILL_REDIRECT)
        The user is redirected to this url which supplies information on the job
        The client then needs to refresh that job endpoint until a result or error is given 
        We leverage the result system of Celery (timeout 1 day) to have cache compute results for the infite compute jobs
        The finite compute jobs are cached on disk

        We decided not to do redirects after result is done because its simpler, less calls for client , more robust
        and we can leverage Celery cache for 'infinite' script results. 
        Otherwise we have to maintain a tmp cache for these results on disk

        Multiple clients can be refered to the same compute job URL without creating a new celery task.
        But using the Celery task_id keeps the results available 
        If the compute is done the .compute file is cleaned automatically
    """
    
    celery_task_result:AsyncResult = AsyncResult(celery_task_id)

    if celery_task_result.state in ['PENDING', 'FAILURE']: # pending means unknown because we directly set state to SEND (see ModelRequestHandler.setup_celery_publish_status())
        raise HTTPException(status_code=404, detail="Compute task not found or in error state. Please go back to original request url!")

    elif celery_task_result.ready():
        '''
        NOTE: we lean on the Celery result system to have cache for 'infinite' script variants
         results are automatically reset after one day: https://docs.celeryq.dev/en/stable/userguide/configuration.html#std-setting-result_expires
        ''' 
        script_result_dict = celery_task_result.result
        script_result = CadScriptResult(**script_result_dict)
        library._apply_single_model_format(script_result)
        
        return script_result.dict() # output as dict
    else:
        # the job info we can get from a temporary file (.compute) in directory
        job = library.check_script_model_computing_job(script_name, script_instance_hash)
        if not job:
           raise HTTPException(status_code=404, detail="Compute task not found or in error state. Please go back to original request url!") 
        job.celery_task_status = celery_task_result.status
        
        response.status_code = status.HTTP_202_ACCEPTED # special code to signify the job is still being processed
        return job.dict() # return status of job 
            

#### SEARCH ####
@app.get('/search')
async def search(inp:SearchQueryInput = Depends()) -> List[Dict]:
    if inp.q is None: # return all scripts
        return [s.dict() for s in library.scripts]
    else:
        return library.search(inp.q)

@app.post('/search')
async def search(inp:SearchQueryInput) -> List[Dict]:
    if inp.q is None: # return all scripts
        return [s.dict() for s in library.scripts]
    else:
        return library.search(inp.q)


#### TEST SERVER ####
if __name__ == '__main__':
    uvicorn.run(app, host='127.0.0.1', port=8090, workers=1)

