// LEDA Drone Scoring - Main Bicep Deployment
// Deploys: App Service, Computer Vision, Storage, Key Vault

@description('Azure region for all resources')
param location string = resourceGroup().location

@description('Project base name used in resource naming')
param projectName string = 'dronescoring'

@description('Environment (dev, staging, prod)')
@allowed(['dev', 'staging', 'prod'])
param environment string = 'dev'

// Step 1: Deploy App Service (creates managed identity, no external deps)
module appService 'modules/appservice.bicep' = {
  name: 'appServiceDeployment'
  params: {
    location: location
    baseName: projectName
    environment: environment
  }
}

// Step 2: Deploy Computer Vision (needs appService principalId)
module cognitiveServices 'modules/cognitiveservices.bicep' = {
  name: 'cognitiveServicesDeployment'
  params: {
    location: location
    baseName: projectName
    environment: environment
    webAppPrincipalId: appService.outputs.principalId
  }
}

// Step 3: Deploy Storage Account (needs appService principalId)
module storage 'modules/storage.bicep' = {
  name: 'storageDeployment'
  params: {
    location: location
    baseName: projectName
    environment: environment
    webAppPrincipalId: appService.outputs.principalId
  }
}

// Step 4: Deploy Key Vault (needs appService principalId)
module keyVault 'modules/keyvault.bicep' = {
  name: 'keyVaultDeployment'
  params: {
    location: location
    baseName: projectName
    environment: environment
    webAppPrincipalId: appService.outputs.principalId
  }
}

// Step 5: Configure App Settings after all resources are deployed
resource webAppSettings 'Microsoft.Web/sites/config@2024-11-01' = {
  name: 'app-${projectName}-${environment}/appsettings'
  properties: {
    AZURE_COMPUTER_VISION_ENDPOINT: cognitiveServices.outputs.endpoint
    AZURE_STORAGE_ACCOUNT_NAME: storage.outputs.storageAccountName
    AZURE_STORAGE_BLOB_ENDPOINT: storage.outputs.blobEndpoint
    AZURE_STORAGE_CONTAINER_NAME: 'drone-images'
    SCM_DO_BUILD_DURING_DEPLOYMENT: 'true'
    FLASK_ENV: environment == 'prod' ? 'production' : 'development'
  }
}

// Outputs
output webAppUrl string = 'https://${appService.outputs.defaultHostName}'
output webAppName string = appService.outputs.webAppName
output storageAccountName string = storage.outputs.storageAccountName
output computerVisionEndpoint string = cognitiveServices.outputs.endpoint
output keyVaultName string = keyVault.outputs.keyVaultName
