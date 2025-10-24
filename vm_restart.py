import argparse
import os
import sys
import time
import traceback
from typing import List

from googleapiclient import discovery
from google.auth import default


def get_required_env(var_name: str) -> str:
    value = os.getenv(var_name)
    if not value:
        raise ValueError(f"Missing required environment variable: {var_name}")
    return value


def wait_for_zone_operation(
    compute,
    project_id: str,
    zone: str,
    op_name: str,
    timeout_sec: int = 600,
    poll_sec: int = 5,
):
    """Polls a zonal operation until it reaches DONE or times out."""
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        result = compute.zoneOperations().get(
            project=project_id, zone=zone, operation=op_name
        ).execute()
        status = result.get("status")
        if status == "DONE":
            if "error" in result:
                errors = result["error"].get("errors", [])
                messages = ", ".join(e.get("message", str(e)) for e in errors)
                raise RuntimeError(
                    f"Operation {op_name} finished with errors: {messages}"
                )
            return
        time.sleep(poll_sec)
    raise TimeoutError(
        f"Operation {op_name} did not complete within {timeout_sec} seconds"
    )


def perform_action(
    action: str,
    project_id: str,
    zone: str,
    instance_name: str,
    wait: bool = True,
) -> List[str]:
    """Execute stop/start/restart for an instance. Returns operation names."""
    creds, _ = default()
    compute = discovery.build("compute", "v1", credentials=creds)

    op_names: List[str] = []
    if action in ("restart", "stop"):
        try:
            stop_op = compute.instances().stop(
                project=project_id, zone=zone, instance=instance_name
            ).execute()
            stop_name = stop_op.get("name")
            print(f"🛑 Stop requested: operation={stop_name}")
            if wait:
                wait_for_zone_operation(compute, project_id, zone, stop_name)
                print("🛑 Stop completed")
            op_names.append(stop_name)
        except Exception as e:
            # If already stopped, continue for restart/start
            print(f"⚠️ Stop error (continuing if restart/start): {e}")

    if action in ("restart", "start"):
        start_op = compute.instances().start(
            project=project_id, zone=zone, instance=instance_name
        ).execute()
        start_name = start_op.get("name")
        print(f"🚀 Start requested: operation={start_name}")
        if wait:
            wait_for_zone_operation(compute, project_id, zone, start_name)
            print("🚀 Start completed")
        op_names.append(start_name)

    return op_names


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Stop/start/restart a GCE VM using ADC credentials."
    )
    parser.add_argument(
        "-a",
        "--action",
        choices=["restart", "stop", "start"],
        default="restart",
        help="Action to perform (default: restart)",
    )
    parser.add_argument(
        "-p",
        "--project-id",
        default=os.getenv("PROJECT_ID"),
        help="GCP project ID (or set env PROJECT_ID)",
    )
    parser.add_argument(
        "-z",
        "--zone",
        default=os.getenv("ZONE"),
        help="GCE zone (or set env ZONE)",
    )
    parser.add_argument(
        "-i",
        "--instance",
        default=os.getenv("INSTANCE_NAME"),
        help="GCE instance name (or set env INSTANCE_NAME)",
    )
    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Do not wait for operations to reach DONE",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    try:
        args = parse_args(argv)
        if not args.project_id:
            raise ValueError("--project-id is required or set env PROJECT_ID")
        if not args.zone:
            raise ValueError("--zone is required or set env ZONE")
        if not args.instance:
            raise ValueError("--instance is required or set env INSTANCE_NAME")

        print(
            f"➡️ Action={args.action} instance={args.instance} zone={args.zone} project={args.project_id}"
        )
        ops = perform_action(
            action=args.action,
            project_id=args.project_id,
            zone=args.zone,
            instance_name=args.instance,
            wait=not args.no_wait,
        )
        print({
            "status": "ok",
            "action": args.action,
            "project": args.project_id,
            "zone": args.zone,
            "instance": args.instance,
            "operations": ops,
        })
        return 0
    except Exception as e:
        print("❌ ERROR:")
        traceback.print_exc()
        print({"status": "error", "message": str(e)})
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
