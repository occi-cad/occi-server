import os
os.sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from occilib.CadLibrary import CadLibrary
from occilib.CadScript import CadScriptRequest
from occilib.Admin import Admin, PublishJob, PublishRequest

lib = CadLibrary()

script_request = CadScriptRequest(**{
	"id": None,
	"org": "mark",
	"name": "doctestnew",
	"title": "DocTestNew",
	"namespace": "mark/doctestnew",
	"author": "mark",
	"license": "copyright",
	"version": "2.0.0",
	"url": None,
	"description": "Blablablabla",
	"created_at": "2023-11-27T15:05:52.281135",
	"updated_at": "2023-11-27T15:05:52.281139",
	"prev_version": None,
	"safe": False,
	"published": True,
	"units": None,
	"params": {
		"SIZE": {
			"name": "SIZE",
			"label": "SIZE",
			"type": "number",
			"default": 25,
			"description": None,
			"units": None,
			"iterable": True,
			"enabled": True,
			"order": 0,
			"start": 0.0,
			"end": 50.0,
			"step": 1.0
		}
	},
	"param_presets": {},
	"public_code": False,
	"code": "// Archiyou 0.20\r\n\r\nr = rect(100,$SIZE)\r\n\r\nr.select('E||right').dimension({ offset: 30});\r\nr.select('E||back').dimension({ offset: 10});\r\n\r\nd = doc\r\n    .name('spec')\r\n    .units('mm')\r\n    .page('test')\r\n    .size('A4')\r\n    .padding('1cm')\r\n    .orientation('landscape') // default: landscape\r\n    // Text\r\n    .text(\r\n        'Text left top 5mm', \r\n        { 'size' : '5mm' }\r\n    )\r\n    // Text aligned\r\n    .text(\r\n        'Text in middle 10mm', \r\n        { 'size' : '10mm' }\r\n    ) \r\n    .position(0.5,0.5)\r\n    // Image from URL 5x5cm aligned right bottom\r\n    .image('https://oscity.nl/static/img/manifest0.png', \r\n        { fit: 'contain'})\r\n    .width('5cm')\r\n    .height('5cm')\r\n    .position(1,0)\r\n    .pivot(1,0)\r\n    // SVG Image Top right 10x5cm with SVG styles preserved and scaled\r\n    .image(\r\n        'https://cms.archiyou.com/uploads/test_9bf0f065ed.svg', \r\n        { fit: 'contain',  align: ['right','center'] }\r\n    )\r\n    .width('10cm')\r\n    .height('5cm')\r\n    .pivot([1,1])\r\n    .position([1,1])\r\n    // Shapes with dimension line\r\n    .view('rect')\r\n    .shapes(r)\r\n    .width('10cm')\r\n    .height('5cm')\r\n    .position(0,0)\r\n    .pivot(0,0)\r\n    // Table directly without Calc\r\n    .table([\r\n            { field1: 'R0V1', field2: 'R0V2' },\r\n            { field1: 'R1V1', field2: 'R2V2' }\r\n        ])\r\n    .position(0,0.5);\r\n    \r\n",
	"cad_engine": "archiyou",
    "cad_engine_config" : {
        "docs" : ['spec']
    },
	"cad_engine_version": None,
	"secret_edit_token": None,
	"meta": {},
	"status": "success",
	"request": {
		"created_at": "2023-11-28T10:44:15.817142",
		"hash": "dbYLCTkbT-e",
		"params": {
			"SIZE": 25
		},
		"format": "gltf",
		"output": "full",
		"quality": "high",
		"batch_id": None,
		"batch_on_end_action": "publish",
		"settings": {
            "docs": ['spec'] # is_cached:True
            #"docs": False, # is_cached:True
            #"docs": ['manual'] # is_cached:True
        }
	}
})

#### TEST RESULTS WITH SPECIAL REQUESTS ####
print(lib.is_cached(script_request))