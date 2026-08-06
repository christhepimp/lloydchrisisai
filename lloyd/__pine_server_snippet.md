Server wiring note (applied in server.py):
- from lloyd.pine_client import get_pine
- pine = get_pine(); lloyd.pine = pine
- GET /pine/status /pine/features
- POST /pine/connect /pine/disconnect /pine/call /pine/sync
- /status includes pine.status_dict()
