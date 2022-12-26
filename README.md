# OCCI-API

Open CAD Components Interface (OCCI) brings parametric components to all by using ScriptCAD engines like CadQuery, OpenSCAD and Archiyou. 

The OCCI standard enables the creation of Libraries of CADScripts. Scripts can be configured by Parameters and Parameter Presets and are executed by the OCCI execution engines and returned as a 3d Model in various formats (STEP, STL, GLTF). 

CAD designers can use the OCCI FreeCAD plugin to access a lot of parametric CAD components from a curated list of Libraries. For developers OCCI offers REST API’s to start making applications with parametric CAD content. 

## Definitions

* Component: A 3d object. A part can be represented in multiple part formats
* Component bundle: A collection of files ( or a zip archive), containing multiple representations of a Part.  Typical examples might include STEP, STL, a 3d javascript mesh, or an HTML viewer. 
* CADScript: A set of source code that, when executed, will generate one or more Components .  Specifically, a Component , combined with a Parameter Set, will produce a Part
* User: a person who seeks to make a Component using a CADScript
* Author: a person who creates a Component , typically using a Code-CAD framework like ArchiYou, CadQuery, or OpenSCAD
* Framework Developer: A developer who is familiar with a Code-CAD framework, like ArchiYou, CadQuery, or OpenSCAD
* Parameter: a user input having a value and a type, used to collect design values from a User
* Parameter Preset: a set of parameter values provided by an Author, that will produce a specific Part. Used so that the Author can guide users as they create Components using a CADScript
* Job: the activity of executing the code in a Component , and producing one or more Components 
* Organization: One or more users who control  CADScripts or Components . Organizations allow grouping Components and Component for the purposes of access control and/or distribution
* Executor: software that can execute  Job. An executor contains all of the dependencies needed to run the CADScript that references it.  Example: CadQuery might provide a docker image with CQ installed to form an Executor.
* Executor Service: A software process that exposes a service that can find Executors to run jobs. Example: A web process might accept a URL, and use the CadQuery executor to run the CadScript and produce Components
* Client: A software process being run by a User.
* OCCI Client: Software that allows a User to access CADScripts and Components  in a Component Library. OCCI Clients will be available in many source languages.
* Component Library: Stores Components and CADScript, stored in such a way that Clients and Executors can find them.
* Publish: saving the files from a Component, typically with a reference to the CADScript and the Executor that generated it,  into a Component Library


