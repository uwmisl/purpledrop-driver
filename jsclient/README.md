# PurpleDrop Control Interface

This is a javascript app to provide a simple UI for controlling the purple drop. 

A live view can display a video feed of the purpledrop, with a rendering of the electrode grid overlayed to show which electrodes are active. Electrodes can be turned on and off with the mouse and keyboard. 

Click the "Parameters" button to adjust PurpleDrop configuration parameters. 

This application is served by `pdserver` whenever it is running. 

## Development 

Building the webpack bundle requires node, and yarn (or npm). 

To install dependencies: 

`yarn install`

To build the distribution bundle:

`yarn build`

To run the development server locally:

`yarn start`


