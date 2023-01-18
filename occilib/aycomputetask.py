from celery import Celery # docs: https://docs.celeryq.dev/en/stable/userguide/tasks.html#basics
from dotenv import dotenv_values

CONFIG = dotenv_values()  

celery = Celery(__name__)
celery.conf.broker_url = CONFIG.get('CELERY_BROKER_URL')
celery.conf.result_backend = CONFIG.get('CELERY_RESULT_BACKEND')

@celery.task(name='archiyou.compute', bind=True, delivery_mode=1)
def compute_job_archiyou(self,script:str):
    # dummy for sending to broker: real work is done by archiyou nodejs worker
    pass
