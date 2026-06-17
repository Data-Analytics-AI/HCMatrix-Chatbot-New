# HCMatrix Chatbot CI/CD Workflow Guide

This document outlines the end-to-end development lifecycle for the HCMatrix Chatbot, from writing code locally to deploying to the production Kubernetes cluster.

---

## Phase 1: Local Development & Testing
Always start by developing and testing your features locally before pushing to GitHub.

1. **Pull Latest Changes:** Ensure you are up to date with the main branch.
   ```bash
   git pull origin main
   ```
2. **Create a Feature Branch:** Never work directly on `main`. Create a new branch for your task.
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Setup Secrets (`.env`):**
   - Run `cp .env.example .env`
   - Fill in your `.env` with the necessary database and Azure OpenAI credentials.
4. **Run Local Server:**
   - Install dependencies: `pip install -r requirements.txt`
   - Start Uvicorn: `python main.py`
5. **Test Your Code:** Use Postman or the provided `curl` commands in `LOCAL_TESTING.md` to ensure your changes work as expected.

---

## Phase 2: Deploying to Staging (Development Environment)

Once your local testing is successful, it is time to deploy to the staging environment (`feature_test_workflow` or your custom feature branch).

1. **Commit and Push:**
   ```bash
   git add .
   git commit -m "feat: Describe your changes"
   git push origin feature/your-feature-name
   ```
2. **Trigger the Staging CI/CD Pipeline:**
   - Open GitHub in your browser and go to the **Actions** tab.
   - Click on the **Integration Tests and Deployment** workflow on the left sidebar.
   - Click the **Run workflow** dropdown on the right.
   - Select your branch (`feature/your-feature-name`) from the dropdown.
   - Click the green **Run workflow** button.
3. **What happens under the hood?**
   - GitHub Actions runs `flake8` to check for syntax/linting errors.
   - It builds the Docker image and pushes it to `hcmatrixmoved.azurecr.io`.
   - Because you selected a non-main branch, the pipeline sets `DEPLOY_ENV=development` and updates the development AKS cluster pods.

---

## Phase 3: Deploying to Production

Once the staging environment has been thoroughly QA tested, you are ready to deploy to the live production cluster.

1. **Create a Pull Request:**
   - Go to the GitHub repository.
   - Click **Pull requests** > **New pull request**.
   - Set the `base` branch to `main` and the `compare` branch to your feature branch (`feature/your-feature-name`).
   - Fill out the PR description and request reviews from the Lead Developer.
2. **Merge the Pull Request:**
   - Once approved, click **Merge pull request** to bring your code into `main`.
3. **Trigger the Production CI/CD Pipeline:**
   - Go to the **Actions** tab in GitHub.
   - Click on the **Integration Tests and Deployment** workflow.
   - Click **Run workflow**, ensure the branch is set to `main`.
   - Click the green **Run workflow** button.
4. **What happens under the hood?**
   - The pipeline detects that it is running on the `main` branch.
   - It sets `DEPLOY_ENV=production`.
   - It pushes the production-tagged image to ACR and updates the production Kubernetes environment on the `hcmatrix-aks-moved` cluster.

---

## Troubleshooting the Pipeline
- **Pipeline fails at Linting:** If `flake8` fails, check the GitHub Actions logs. You likely have unused imports or messy formatting in your Python files. Fix them locally, commit, and push again.
- **Docker Build Fails:** Ensure there are no unlisted packages in your `requirements.txt`.
- **Deployment Fails:** Check your AKS connection and ensure the ACR credentials stored in GitHub Secrets are up to date.
