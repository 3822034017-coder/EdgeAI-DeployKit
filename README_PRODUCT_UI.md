# EdgeAI-DeployKit Product WebUI

This package replaces the early Streamlit-style prototype with a product-oriented architecture:

- `product-ui/`: Next.js + Tailwind front-end control plane.
- `backend/`: FastAPI bridge that scans artifacts and launches allowlisted `edgeai` jobs.
- `docker-compose.product.yml`: optional two-service startup for web + API.

The existing `webui/app.py` can remain for compatibility. This UI is a separate product layer.
