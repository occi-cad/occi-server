# About OCCI

Open CAD Components Interface (OCCI) brings parametric components to all by using script CAD engines like CadQuery and Archiyou. Script CAD is very suitable to deliver platform-independant 'open design' parametric CAD content and we hope that OCCI will contribute to that. 

The simplest way to try OCCI is with our [FreeCAD plugin](https://github.com/occi-cad/occi-freecad-plugin). You can find the [OCCI design principles and spec here](https://github.com/occi-cad/occi-cad-spec).

# OCCI server

This repository contains a reference server stack that allows CAD scripts (currently we support CadQuery and Archiyou scripts) to be quickly turned into an OCCI API. 

Use cases:
* You have a CAD script for which you want to build a viewing/configurator web-application
* You have a lot of CAD scripts that you want to share with other online

## Developer Quickstart

The stack is fully dockerized. To start up a local OCCI server with a default CadQuery worker:

1. git clone https://github.com/occi-cad/occi-server.git
2. Add a .env file to the main directory based on env.example
3. Add scripts into the 'scriptlibrary' directory in format ./scriptlibrary/{org}/{name}/{version}/{name}.py|js and {name}.json for the config file. There is an [OCCI example library](https://github.com/occi-cad/scriptlibrary) to get you started. Make sure you are in the root directory:
```
git clone https://github.com/occi-cad/scriptlibrary
```
4. Go into a terminal and run:

``` 
    docker-compose up
```
5. Once everything is started up and connected go to localhost:8090 to see the OCCI server basic information
6. Get your first parametric model from OCCI example library. Go to url: http://localhost:8090/tests/box. This will give you a parametric box in STEP file. Use http://localhost:8090/tests/box?output=full to see more information. 

## Using an OCCI API

We have auto-generated API docs. Go to http://localhost:8090/docs on your OCCI server for all query possibilities. Here are the basics:

1. Get script: {ROOT}/{org}/{name} - Access the default version of a script
    * format=step|stl|gltf - File format of model (GLTF not supported in CQ for now!)
    * output=full|model - return a full JSON response or just the model file in given format (default=STEP)
2. Search: {ROOT}/search?q={search_string}

## Manage and configure your CAD scripts

To quickly turn your CAD scripts into an API:

1. Create a directory _scriptlibrary_ if not exists
2. Place your scripts (for example _mybox.py_ for Cadquery) in a folder structure like this: 
    scriptlibrary/{org/author}/{scriptname}/{version}/{scriptname}.py
    for example: _scriptlibrary/mycadcompany/mybox/0.5/mybox.py_
3. Also add a simple configuration JSON file called mybox.json in that directory with the following basic information:

```
{
    "description" : "A simple test box",
    "params" : { 
        "size" : {
            "type": "number",
            "start" : 1,
            "end" : 100,
            "default" : 50,
            "description" : "The size of the box",
            "units" : "mm"
        }
    },
    "param_presets": {
        "small": { "size" : 5 },
        "medium": { "size" : 50 },
        "big": { "size" : 100 }
    },
    "license" : "CC0"
}
```
This will make the box parametric and enable OCCI API to check inputs

4. If you run the occi-server stack (see Developer Quickstart) your script should be available at
   _localhost:8090/mycadcompany/mybox/0.5/mybox_

You can configure the parameters to your scripts in multiple ways. Currently these parameter types are supported:
* _number_ -  'start' to 'end' with 'step'
* _boolean_ 
* _text_ - optional: 'max_length', 'min_length'
* _options_ - with 'values' with a list of strings

For more information on optional content of the *.json config file see CadScript.py in occilib/ 

## Deploy in Production

Use 'docker-compose.prod.yml' if you want to host a OCCI server with a HTTPS certificate and Nginx webserver:

1. Go to nginx.conf and fill in your domain information

```
    server_name myocci.server.org;

    # Load the certificate files.
    ssl_certificate         /etc/letsencrypt/live/myocci.server.org/fullchain.pem;
    ssl_certificate_key     /etc/letsencrypt/live/myocci.server.org/privkey.pem;
    ssl_trusted_certificate /etc/letsencrypt/live/myocci.server.org/chain.pem;
```

2. Make sure the URL in nginx.conf works and resolves to your current server 
3. Start the OCCI server:
```
 docker-compose -f docker-compose.prod.yml up -d
```
4. The stack should start, a certificate is obtained and the server would start much as in local development


## Open Toolchain Foundation    

This project is supported by the [Open Toolchain Foundation (OTF)](https://opentoolchain.org/) and has contributors from the [CadQuery](https://github.com/CadQuery/cadquery) and [Archiyou](https://archiyou.com) teams.

## Licence

Apache2


