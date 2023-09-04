"""
    test_library.py

    Some debug functions directly with the CadLibrary class

"""

import os
os.sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from occilib.CadLibrary import CadLibrary
from occilib.CadScript import CadScript
from occilib.Admin import Admin, PublishJob, PublishRequest

lib = CadLibrary()
#print (lib._load_scripts_dir())
#lib._print_library_overview()
#print (lib.get_script_request('tests/box', version=0.5))
#print (lib.get_script_request('tests/box'))


#print(lib.scripts[2].all_possible_model_params())  
#lib.compute_cache()

### PRECOMPUTE ###
'''
script = lib.get_script_request(org='tests', name='sphere')
print(script.get_num_variants())
for d in script.iterate_possible_model_params_dicts():
    print(d)
'''

#lib.compute_script_cache(org='tests', name='sphere')

### ADMIN ###

'''
test_script = CadScript(name='Test', org='testorg')
print(test_script)
print(lib.script_to_library_path(test_script))
print(lib.script_exists(test_script))

print(lib.script_to_library_path(CadScript(name='steelbeam', org='archiyou', version='0.5')))
print(lib.script_exists(CadScript(name='steelbeam', org='archiyou', version='0.5'))) # True
'''

# lib.add_script(CadScript(name='steelbeam', org='archiyou', version='0.5')) # error
#lib.add_script(CadScript(name='testscript', org='testorg', code='b = box();', cad_engine='archiyou'), overwrite=True)

#### TEST VALIDATION AND UPGRADE OF PARAMS ####
"""
script = CadScript(**{
		 "name" : "pubtest",
		 "org" : "archiyou",
		 "version" : "1.2",
		 "cad_engine" : "archiyou",
		 "code": "b = box($SIZE);",
		 "params" : {
					"SIZE" : { "type" : "number", "start" : 1, "end" : 1000, "step" : 1, "default" : 5 }
		 }
	 })

print(script) # params should not be ParamConfigBase
"""

#### TEST SCRIPT DIRS ####
'''
script=CadScript(**{ "name" : "pubtest", "org" : "archiyou", "version" : "1.2", "cad_engine" : "archiyou", "code": "b = box($SIZE);", "params" : { "SIZE" : { "type" : "number", "start" : 1, "end" : 10, "step" : 1, "default" : 5 } }})
print(lib._get_script_version_dir(script))
print(lib._get_script_version_cache_dir(script))
print(lib._get_script_version_cached_model_dir(script))
'''   

#### TEST BUG ####

'''
script = lib.get_script_request(org='mark', name='pubtest', version='2.12.0')

#lib.check_script_model_computing_job(script=script, script_instance_hash=script.hash())

# test if CadScript params are upgraded
req = PublishRequest(script=script)
print(req.script.dict())
'''

#### TEST SEARCH ####
# print(lib.search('box'))

#### LATEST SCRIPTS ####
# print(lib.latest_scripts)

#### ALL VERSIONS OF SCRIPT ####
print(lib.script_versions)