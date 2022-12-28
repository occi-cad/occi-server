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

from typing import List, Dict

from .CadScript import CadScript, ModelRequest
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
    scripts_by_name:Dict[str,CadScript] = {}
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

    def get_script(self, name:str) -> CadScript:
        
        script = self.scripts_by_name.get(name)

        if not script:
            self.logger.error(f'CadLibrary:get_script(name): Could not find script with name "{name}" in library!')
        return script
        
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

    def _load_scripts_json(self, rel_path:str) -> List[CadScript]:

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
        """

        file_parse_regexs = list(map(lambda t: self._template_to_regex(t), self.FILE_STRUCTURE_TEMPLATES))
        
        for regex in file_parse_regexs:
            m = re.match(regex, script_path) # NOTE: script path is relative to library dir (this.path)
            if m:
                author = None
                org = None
                script_name = None # name is handled in _parse_config(script_path)
                script_file_name = m.groups()[-1] 
                
                if len(m.groups()) >= 2: 
                    script_name = m.groups()[-2] 
                if len(m.groups()) >= 3:
                    author = m.groups()[-3]
                if len(m.groups()) == 4:
                    org = m.groups()[-4]

                base_script = self._parse_config(script_path)
                self._set_script_dir(base_script.name, script_path)
                
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
        script_path, script_ext = os.path.splitext(script_path)
        script_name = os.path.split(script_path)[-1]
        
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

            base_script = None

            if script_config_file_ext == '.json':
                try:
                    script_config = json.load(open(script_config_file_path))
                except Exception as e:
                    self.logger.error(f'CadLibrary::_parse_config(): Failed to parse JSON config file "{script_config_file_path}" for CadScript "{script_name}": {e}')
                self._set_params_keys_to_names(script_config)
                base_script = CadScript(**{ 'name': script_name } | script_config)
                base_script = self._upgrade_params(base_script, script_config)
                
            elif script_config_file_ext == '.yaml' or script_config_file_ext == '.yml':
                self.logger.warn('CadLibrary::_parse_config(): YML config files not implemented yet!')
                pass
            
            if base_script:
                return base_script
            else:
                self.logger.warn(f'CadLibrary::_parse_config(): Invalid config for component "{script_name}". Check config file: {script_config_file_path}!')
                return CadScript(name=script_name) # return default script (only name is required)
                
    def _set_script_dir(self, script_name:str, script_path):
        """
            Set script name key in dirs_by_script_name 
            for getting to script directories for caching 
        """
        self.dirs_by_script_name[script_name] = os.path.dirname(script_path)

            
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

    #### HANDLING SCRIPT CONFIGS AND INSTANCES  ####

    def get_cached(self, script:CadScript) -> bool:

        return None

    #### CACHE OPERATIONS ####

    def set_cache_is_computing(self, script:CadScript, task_id:str):
        """
            Set computing status in library cache for this script and parameter hash
            This is needed to avoid computing things twice when requests are shortly after each other
            The task_id is placed as filename in the cache directory 
        """

        if not isinstance(script.request, ModelRequest):
            self.logger.error('CadLibrary::set_cache_computing(): Please supply a script instance with a .request!')
            return False

        script_request_dir_path = self._get_script_request_dir(script.name, script.hash())
        Path(script_request_dir_path).mkdir(parents=True, exist_ok=True) # check and make needed dirs if not exist
        # to avoid all kinds of problems clear the directory before writing the task file
        self._clear_dir(script_request_dir_path)

        with open(f'{script_request_dir_path}/{task_id}{self.COMPUTE_FILE_EXT}', 'w') as fp: # {library_path}/{component}/{param hash}/{task_id}
            fp.write(script.json()) # write requested script in file for convenience

        return True

    def check_cache_is_computing(self, script_name:str, script_instance_hash:str) -> str|bool:
        """
            Check if a specific script model request is computing
            Return task_id or False
        """
        script_request_dir = self._get_script_request_dir(script_name, script_instance_hash)

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
    
    def _get_script_request_dir(self, script_name:str, script_instance_hash:str) -> str:

        script_dir_path = self._get_script_filedir_path(script_name)
        return f'{script_dir_path}/{script_instance_hash}/'

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




            
   

