import uvicorn as uvicorn
from starlette.responses import RedirectResponse
from fastapi import FastAPI, HTTPException, Depends
from celery.result import AsyncResult

from typing import List, Dict

from occilib.CadLibrary import CadLibrary
from occilib.ApiGenerator import ApiGenerator
from occilib.models import SearchQueryInput

from dotenv import dotenv_values
CONFIG = dotenv_values()

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
        'library': CONFIG.get('OCCI_LIBRARY_NAME', 'unnamed OCCI library. See settings in .env'),
        'maintainer': CONFIG.get('OCCI_LIBRARY_MAINTAINER'),
        'maintainer_email': CONFIG.get('OCCI_LIBRARY_MAINTAINER_EMAIL'),
    }

#### COMPUTING SCRIPTS STATUS ####
@app.get('/{script_name}/{script_instance_hash}/job')
async def get_model_compute_task(script_name:str, script_instance_hash:str):
    """
        If a compute takes longer then a defined time (see ModelRequestHandler.WAIT_FOR_COMPUTE_RESULT_UNTILL_REDIRECT)
        The user is redirected to this url which supplies information on the task
        If the task is done redirect to original url that will serve the result from cache
    """
    job = library.check_script_model_computing_job(script_name, script_instance_hash)
    # TODO: somewhere check if compute ever was ever succesful?
    if job is None:
        # no such celery task found in cache: show error
        raise HTTPException(status_code=404, detail="Compute task not found. Please go back to original request url!")
    else:
        celery_task_result:AsyncResult = AsyncResult(job.celery_task_id)
        if celery_task_result.ready():
            r = celery_task_result.result
            #celery_task_result.forget() # clear result from backend!
            return r # this is the CadScriptResult
        else:
            job.celery_task_status = celery_task_result.status
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

