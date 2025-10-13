from flask import Flask
from googleapiclient import discovery
from google.auth import default
import os, traceback

app = Flask(__name__)

@app.route("/")
def restart_vm():
    try:
        creds, project = default()
        project_id = os.getenv("PROJECT_ID")
        zone = os.getenv("ZONE")
        instance_name = os.getenv("INSTANCE_NAME")

        service = discovery.build('compute', 'v1', credentials=creds)
        print(f"🔁 Restarting {instance_name} in {zone} ({project_id})")

        # Try stopping the VM
        try:
            service.instances().stop(project=project_id, zone=zone, instance=instance_name).execute()
            print("🛑 VM stop requested")
        except Exception as e:
            print(f"⚠️ Stop skipped: {e}")

        # Always try to start it
        service.instances().start(project=project_id, zone=zone, instance=instance_name).execute()
        print("🚀 VM start requested")

        return f"✅ Restarted VM '{instance_name}' in zone '{zone}' (project: {project_id})", 200

    except Exception as e:
        print("❌ ERROR restarting VM:")
        traceback.print_exc()
        return f"Error restarting VM: {e}", 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
