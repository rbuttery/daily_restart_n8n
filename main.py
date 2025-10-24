from flask import Flask, request
import os
import traceback

from vm_restart import (
    get_required_env,
    perform_action,
)

app = Flask(__name__)

@app.route("/")
def restart_vm():
    try:
        project_id = get_required_env("PROJECT_ID")
        zone = get_required_env("ZONE")
        instance_name = get_required_env("INSTANCE_NAME")

        action = request.args.get("action", "restart").lower()
        if action not in {"restart", "stop", "start"}:
            return ("Invalid action. Use one of: restart, stop, start", 400)
        print(f"➡️ Action={action} instance={instance_name} zone={zone} project={project_id}")
        op_names = perform_action(action, project_id, zone, instance_name, wait=True)
        return {
            "status": "ok",
            "action": action,
            "project": project_id,
            "zone": zone,
            "instance": instance_name,
            "operations": op_names,
        }, 200

    except Exception as e:
        print("❌ ERROR restarting VM:")
        traceback.print_exc()
        return {"status": "error", "message": str(e)}, 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
