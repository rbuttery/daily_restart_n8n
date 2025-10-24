# 🌀 GCP VM Daily Restart — Deployment Guide

This project deploys a **Cloud Run service** that restarts a GCP VM instance daily using **Cloud Scheduler**.

---

## ⚙️ 1. Authenticate and Configure GCloud

### Login to GCP (user and ADC)
```powershell
gcloud auth login
gcloud auth application-default login
gcloud auth application-default set-quota-project n8n-automations-450821
gcloud config set project n8n-automations-450821
```

### Verify authentication
```powershell
gcloud auth list
```

### Check current project
```powershell
gcloud config list project
```

---

## 🏗️ 2. Artifact Registry Setup

### Create a Docker repository
```powershell
gcloud artifacts repositories create vm-restart-repo `
  --repository-format=docker `
  --location=us-central1 `
  --description="Docker repo for VM restart service"
```

### Enable Artifact Registry API
```powershell
gcloud services enable artifactregistry.googleapis.com
```

### Configure local Docker authentication
```powershell
gcloud auth configure-docker us-central1-docker.pkg.dev
```

---

## 🔐 3. Grant Permissions

### Allow Cloud Build to push images
```powershell
gcloud projects add-iam-policy-binding n8n-automations-450821 `
  --member="serviceAccount:669887151122@cloudbuild.gserviceaccount.com" `
  --role="roles/artifactregistry.writer"
```

### Allow Compute Engine default account (used by build) to push images
```powershell
gcloud projects add-iam-policy-binding n8n-automations-450821 `
  --member="serviceAccount:669887151122-compute@developer.gserviceaccount.com" `
  --role="roles/artifactregistry.writer"
```

### Allow runtime to manage the VM (critical)
The Cloud Run runtime service account must be able to stop/start the VM. Grant it Compute Instance Admin.

```powershell
gcloud projects add-iam-policy-binding n8n-automations-450821 `
  --member="serviceAccount:669887151122-compute@developer.gserviceaccount.com" `
  --role="roles/compute.instanceAdmin.v1"
```

---

## 🚀 4. Build and Deploy

### Build and push the Docker image
```powershell
gcloud builds submit --tag us-central1-docker.pkg.dev/n8n-automations-450821/vm-restart-repo/vm-restart
```

### Deploy to Cloud Run
```powershell
# PowerShell note: wrap the value to avoid comma-splitting
gcloud run deploy vm-restart `
  --image us-central1-docker.pkg.dev/n8n-automations-450821/vm-restart-repo/vm-restart `
  --region=us-central1 `
  --allow-unauthenticated `
  --set-env-vars "PROJECT_ID=n8n-automations-450821,ZONE=us-central1-c,INSTANCE_NAME=instance-20250804-155059"
```

After deployment, note the **Service URL** printed in the output.  
Example:
```
https://vm-restart-xxxxx-uc.a.run.app
```

---

## 🧪 5. Test the Service

### Trigger a manual restart
```powershell
curl https://vm-restart-xxxxx-uc.a.run.app
```

Expected output:
```
✅ Restarted VM 'instance-20250804-155059' in zone 'us-central1-c' (project: n8n-automations-450821)
```

---

## 🕒 6. Schedule Daily Restarts

### Create a Cloud Scheduler job (runs daily at 5 AM UTC)
```powershell
$CLOUD_RUN_URL = (gcloud run services describe vm-restart --region=us-central1 --format="value(status.url)")
gcloud scheduler jobs create http restart-vm-daily `
  --schedule="0 5 * * *" `
  --uri="$CLOUD_RUN_URL" `
  --http-method=GET
```

---

## 🔍 7. View Logs

### Cloud Run logs
```powershell
gcloud run logs read vm-restart --region=us-central1
```

### Compute Engine activity (stop/start events)
```powershell
gcloud logging read 'protoPayload.methodName="v1.compute.instances.start"' --limit 10
```

---

## 🧹 8. Optional Cleanup

To remove all resources later:
```powershell
gcloud run services delete vm-restart --region=us-central1
gcloud artifacts repositories delete vm-restart-repo --location=us-central1
```

---

## 🔁 9. Quick Update Command (Optional)

After editing your code, rebuild + redeploy in one go:
```powershell
gcloud builds submit --tag us-central1-docker.pkg.dev/n8n-automations-450821/vm-restart-repo/vm-restart && `
gcloud run deploy vm-restart `
  --image us-central1-docker.pkg.dev/n8n-automations-450821/vm-restart-repo/vm-restart `
  --region=us-central1 `
  --allow-unauthenticated `
  --set-env-vars "PROJECT_ID=n8n-automations-450821,ZONE=us-central1-c,INSTANCE_NAME=instance-20250804-155059"
```

---

## 🔧 Local testing

Run the Flask app locally (it will try to call GCP APIs):

```powershell
$env:PROJECT_ID = "n8n-automations-450821"
$env:ZONE = "us-central1-c"
$env:INSTANCE_NAME = "instance-20250804-155059"
python .\main.py
```

Then in another shell:

```powershell
curl "http://localhost:8080/?action=restart"
```

If you haven't run ADC login yet, do:

```powershell
gcloud auth application-default login
gcloud auth application-default set-quota-project n8n-automations-450821
```

---

## 📜 Single-script usage (for future updates)

You can run the logic outside of Flask/Cloud Run using `vm_restart.py`.

Env vars (or pass flags):

```powershell
$env:PROJECT_ID = "n8n-automations-450821"
$env:ZONE = "us-central1-c"
$env:INSTANCE_NAME = "instance-20250804-155059"
```

Run with defaults (restart + wait):

```powershell
python .\vm_restart.py
```

Specify action/flags:

```powershell
python .\vm_restart.py --action start
python .\vm_restart.py --action stop
python .\vm_restart.py --action restart --no-wait
python .\vm_restart.py --project-id n8n-automations-450821 --zone us-central1-c --instance instance-20250804-155059
```

Authentication uses Application Default Credentials:

```powershell
gcloud auth application-default login
gcloud auth application-default set-quota-project n8n-automations-450821
```
