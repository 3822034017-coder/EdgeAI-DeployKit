# edgeai/model_config.py

MODEL_CONFIG = {

    "mnist": {
        "input_name": "Input3",
        "shape": "Input3:1,1,28,28"
    },

    "mobilenetv2": {
        "input_name": "input",
        "shape": "input:1,3,224,224"
    },

    "resnet18": {
        "input_name": "data",
        "shape": "data:1,3,224,224"
    },

    "yolov5n": {
        "input_name": "images",
        "shape": "images:1,3,640,640"
    }
}
