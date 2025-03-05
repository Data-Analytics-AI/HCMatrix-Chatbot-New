# **HCMatrix AKS Deployment Guide**

This documentation outlines the setup of our Azure Kubernetes Service (AKS) cluster, Azure Container Registry (ACR), and necessary configurations. All configurations are done outside GitHub Actions to ensure efficiency in deployments.

## **1. Create Azure Container Registry (ACR)**

```sh
az acr create --resource-group HCM-Production --name hcmatrix --sku Standard --location eastus
```

## **2. Login to ACR**

```sh
az acr login --name hcmatrix
```

## **3. Create Azure Kubernetes Service (AKS) Cluster**

```sh
az aks create --resource-group HCM-Production --name hcmatrix-aks --node-count 3 --enable-cluster-autoscaler --min-count 1 --max-count 5 --generate-ssh-keys --attach-acr hcmatrix
```

## **4. Configure kubectl to Connect to AKS**

```sh
az aks get-credentials --resource-group HCM-Production --name hcmatrix-aks
```

## **5. Create Kubernetes Secrets**

### **5.1 Create Application Secrets**

```sh
kubectl create secret generic hcm-secrets \
  --from-literal=CLIENT_SECRET="your-client-secret" \
  --from-literal=KEY_VAULT_NAME="your-key-vault-name"
```

### **5.2 Create ACR Image Pull Secret**

```sh
kubectl create secret docker-registry acr-secret \
  --docker-server=hcmatrix.azurecr.io \
  --docker-username=<your-acr-username> \
  --docker-password=<your-acr-password> \
  --docker-email=<your-email>
```

## **6. Deploy Kubernetes Resources**

Apply the Kubernetes deployment and service YAML files:

```sh
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
```

## **7. Verify Deployments**

```sh
kubectl get pods -o wide
kubectl get svc
kubectl get nodes
```

## **8. Enable Autoscaling**

```sh
kubectl autoscale deployment hcmatrix-k8s-deployment --cpu-percent=50 --min=2 --max=10
```

This ensures the number of pods automatically scales based on CPU usage.

## **9. Configure Horizontal Pod Autoscaler (HPA)**

```sh
kubectl get hpa
```

Verify that the HPA is active and adjusting pods as needed.

---

### **Notes**

- The cluster name is **hcmatrix-aks**.
- ACR and AKS are linked to allow pulling images without requiring additional authentication.
- Scaling for both nodes and pods is configured during AKS creation and with `kubectl autoscale`.
- GitHub Actions will only handle deployments; infrastructure changes remain outside CI/CD.

This guide should be followed for setting up new environments or troubleshooting AKS and ACR configurations.

