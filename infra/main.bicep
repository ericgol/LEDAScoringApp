// LEDA Drone Scoring - Main Bicep Deployment
// Deploys: App Service, Computer Vision, Storage, Key Vault

@description('Azure region for all resources')
param location string = resourceGroup().location

@description('Project base name used in resource naming')
param projectName string = 'dronescoring'

@description('Environment (dev, staging, prod)')
@allowed(['dev', 'staging', 'prod'])
param environment string = 'dev'

// Step 1: Deploy App Service (creates managed identity)
module appService 'modules/appservice.bicep' = {
  name: 'appServiceDeployment'
  params: {
    location: location
    baseName: projectName
    environment: environment
    computerVisionEndpoint: cognitiveServices.outputs.endpoint
    storageAccountName: storage.outputs.storageAccountName
    storageBlobEndpoint: storage.outputs.blobEndpoint
  }
}

// Step 2: Deploy Computer Vision
module cognitiveServices 'modules/cognitiveservices.bicep' = {
  name: 'cognitiveServicesDeployment'
  params: {
    location: location
    baseName: projectName
    environment: environment
    webAppPrincipalId: appService.outputs.principalId
  }
}

// Step 3: Deploy Storage Account
module storage 'modules/storage.bicep' = {
  name: 'storageDeployment'
  params: {
    location: location
    baseName: projectName
    environment: environment
    webAppPrincipalId: appService.outputs.principalId
  }
}

// Step 4: Deploy Key Vault
module keyVault 'modules/keyvault.bicep' = {
  name: 'keyVaultDeployment'
  params: {
    location: location
    baseName: projectName
    environment: environment
    webAppPrincipalId: appService.outputs.principalId
  }
}

// Outputs
output webAppUrl string = 'https://${appService.outputs.defaultHostName}'
output webAppName string = appService.outputs.webAppName
output storageAccountName string = storage.outputs.storageAccountName
output computerVisionEndpoint string = cognitiveServices.outputs.endpoint
output keyVaultName string = keyVault.outputs.keyVaultName
