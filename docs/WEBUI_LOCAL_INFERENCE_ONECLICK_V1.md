# WebUI Local Inference One-click Flow v1

This note defines the productized local inference loop used by the WebUI.

## Goal

The early UI exposed several separate debugging buttons. The product flow keeps
those lower-level actions available for troubleshooting, but gives ordinary
users a single local inference path:

```text
Upload / Convert Model -> Select Local Inference -> Upload Test Input -> Run Local Inference -> View Result -> Download Report
```

## Backend Sequence

When the user starts the one-click local inference flow, the backend runs:

1. `Analyze`
2. `Task Init`
3. `Prepare Input`
4. `Local Run`
5. `Task Render`
6. `Report`

The flow produces package-local artifacts under:

```text
outputs/packages/<package_name>/
```

Expected artifacts include:

- `model_signature.json`
- `model_task.json`
- `input.npy`
- `preprocess.json`
- `local_result.json`
- `task_result.json`
- `report.md`
- `report.pdf`

## UI Behavior

The WebUI should:

- show which stage is running
- show stage success or failure
- show whether required artifacts were generated
- preview `task_result.json` in a task-aware format
- link to the generated Markdown/PDF report

The manual debug buttons can remain for development, but the main user action
should be the one-click local inference flow.

