Put the full ImageNet 1000-class label file here as:

  imagenet_classes.txt

The file must contain one class label per line, using 0-based ImageNet order.
If the file is missing, EdgeAI keeps numeric top1/top5 indices and only uses a
small fallback mapping for common demo classes such as cat labels.
