from occilib.CadLibrary import CadLibrary

#lib = CadLibrary()

lib = CadLibrary()
#print(lib.scripts)
#print(lib.scripts[2].all_possible_model_params())  
#lib.compute_cache()

print(lib.search('box'))