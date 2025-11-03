Web App Deployment steps:

1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Open git bash or terminal

3. Navigate to C:/<DRIVE>/ca-gcch-test-app

4. Make the deployment script executable:
   ```bash
   chmod +x scripts/deploy-py-gcch-app.sh
   ```

5. Run the Python deployment script:
   ```bash
   ./scripts/deploy-py-gcch-app.sh
   ```

6. Configure environment variables in Azure App Service:
   Go to your App Service → Configuration → Application Settings and add:

   ```
   PORT=8080
   CONNECTION_STRING="<your-azure-communication-services-connection-string>"
   ACS_RESOURCE_PHONE_NUMBER="<your-phone-number>"
   CALLBACK_URI="<your-callback-uri>"
   COGNITIVE_SERVICES_ENDPOINT="<your-cognitive-services-endpoint>"
   ```

   **Note**: The Python runtime (PYTHON|3.11) is automatically configured by the deployment script.