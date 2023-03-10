"""
    test_library.py

    Some debug functions directly with the CadLibrary class

"""

import os
os.sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from occilib.CadLibrary import CadLibrary
from occilib.CadScript import CadScript

lib = CadLibrary()
print (lib._load_scripts_dir())
#lib._print_library_overview()
#print (lib.get_script_request('tests/box', version=0.5))
#print (lib.get_script_request('tests/box'))


#print(lib.scripts[2].all_possible_model_params())  
#lib.compute_cache()

#### SEARCH ####
#print(lib.search('box'))

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
lib.add_script(CadScript(name='testscript', org='testorg', code='b = box();', script_cad_language='archiyou'), overwrite=True)