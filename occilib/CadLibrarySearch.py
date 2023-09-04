"""
    LibrarySearch.py

    Simple wrapping class over Whoosh search library

"""

import os, os.path
import logging
from datetime import datetime
from pathlib import Path
from dotenv import dotenv_values

from pydantic import BaseModel
import whoosh.fields
from whoosh.fields import Schema as WhooshSchema
from whoosh.index import FileIndex, create_in, open_dir

from whoosh.qparser import MultifieldParser
import whoosh.qparser

from typing import Any, List

from .CadScript import CadScript

CONFIG = dotenv_values()

class CadLibrarySearch:

    #### SETTINGS ####
    SEARCH_INDEX_DIRNAME = 'library_index'
    SEARCHABLE_FIELDS = ['name', 'author', 'org', 'description', 'units', 'code', 'cad_engine']

    library = None
    parser:MultifieldParser = None
    index:FileIndex = None

    def __init__(self, library):
        
        self._setup_logger()
        self.library = library
        self.build_index()

    def build_index(self):

        self.logger.info('**** Building Library Search index ****')

        schema = self._pydantic_model_to_whoosh_schema(CadScript)
        lib_dir_path = f'{self.library.path}/{self.SEARCH_INDEX_DIRNAME}'
        Path(lib_dir_path).mkdir(parents=True, exist_ok=True)
        self.index = create_in(lib_dir_path, schema)
        index_writer = self.index.writer()
        for script in self.library.latest_scripts.values(): # for now only show latest scripts in search!
            index_writer.add_document(**script.dict())
        index_writer.commit()
        self.parser = MultifieldParser(self.SEARCHABLE_FIELDS, schema=schema)        
        
        # allow lowercase and / or (to be consistent with MS REST API spec)
        op = whoosh.qparser.OperatorsPlugin(And=" and ", Or=" or ")
        self.parser.replace_plugin(op)

        # add fuzzy text search
        self.parser.add_plugin(whoosh.qparser.FuzzyTermPlugin())

        self.logger.info('**** Library Search index complete ****')

    def search(self, q:str) -> List[CadScript]:

        # Add search fuzzyness of distance 1. See: https://whoosh.readthedocs.io/en/latest/parsing.html
        q += '~1'
        query_obj = self.parser.parse(q)
        
        with self.index.searcher() as searcher:
            results = searcher.search(query_obj)
            if len(results) > 0:
                result_dicts = []
                for r in results:
                    # add url on the fly for now
                    result_dict = dict(r)
                    result_dict['url'] = f"{CONFIG['API_ROOT_URL']}/{result_dict['namespace']}" if CONFIG.get('API_ROOT_URL') else None
                    result_dicts.append(result_dict)
                return result_dicts
            else:
                return []
            
    


    def _pydantic_model_to_whoosh_schema(self, Model:Any) -> WhooshSchema:

        BASE_WHOOSH_FIELDS = { 'name' : whoosh.fields.ID }
 
        PYDANTIC_FIELD_TYPE_TO_WHOOSH_FIELDS = {
            'integer' :  whoosh.fields.NUMERIC(stored=True),
            'float' : whoosh.fields.NUMERIC(stored=True),
            'datetime' : whoosh.fields.DATETIME(stored=True),
            'str' :  whoosh.fields.TEXT(stored=True),
            'enum' : whoosh.fields.TEXT(stored=True),
        }
        UNKNOWN_WHOOSH_FIELD = whoosh.fields.STORED

        whoosh_fields = BASE_WHOOSH_FIELDS

        for name, model_field in Model.__fields__.items(): # for ModelField. See: https://github.com/pydantic/pydantic/blob/main/pydantic/fields.py
            try:
                # NOTE: some hacky handling of enums as just text
                type_class_str = model_field.type_.__name__ if model_field.type_.__class__.__name__ != 'EnumMeta' else 'enum' 
                whoosh_field_class = PYDANTIC_FIELD_TYPE_TO_WHOOSH_FIELDS.get(type_class_str)
                if whoosh_field_class:
                    whoosh_fields[name] = whoosh_field_class
                else:
                    self.logger.warn(f'CadLibrarySearch::_pydantic_model_to_whoosh_schema(): Skipped field with name "{name}": Unknown type in Pydantic Model: "{type_class_str}". Reverting to non-searchable field!')
                    whoosh_fields[name] = UNKNOWN_WHOOSH_FIELD
                
            except Exception as e:
                self.logger.warn(f'CadLibrarySearch::_pydantic_model_to_whoosh_schema(): Skipped field with name "{name}": Error converting. This field will not be searchable!')
                whoosh_fields[name] = UNKNOWN_WHOOSH_FIELD

        return WhooshSchema(**whoosh_fields)



    #### UTILS ####

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