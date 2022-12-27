import os
import time

from celery import Celery # docs: https://docs.celeryq.dev/en/stable/userguide/tasks.html#basics

from occilib.CadScript import CadScript

from dotenv import dotenv_values

CONFIG = dotenv_values()  

celery = Celery(__name__)
celery.conf.broker_url = CONFIG.get('CELERY_BROKER_URL') or 'amqp://guest:pass@localhost:5672'
celery.conf.result_backend = CONFIG.get('CELERY_RESULT_BACKEND') or 'rpc://localhost:5672' # for RMQ as backend see: https://github.com/celery/celery/issues/6384 - TODO: move to redis?

@celery.task(name='compute_task', bind=True) # bind needed for retries
def compute_task(script:CadScript):
    print('==== CALCULATING SCRIPT MODEL REQUEST ====')
    print(script)
    #time.sleep(10) # TEMP
    return True