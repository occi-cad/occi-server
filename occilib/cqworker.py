import os
import json # TODO: use orjson?
import base64
import time

from celery import Celery # docs: https://docs.celeryq.dev/en/stable/userguide/tasks.html#basics
from dotenv import dotenv_values

import cadquery
from cadquery import cqgi

from .CadScript import CadScriptResult
from .models import ModelResult


CONFIG = dotenv_values()  

celery = Celery(__name__)
celery.conf.broker_url = CONFIG.get('CELERY_BROKER_URL') or 'amqp://guest:pass@localhost:5672'
celery.conf.result_backend = CONFIG.get('CELERY_RESULT_BACKEND') or 'rpc://localhost:5672' # for RMQ as backend see: https://github.com/celery/celery/issues/6384 - TODO: move to redis?

@celery.task(name='compute_task', bind=True) # bind needed for retries
def compute_task(self,script:str): # json of CadScript 
    time_start = time.time()
    script_result = CadScriptResult(**json.loads(script)) # parse CadScriptRequest json as CadScciptResult
    result_response = ModelResult()

    #### REAL EXECUTION IN CADQUERY ####
    # !!!! ONLY TRUSTED CODE !!!!
    '''
        Some NOTES to extend the worker:
        - capture Exception and add to script.result.errors
        
    '''
    if script_result.script_cad_language == 'cadquery':
        param_values = script_result.get_param_values_dict()
        build_result = cqgi.parse(script_result.code).build(build_parameters=param_values, build_options={} )
        
        # TODO: multiple calling show_object() populates a list of results: can we handle those?
        result = build_result.results[-1].shape  # for now use the last result

        # output main formats: step (text), gltf (binary) and stl (binary) 
        cadquery.exporters.export(result, 'result.step', cadquery.exporters.ExportTypes.STEP)
        #cadquery.exporters.export(build_result, 'result.gltf', cadquery.exporters.ExportTypes.GLTF) # not in yet?
        cadquery.exporters.export(result, 'result.stl', cadquery.exporters.ExportTypes.STL)

        

        with open('result.step', 'r') as f:
            result_response.models['step'] = f.read()
        os.remove('result.step') # to be sure: clean up

        '''
        with open('result.gltf', 'rb') as f:
            result_response.models['gltf'] = base64.b64encode(f.read()).decode('utf-8')
        os.remove('result.gltf') # to be sure: clean up
        '''
 
        with open('result.stl', 'rb') as f:
            result_response.models['stl'] = base64.b64encode(f.read()).decode('utf-8')
        os.remove('result.stl') # to be sure: clean up

        script_result.results = result_response
        script_result.results.duration = round((time.time() - time_start) * 1000) # in ms 

    #### END EXECUTION

    return script_result.dict()