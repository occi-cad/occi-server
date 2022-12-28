import uvicorn as uvicorn
from fastapi import FastAPI
from celery.result import AsyncResult

from occilib.CadLibrary import CadLibrary
from occilib.ApiGenerator import ApiGenerator

# TMP GET SCRIPT FROM JSON
library = CadLibrary('./scripts.json')
scripts = library.scripts

api_generator = ApiGenerator(library)
app = FastAPI(openapi_tags=api_generator.get_api_tags(scripts))
api_generator.generate_endpoints(api=app, scripts=scripts)

@app.get("/")
async def index():
    return 'OCCI index'

@app.get('/{script_name}/{script_instance_hash}/status')
async def get_model_compute_task(script_name:str, script_instance_hash:str):
    """
        If a compute takes longer then a defined time (see ModelRequestHandler.WAIT_FOR_COMPUTE_RESULT_UNTILL_REDIRECT)
        The user is redirected to this url which supplies information on the task
        If the task is done redirect to original url that will serve the result from cache
    """
    task_id = library.check_cache_is_computing(script_name, script_instance_hash)
    task_result:AsyncResult = AsyncResult(task_id)
    return { 'task_id': task_result.id, 'task_status': task_result.status }


#### TEST SERVER ####
if __name__ == '__main__':
    uvicorn.run(app, host='127.0.0.1', port=8090, workers=1)

