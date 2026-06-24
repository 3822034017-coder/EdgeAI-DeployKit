# WebUI Product Flow Layout v1

本补丁按新的项目定位调整 workspace 主要页面：

- Pipeline 初始只保留模型上传 / 转换入口。
- 转换任务提交后弹出部署方式选择：本地推理 / 香橙派推理。
- 选择本地推理后，只显示本地任务向导、输入上传、本地推理、任务结果和报告入口。
- 选择香橙派推理后，只显示板端打包、同步、运行和板端报告流程。
- Overview 分成本地部署和香橙派部署两条路线，不再只展示香橙派流程。
- Infer Result 根据部署方式显示本地推理结果或香橙派推理结果。
- Reports 去掉大块 Reports & packages 列表，改为紧凑报告资产抽屉，支持浏览器预览和下载。
- Runtime 默认显示 Runtime output 和 Work queue & logs；项目助手和 Runtime capability 默认折叠。

后续 v2 应继续做：

- 输入面板按 task_type 细分：digit / classification / detection / llm_chat。
- Reports 根据 task_result.json 展示不同任务的可视化结果。
- 跨平台 release scaffold：Windows / macOS / Linux x86_64 / Linux arm64。
