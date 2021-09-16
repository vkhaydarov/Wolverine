# vkhaydarov-planteye-wolverine

PlantEye/Wolverine is a tool for image data collection that received data from PlantEye/Vision and saves them locally. The component requests frames with a given time interval, which endpoint response with the frame and metadata will be received and saved into given folders.

## Usage
To run the script be sure that config-file (config.yaml) is proper and then run the script:
```bash
python3 main.py
```

## Configure
Create a config file (config.yaml) according to the following structure:
```yaml
---
storage:
  interval: 1000
  filename_mask: timestamp
  frame_folder: /home/user/Desktop/data/frames
  metadata_folder: /home/user/Desktop/data/metadata
api:
  endpoint: http://localhost:5000/
```
Please provide the time interval in milliseconds how often the image should be requested from PlantEye/Vision.
The parameter filename_mask defines the filename under which the images and metadata files will be saved.
Images and metadata files can be stored at the same as well as in separated folders, what can be specified by corresponding parameters.
The parameter endpoint denotes the host of the PlantEye/Vision endpoint. Please bear in mind that request name "/get_frame" is added by default.

## Requirements
To install requirements use the following command:
```bash
pip3 install -r requirements.txt
```

## License
Valentin Khaydarov (valentin.khaydarov@tu-dresden.de)\
Process-To-Order-Lab\
TU Dresden