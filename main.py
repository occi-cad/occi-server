import uvicorn as uvicorn
from fastapi import FastAPI

import json

from occilib.CadLibrary import CadLibrary
from occilib.ApiGenerator import ApiGenerator

# TMP GET SCRIPT FROM JSON
lib = CadLibrary('./scripts.json')
scripts = lib.scripts

api_generator = ApiGenerator()
app = FastAPI(openapi_tags=api_generator.get_api_tags(scripts))
api_generator.generate_endpoints(api=app, scripts=scripts)

@app.get("/")
async def index():
    return 'OCCI index'

#### TEST SERVER ####
if __name__ == '__main__':
    uvicorn.run(app, host='127.0.0.1', port=8090, workers=1)

