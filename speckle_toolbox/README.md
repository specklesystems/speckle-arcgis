<h1 align="center">
  <img src="https://user-images.githubusercontent.com/2679513/131189167-18ea5fe1-c578-47f6-9785-3748178e4312.png" width="150px"/><br/>
  Speckle | ArcGIS
</h1>
<h3 align="center">
    Connector for Spatial Data from ArcGIS
</h3>
<p align="center"><b>Speckle</b> is the data infrastructure for the AEC industry.</p><br/>

<p align="center"><a href="https://twitter.com/SpeckleSystems"><img src="https://img.shields.io/twitter/follow/SpeckleSystems?style=social" alt="Twitter Follow"></a> <a href="https://speckle.community"><img src="https://img.shields.io/discourse/users?server=https%3A%2F%2Fspeckle.community&amp;style=flat-square&amp;logo=discourse&amp;logoColor=white" alt="Community forum users"></a> <a href="https://speckle.systems"><img src="https://img.shields.io/badge/https://-speckle.systems-royalblue?style=flat-square" alt="website"></a> <a href="https://speckle.guide/dev/"><img src="https://img.shields.io/badge/docs-speckle.guide-orange?style=flat-square&amp;logo=read-the-docs&amp;logoColor=white" alt="docs"></a></p>
<p align="center">

# About Speckle

What is Speckle? Check our ![YouTube Video Views](https://img.shields.io/youtube/views/B9humiSpHzM?label=Speckle%20in%201%20minute%20video&style=social)

### Features

- **Object-based:** say goodbye to files! Speckle is the first object based platform for the AEC industry
- **Version control:** Speckle is the Git & Hub for geometry and BIM data
- **Collaboration:** share your designs collaborate with others
- **3D Viewer:** see your CAD and BIM models online, share and embed them anywhere
- **Interoperability:** get your CAD and BIM models into other software without exporting or importing
- **Real time:** get real time updates and notifications and changes
- **GraphQL API:** get what you need anywhere you want it
- **Webhooks:** the base for a automation and next-gen pipelines
- **Built for developers:** we are building Speckle with developers in mind and got tools for every stack
- **Built for the AEC industry:** Speckle connectors are plugins for the most common software used in the industry such as Revit, Rhino, Grasshopper, AutoCAD, Civil 3D, Excel, Unreal Engine, Unity, QGIS, ArcGIS (you are here), Blender and more!

### Try Speckle now!

Give Speckle a try in no time by:

- [![speckle XYZ](https://img.shields.io/badge/https://-speckle.xyz-0069ff?style=flat-square&logo=hackthebox&logoColor=white)](https://speckle.xyz) ⇒ creating an account at our public server
- [![create a droplet](https://img.shields.io/badge/Create%20a%20Droplet-0069ff?style=flat-square&logo=digitalocean&logoColor=white)](https://marketplace.digitalocean.com/apps/speckle-server?refcode=947a2b5d7dc1) ⇒ deploying an instance in 1 click

### Resources

- [![Community forum users](https://img.shields.io/badge/community-forum-green?style=for-the-badge&logo=discourse&logoColor=white)](https://speckle.community) for help, feature requests or just to hang with other speckle enthusiasts, check out our community forum!
- [![website](https://img.shields.io/badge/tutorials-speckle.systems-royalblue?style=for-the-badge&logo=youtube)](https://speckle.systems) our tutorials portal is full of resources to get you started using Speckle
- [![docs](https://img.shields.io/badge/docs-speckle.guide-orange?style=for-the-badge&logo=read-the-docs&logoColor=white)](https://speckle.guide/dev/) reference on almost any end-user and developer functionality

![Untitled](https://user-images.githubusercontent.com/2679513/132021739-15140299-624d-4410-98dc-b6ae6d9027ab.png)

## Repo Structure

This repo contains the ArcGIS plugin for Speckle 2.0. It is written in `python` and uses our fantastic [Python SDK](https://github.com/specklesystems/speckle-py). The [Speckle Server](https://github.com/specklesystems/Server) is providing all the web-facing functionality and can be found [here](https://github.com/specklesystems/Server).

> **Try it out!!**
> Although we're still in early development stages, we encourage you to try out the latest stable release.
> Just follow the instructions on this file, and head to the [Releases page](https://github.com/specklesystems/speckle-arcgis/releases) to download the necessary files and dependencies.
>
> **What can it do?**
>
> Currently, the plugin allows to receive the data from Speckle and send data from a AcrGIS Pro layers to a Speckle server using one of the accounts configured on your computer. It will extract all the features of that layer along side their properties. 
> The following geometry types are supported for now:
>
> - Point
> - Multipoint
> - Polyline 
> - Polygon
> - **More to come!!**
>
> If you have questions, you can always find us at our [Community forum](https://speckle.community)



## Developing

### Setup

Setup is adapted from [this tutorial](https://pro.arcgis.com/en/pro-app/2.8/arcpy/get-started/debugging-python-code.htm)


#### Dev Environment

For a better development experience in your editor, we recommend creating a [virtual environment in ArcGIS](https://pro.arcgis.com/en/pro-app/2.8/arcpy/get-started/work-with-python-environments.htm). In the venv, you'll just need to install `specklepy`. 

### Debugging

#### Visual Studio Code

In VS Code, you can use the built in python debugger. You'll need to create a debug configuration by creating a `launch.json` file.

![Create Debug Config](https://user-images.githubusercontent.com/2316535/129895259-3b9ede24-a898-4dbd-86df-0d15f19a2714.png)

Select the "Python" -> "Remote Attach" option. Your `launch.json` should look like this:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Attach using Process Id",
      "type": "python",
      "request": "attach",
      "processId": "${command:pickProcess}",
      "justMyCode": true
    }
  ]
}
```

To start debugging, you'll need to first launch ArcGIS. Once it's running, run your debug `Python: Remote Attach` configuration and select ArcGISPro.exe from the dropdown.

For now, the breakpoints are only hit in the _init_ part of your Toolbox classes, but it's a [known limitation](https://community.esri.com/t5/python-questions/has-anyone-successfully-attached-the-vscode/td-p/1092605)

Enjoy!
