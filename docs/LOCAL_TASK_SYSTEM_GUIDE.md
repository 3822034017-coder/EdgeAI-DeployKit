# EdgeAI Local Task System Foundation

本补丁新增 `model_task.json` 任务配置系统。

```bash
edgeai task-init --package outputs/packages/mobilenet_v3_small_imagenet_local --task-type auto
edgeai task-info --package outputs/packages/mobilenet_v3_small_imagenet_local
```

如果 CLI 自动补丁未生效：

```bash
python scripts/edgeai_task_init.py --package outputs/packages/mobilenet_v3_small_imagenet_local --task-type auto
```

支持任务类型：`digit_classification`、`image_classification`、`object_detection`、`segmentation`、`text_classification`、`llm_chat`、`unknown`。
