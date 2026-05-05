// Azure Cognitive Services - Computer Vision for drone image analysis

@description('Location for the Cognitive Services account')
param location string

@description('Base name for the resource')
param baseName string

@description('Environment suffix')
param environment string = 'dev'

@description('Principal ID of the web app managed identity for RBAC')
param webAppPrincipalId string = ''

var cognitiveServicesName = 'cv-${baseName}-${environment}'

resource computerVision 'Microsoft.CognitiveServices/accounts@2025-06-01' = {
  name: cognitiveServicesName
  location: location
  kind: 'ComputerVision'
  sku: {
    name: 'S1'
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    customSubDomainName: cognitiveServicesName
    publicNetworkAccess: 'Enabled'
    // Allow key-based auth during development; tighten for production
    disableLocalAuth: false
    networkAcls: {
      defaultAction: 'Allow'
    }
  }
}

// Cognitive Services User role for the web app managed identity
var cognitiveServicesUserRole = 'a97b65f3-24c7-4388-baec-2e87135dc908'

resource cognitiveServicesRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(webAppPrincipalId)) {
  name: guid(computerVision.id, webAppPrincipalId, cognitiveServicesUserRole)
  scope: computerVision
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', cognitiveServicesUserRole)
    principalId: webAppPrincipalId
    principalType: 'ServicePrincipal'
  }
}

@description('Computer Vision endpoint URL')
output endpoint string = computerVision.properties.endpoint

@description('Computer Vision resource name')
output name string = computerVision.name

@description('Computer Vision resource ID')
output resourceId string = computerVision.id
