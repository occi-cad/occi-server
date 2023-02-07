# OCCI-API

Open CAD Components Interface (OCCI) brings parametric components to all by using ScriptCAD engines like CadQuery, OpenSCAD and Archiyou. 

The OCCI standard enables the creation of Libraries of CADScripts. Scripts can be configured by Parameters and Parameter Presets and are executed by the OCCI execution engines and returned as a 3d Model in various formats (STEP, STL, GLTF). 

CAD designers can use the OCCI FreeCAD plugin to access a lot of parametric CAD components from a curated list of Libraries. For developers OCCI offers REST API’s to start making applications with parametric CAD content. 

## Developer Quickstart

The stack is fully dockerized. You can either set up the full stack locally, or set up the storage layers (rabbitmq and redis) on some external server and run the Python scripts locally. 

1. Add a .env file to the main directory based on env.example
2. Go into a terminal and run:

``` 
    docker-compose up
```

You have now all the infrastructure available:
* REST API: localhost:8090
* RabbitMQ: localhost:5672 and dashboard on 15672
* Redis: localhost:6379

## Production 

```
 docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```


## Open Toolchain Foundation    

This project is supported by the [Open Toolchain Foundation (OTF)](https://opentoolchain.org/) and has contributors from the [CadQuery](https://github.com/CadQuery/cadquery) and [Archiyou](https://archiyou.com) teams.


