// Azure Storage Account for drone scoring images
// Uses RBAC-only access (shared key disabled)

@description('Location for the storage account')
param location string

@description('Base name for the storage account (will be sanitized)')
param baseName string

@description('Environment suffix')
param environment string = 'dev'

@description('Principal ID of the web app managed identity for RBAC')
param webAppPrincipalId string = ''

// Storage account names must be 3-24 chars, lowercase alphanumeric only
var storageAccountName = toLower(replace('st${baseName}${environment}', '-', ''))

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: length(storageAccountName) > 24 ? substring(storageAccountName, 0, 24) : storageAccountName
  location: location
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
  properties: {
    accessTier: 'Hot'
    allowSharedKeyAccess: false
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    networkAcls: {
      defaultAction: 'Allow'
      bypass: 'AzureServices'
    }
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: storageAccount
  name: 'default'
}

resource droneImagesContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobService
  name: 'drone-images'
  properties: {
    publicAccess: 'None'
  }
}

resource sessionDataContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobService
  name: 'session-data'
  properties: {
    publicAccess: 'None'
  }
}

// Storage Blob Data Contributor role for the web app managed identity
var storageBlobDataContributorRole = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'

resource storageRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(webAppPrincipalId)) {
  name: guid(storageAccount.id, webAppPrincipalId, storageBlobDataContributorRole)
  scope: storageAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageBlobDataContributorRole)
    principalId: webAppPrincipalId
    principalType: 'ServicePrincipal'
  }
}

@description('Storage account name')
output storageAccountName string = storageAccount.name

@description('Storage account blob endpoint')
output blobEndpoint string = storageAccount.properties.primaryEndpoints.blob

@description('Storage account resource ID')
output storageAccountId string = storageAccount.id
