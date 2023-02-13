# About OCCI

Open CAD Components Interface (OCCI) brings parametric components to all by using script CAD engines like CadQuery and Archiyou. Script CAD is very suitable to deliver platform-independant 'open design' parametric CAD content and we hope that OCCI will contribute to that. 

The simplest way to try OCCI is with our [https://github.com/occi-cad/occi-freecad-plugin](FreeCAD plugin). You can find the [https://github.com/occi-cad/occi-cad-spec](OCCI design principles and spec here).

# OCCI server

This repository contains a reference server stack that allows CAD scripts (currently we support CadQuery and Archiyou scripts) to be quickly turned into an OCCI API. 

Use cases:
* You have a CAD script for which you want to build a viewing/configurator web-application
* You have a lot of CAD scripts that you want to share with other online

## Developer Quickstart

The stack is fully dockerized. To start up a local OCCI server with a default CadQuery worker:

1. Add a .env file to the main directory based on env.example
2. Add scripts into the 'scriptlibrary' directory in format ./scriptlibrary/{org}/{name}/{version}/{name}.py|js and {name}.json for the config file. There is an [https://github.com/occi-cad/scriptlibrary](OCCI example library) to get you started. Make sure you are in the root directory:
```
git clone https://github.com/occi-cad/scriptlibrary
```
3. Go into a terminal and run:

``` 
    docker-compose up
```
4. Once Go to localhost:8090 to see the OCCI server basic information
5. Get your first parametric model from OCCI example library. Go to url: http://localhost:8090/tests/box. This will give you a parametric box in STEP file. Use http://localhost:8090/tests/box?output=full to see more information. 

## OCCI API docs

We have generated API docs. Go to http://localhost:8090/docs on your OCCI server for all query possibilities. 

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


