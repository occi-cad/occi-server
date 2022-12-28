import os
import time
import json # TODO: use orjson?

from celery import Celery # docs: https://docs.celeryq.dev/en/stable/userguide/tasks.html#basics

from .CadScript import CadScript
from .models import ModelResult

from dotenv import dotenv_values

CONFIG = dotenv_values()  

celery = Celery(__name__)
celery.conf.broker_url = CONFIG.get('CELERY_BROKER_URL') or 'amqp://guest:pass@localhost:5672'
celery.conf.result_backend = CONFIG.get('CELERY_RESULT_BACKEND') or 'rpc://localhost:5672' # for RMQ as backend see: https://github.com/celery/celery/issues/6384 - TODO: move to redis?

@celery.task(name='compute_task', bind=True) # bind needed for retries
def compute_task(self,script:str): # json of CadScript
    time_start = time.time()
    time.sleep(2) # TEMP instead of really execution on CQ
    script_instance = CadScript(**json.loads(script))
    script_instance.results = ModelResult() # some fase result 
    script_instance.results.duration = round((time.time() - time_start) * 1000) # in ms 
    return json.loads(script_instance.json()) # NOTE: .dict() does not serialize nested pydantic instances