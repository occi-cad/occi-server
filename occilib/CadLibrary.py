"""

    CadLibrary.py

    Main class for getting CadScripts from filesystem and serving them up 
    as parametric models through a REST API to the user. 
    Either the result is served from the cache or executed in real time by workers

    Important notes:

    * Unique names for scripts

"""

import os
import __main__
import logging
from glob import iglob
from pathlib import Path
from shutil import rmtree
import re
from datetime import datetime
import json
import base64

from typing import List, Dict, Any

from fastapi.responses import Response, FileResponse

from .CadScript import ModelRequest, CadScript, CadScriptRequest, CadScriptResult
from .models import ModelFormat
from .Param import ParamConfigNumber, ParamConfigText

class CadLibrary:

    DEFAULT_PATH = './components' # relative to script
    FILE_STRUCTURE_TEMPLATES = [
        r'{org}/{author}/{component}/{script}',
        r'{author}/{component}/{script}',
        r'{component}/{script}', # maybe change this to {author}/{script}?
        r'{script}',
    ]
    CADSCRIPT_FILE_GLOB = ['*.py', '*.js']
    CADSCRIPT_CONFIG_GLOB = ['*.json', '*.yaml'] # TODO: YAML
    COMPUTE_FILE_EXT = '.compute'

    source = 'disk' # source of the scripts: disk or file (debug)
    path = DEFAULT_PATH # absolute path to directory of CadScripts
    scripts:List[CadScript] = []
    scripts_by_name:Dict[str,CadScriptRequest] = {}
    dirs_by_script_name:Dict[str,str] = {}

    def __init__(self, rel_path:str=DEFAULT_PATH):
        """
            Populate a library with CadScripts either from a directory (default) or a json file (for debugging)
            Paths are relative to root of the api directory
        """
        self._setup_logger()

        if '.json' in rel_path:
            self._load_scripts_json(rel_path)

        else:
            if self._check_path(rel_path) is None:
                self.logger.error(f'CadLibrary::__init__(): Given path "{rel_path}" is not a valid directory')
            else:
                self._load_scripts_dir(self.path)

        # for easy and fast access to certain scripts from the API 
        for script in self.scripts:
            self.scripts_by_name[script.name] = script

        # clear all compute files in cache to avoid old stuff blocking new tasks
        self._clear_computing_files()

        self._print_library_overview()

    def get_script_request(self, name:str) -> CadScriptRequest:
        
        script = self.scripts_by_name.get(name)

        if not script:
            self.logger.error(f'CadLibrary:get_script(name): Could not find script with name "{name}" in library!')
        
        script_request = CadScriptRequest(**dict(script)) # upgrade CadScript instance to CadScriptRequest for direct use by ModelRequestHandler
        return script_request
        
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

    def _check_path(self, rel_path:str) -> str:
        # rel_path is related to the root of this project (occilib/..)
        path = os.path.realpath(
            os.path.join(
                os.path.dirname(
                    os.path.dirname(__file__)), rel_path))

        self.path = path if os.path.isdir(path) else None
        return self.path

    def _load_scripts_json(self, rel_path:str) -> List[CadScriptRequest]:
        # rel_path is related to the root of this project (occilib/..)
        json_file_path = os.path.realpath(
            os.path.join(
                os.path.dirname(
                    os.path.dirname(__file__)), rel_path))

        if not os.path.isfile(json_file_path):
            self.logger.error(f'CadLibrary::_load_scripts_json(): No valid JSON file given ("{json_file_path}")!')
            return

        # just parse the json
        try:
            script_config_dicts = json.load(open(json_file_path))
        except Exception as e:
            self.logger.error(f'CadLibrary::_load_scripts_json(): Failed to parse JSON config file "{json_file_path}" for CadScripts: "{e}"')
            return

        for script_config in script_config_dicts:
            self._set_params_keys_to_names(script_config) 
            base_script = CadScript(**script_config)
            base_script = self._upgrade_params(base_script, script_config)
            self.scripts.append(base_script)

        self.source = 'file' # set flag so we now the scripts came from a file

        return self.scripts

        
    def _load_scripts_dir(self, path:str) -> List[CadScript]:
        glob_patterns = list(map(lambda t: self._template_to_glob_pattern(t), self.FILE_STRUCTURE_TEMPLATES ))
        for g in glob_patterns:
            for ext in self.CADSCRIPT_FILE_GLOB:
                glob_path_and_file = g.format(script=ext)
                for found_file in iglob(glob_path_and_file, root_dir=self.path, recursive=True):
                    found_file_path = found_file.replace('\\', r'/') # file name with relative path from library root
                    script = self._script_path_to_script(found_file_path) 
                    if script:
                        self.scripts.append(script)
        
        self.source = 'disk'
        return self.scripts


    def _template_to_glob_pattern(self, template:str) -> str:
        dirs = dict([ (d,'*') for d in ['org','author','component']])
        return template.format(script=r'{script}', **dirs) # keep script the same for easy plugin of file extensions

    def _template_to_regex(self,template:str):
        template = template.replace('/','\/')
        re_dirs = re.sub(r'{[^\}]+\}\\', r'([^\/]+)', template) # TODO: use named groups!
        regex = re_dirs.replace('{script}','([^\/$]+)$')
        return regex


    def _script_path_to_script(self,script_path:str) -> CadScript: 

        """ Create Script instance based on script_path 
            NOTE: script_path (including filename) is relative to the library path
            TODO: rewrite this from template pattern and grouped regex for easy config!
        """

        file_parse_regexs = list(map(lambda t: self._template_to_regex(t), self.FILE_STRUCTURE_TEMPLATES))
        
        for regex in file_parse_regexs:
            m = re.match(regex, script_path) # NOTE: script path is relative to library dir (this.path)
            if m:
                author = None
                org = None
                script_name = None # name is handled in _parse_config(script_path)
                script_file_name_ext = m.groups()[-1] # includes extension
                script_file_name = script_file_name_ext.split('.')[0]
                
                if len(m.groups()) >= 2: 
                    script_name = m.groups()[-2] 
                if len(m.groups()) >= 3:
                    author = m.groups()[-3]
                if len(m.groups()) == 4:
                    org = m.groups()[-4]

                base_script = self._parse_config(script_path)
                base_script.name = base_script.name.lower() # always lowercase
                self._set_script_dir(base_script.name, script_path)

                # getting extra info from path
                base_script.code = self._get_code_from_script_path(script_path)
                base_script.script_cad_language = self._get_code_cad_language(script_path)
                base_script.created_at = self._get_script_created_at(script_path)
                base_script.updated_at = self._get_script_created_at(script_path)
                base_script.author = author
                base_script.org = org

                return base_script


    def _get_script_created_at(self,script_path:str) -> datetime: # NOTE: path from library
        script_abs_path = os.path.realpath(os.path.join(self.path, script_path))
        return datetime.fromtimestamp(os.path.getctime(script_abs_path))

    def _get_script_updated_at(self,script_path:str) -> datetime: # NOTE: path from library
        script_abs_path = os.path.realpath(os.path.join(self.path, script_path))
        return datetime.fromtimestamp(os.path.getmtime(script_abs_path))

    def _parse_config(self,script_path:str) -> CadScript:
        """
            Basic on script_path (relative to library dir) scan directory for a config file (*.json or *.yaml)
            If config found populate an CadScript instance, otherwise return
        """
        script_dir_abs_path = os.path.dirname(os.path.realpath(os.path.join(self.path, script_path)))
        script_dir_name = os.path.split(script_dir_abs_path)[-1]
        script_path, script_ext = os.path.splitext(script_path)
        script_name_with_ext = os.path.split(script_path)[-1]
        script_name = script_name_with_ext.split('.')[0]
        
        script_config_file = None
        for config_ext in self.CADSCRIPT_CONFIG_GLOB:
            script_config_file_paths = list(iglob(config_ext, root_dir=script_dir_abs_path))
            if len(script_config_file_paths) > 0:
                script_config_file = script_config_file_paths[0]
                if len(script_config_file_paths) > 1:
                    script_config_file_paths_flat = script_config_file_paths.join(',')
                    self.logger.warn(f'CadLibrary::_parse_config(): There are multiple config files found ({script_config_file_paths_flat}) for script "{script_path}". Took the first!')
                break
        
        if not script_config_file:
            self.logger.warn(f'CadLibrary::_script_path_to_script(): No config found for component "{script_name}. Check its directory: "{script_path}"! Script is consided static now')
            return CadScript(name=script_name) # return default script (only name is required)
        else:
            script_config_file_path = os.path.realpath(os.path.join(script_dir_abs_path, script_config_file))
            script_config_file_name, script_config_file_ext = os.path.splitext(script_config_file)

            script_config = None
            base_script = None

            if script_config_file_ext == '.json':
                try:
                    script_config = json.load(open(script_config_file_path))
                except Exception as e:
                    self.logger.error(f'CadLibrary::_parse_config(): Failed to parse JSON config file "{script_config_file_path}" for CadScript "{script_name}": {e}')

                if script_config:
                    self._set_params_keys_to_names(script_config)
                    # naming priorities: config_file.name, script parent directory name ("script_dir_name") , script file name ("script_name")
                    chosen_script_name = script_config.get('name') or script_dir_name or script_name
                    base_script = CadScript(**{ 'name': chosen_script_name } | script_config) # CadScript needs a name
                    base_script = self._upgrade_params(base_script, script_config)
                
            elif script_config_file_ext == '.yaml' or script_config_file_ext == '.yml':
                self.logger.warn('CadLibrary::_parse_config(): YML config files not implemented yet!')
                pass
            
            if base_script:
                return base_script
            else:
                self.logger.warn(f'CadLibrary::_parse_config(): Invalid config for component "{script_name}". Check config file: {script_config_file_path}!')
                return CadScript(name=script_name) # return default script (only name is required)

    def _get_code_cad_language(self, script_path_rel) -> str:
        # TODO: this is not very robust when other script cad engines join
        EXT_TO_CODE_CAD_LANGUAGE = { 
            'py' : 'cadquery',
            'js' : 'archiyou', 
        }
        return EXT_TO_CODE_CAD_LANGUAGE.get(script_path_rel.split('.')[-1])

    def _get_code_from_script_path(self, script_path_rel:str) -> str:
        """
            Get code inside the script
        """
        script_path_abs = os.path.realpath(os.path.join(self.path, script_path_rel))

        if not os.path.isfile(script_path_abs):
            self.logger.error('CadLibrary::_get_code_from_script_path: given path to script is not a file!')
            return None

        with open(script_path_abs, 'r') as f:
            return f.read()

             
    def _set_script_dir(self, script_name:str, script_path):
        """
            Set script name key in dirs_by_script_name 
            for getting to script directories for caching 
        """
        self.dirs_by_script_name[script_name] = os.path.realpath(os.path.join(self.path, os.path.dirname(script_path)))

            
    def _set_params_keys_to_names(self, script_config:dict) -> dict:
        # if script_config['params'] is a dict, set its keys as names to the Params
        if type(script_config['params']) is dict:
            for k,v in script_config['params'].items():
                v['name'] = k

        
    def _upgrade_params(self, base_script:CadScript, script_config:dict) -> CadScript: 
        """
            Pydantic automatically parses the Param as ParamConfigBase
            Upgrade them according to the type field so we get ParamConfigNumber, ParamConfigText etc

        """
        TYPE_TO_PARAM_CLASS = {
            'number' : ParamConfigNumber,
            'text' : ParamConfigText,
        }

        new_params:Dict[str,ParamConfigNumber|ParamConfigText] = {}
        for name, param in base_script.params.items():
            ParamClass = TYPE_TO_PARAM_CLASS.get(param.type) # name of type is already validated by Pydantic and models.ParamType enum
            orig_param_data = list(filter( lambda param_conf: param_conf['name'] == param.name, script_config['params'].values()))[0]
            new_params[name] = ParamClass(**orig_param_data)

        base_script.params = new_params

        return base_script

    #### CACHE OPERATIONS ####

    def is_cached(self, script:CadScriptRequest) -> bool: 

        return self._get_cached_script_file_path(script) is not None 

        
    def _get_cached_script_file_path(self, script:CadScriptRequest) -> str:
        """
            Get the result.json in the cache
        """

        cached_script_model_dir = self._get_script_cached_model_dir(script)
        cached_script_model_file = f'{cached_script_model_dir}/result.json'
        return cached_script_model_file if Path(cached_script_model_file).is_file() else None


    def get_cached_script(self, script:CadScriptRequest) -> CadScriptResult:
        """
            See if we have a cached version of this CadScriptRequest
        """
        
        cached_script_path = self._get_cached_script_file_path(script)
        if cached_script_path is None:
            self.logger.error(f'CadLibrary::get_cached_script: Can not get cached script with name "{script.name}"!')
            return None
        else:
            with open(cached_script_path) as f:
                cached_script_dict = json.loads(f.read())
                cached_script = CadScriptResult(**cached_script_dict)
                self._apply_single_model_format(cached_script)
                return cached_script

    def get_cached_model(self, script:CadScriptRequest) -> Any:

        EXT_OUTPUT_TYPE = {
            'step' : 'text',
            'gltf' : 'binary',
            'stl' : 'binary'
        }

        cached_script_dir = self._get_script_cached_model_dir(script)
        cached_model_path = f'{cached_script_dir}/result.{script.request.format}'

        if os.path.exists(cached_model_path) is False:
            self.logger.error(f'CadLibrary::get_cached_model: Cannot get requested model from cache for script "{script.name}"')
            return None
        else:
            output_model_filename = f'{script.name}-{script.hash()}.{script.request.format}'
            return FileResponse(cached_model_path, filename=output_model_filename)


    def _apply_single_model_format(self, script:CadScriptResult) -> CadScriptResult:

        format = script.request.format
        if format is None:
            return script

        needed_model_format = script.results.models[format]
        script.results.models = {}
        script.results.models[format] = needed_model_format

        return script


    def set_cache_is_computing(self, script:CadScript, task_id:str):
        """
            Set computing status in library cache for this script and parameter hash
            This is needed to avoid computing things twice when requests are shortly after each other
            The task_id is placed as filename in the cache directory 
        """

        if not isinstance(script.request, ModelRequest):
            self.logger.error('CadLibrary::set_cache_computing(): Please supply a script instance with a .request!')
            return False

        script_request_dir_path = self._get_script_cached_model_dir(script)
        Path(script_request_dir_path).mkdir(parents=True, exist_ok=True) # check and make needed dirs if not exist
        # to avoid all kinds of problems clear the directory before writing the task file
        self._clear_dir(script_request_dir_path)

        with open(f'{script_request_dir_path}/{task_id}{self.COMPUTE_FILE_EXT}', 'w') as fp: # {library_path}/{component}/{component}-cache/{param hash}/{task_id}
            fp.write(script.json()) # write requested script in file for convenience

        return True

    def check_cache_is_computing(self, script_name:str, script_instance_hash:str) -> str|bool:
        """
            Check if a specific script model request is computing
            Return task_id or False
        """
        script_request_dir = f'{self._get_script_cache_dir(script_name)}/{script_instance_hash}'

        if os.path.exists(script_request_dir):
            files = os.listdir(script_request_dir)
            
            if len(files) > 0:
                first_file = files[0]
                path, ext = os.path.splitext(first_file)
                if ext == self.COMPUTE_FILE_EXT: # .compute extension for robustness
                    self.logger.info(f'ModelRequestHandler::check_cache_is_computing: Found computing. task_id = "{files[0]}"')
                    return files[0].replace(self.COMPUTE_FILE_EXT, '') # return name of file, which is the task_id
                else:
                    return False # probably cached files
            else:
                False

        return False

    def _get_script_cached_model_dir(self, script:CadScriptRequest) -> str:
            
            return f'{self._get_script_cache_dir(script.name)}/{script.hash()}'
    
    def _get_script_cache_dir(self, script_name:str) -> str:
        #  {library_path}/{component}/{component}-cache
        script_dir_path = self._get_script_filedir_path(script_name)
        return f'{script_dir_path}/{script_name}-cache'

    def _get_script_filedir_path(self, script_name:str) -> str:
        if self.source == 'file':
            return os.path.join(os.path.realpath(self.path), script_name)
        else:
            return self.dirs_by_script_name.get(script_name)
    
    def _clear_dir(self, dir_path) -> bool:
        for path in Path(dir_path).glob("**/*"):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                rmtree(path)

    def _clear_computing_files(self) -> bool:

        for path in Path(self.path).glob("**/*"):
            if path.is_file() and path.suffix == self.COMPUTE_FILE_EXT:
                path.unlink()

        self.logger.info('CadLibrary::_clear_computing_files: Cleared old compute files!')

        return True

    def set_script_result_in_cache_and_return(self, script_result:CadScriptResult) -> Response|FileResponse: # return a raw Starlette/FastAPI response with json content

        result_cache_dir = f'{self._get_script_cache_dir(script_result.name)}/{script_result.request.hash}'
        # place total JSON response in cache
        Path(result_cache_dir).mkdir(parents=True, exist_ok=True)

        script_result_json = script_result.json()

        # save results to file
        with open(f'{result_cache_dir}/result.json', 'w') as f:
            f.write(script_result_json)
        with open(f'{result_cache_dir}/result.step', 'w') as f:
            f.write(script_result.results.models['step'])
        with open(f'{result_cache_dir}/result.stl', 'wb') as f:
            stl_binary = base64.b64decode(script_result.results.models['stl']) # decode base64
            f.write(stl_binary)

        # Depending on request.format and request.output return either full json or file
        if script_result.request.output == 'full':
            return Response(content=script_result_json, media_type="application/json") # don't parse the content, just output
        else:
            output_model_format = script_result.request.format
            output_model_filename = f'{script_result.name}-{script_result.hash()}.{script_result.request.format}'
            return FileResponse(f'{result_cache_dir}/result.{output_model_format}', filename=output_model_filename)


    #### UTILS ####

    def _print_library_overview(self):

        self.logger.info('**** OCCI COMPONENTS LIBRARY LOADED ****')
        self.logger.info(f'Scripts: {len(self.scripts)}')
        for script in self.scripts:
            self.logger.info(f'- "{script.name}" [{script.script_cad_language}] - path: "{self.dirs_by_script_name[script.name]}/", lines of code: {self._get_lines_of_code(script.code)}, params: {len(script.params.keys())}, author:"{script.author}", org:"{script.org}"')
        self.logger.info('********')

    def _get_lines_of_code(self,code:str) -> int:
        
        if type(code) is not str:
            return 0
        return len(code.split('\n'))



            
   

