// Azure App Service Plan + Web App for drone scoring application

@description('Location for the App Service')
param location string

@description('Base name for resources')
param baseName string

@description('Environment suffix')
param environment string = 'dev'

var appServicePlanName = 'asp-${baseName}-${environment}'
var webAppName = 'app-${baseName}-${environment}'

resource appServicePlan 'Microsoft.Web/serverfarms@2024-11-01' = {
  name: appServicePlanName
  location: location
  kind: 'linux'
  sku: {
    name: 'B1'
    tier: 'Basic'
  }
  properties: {
    reserved: true  // Required for Linux
  }
}

resource webApp 'Microsoft.Web/sites@2024-11-01' = {
  name: webAppName
  location: location
  kind: 'app,linux'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: appServicePlan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'PYTHON|3.11'
      alwaysOn: true
      ftpsState: 'Disabled'
      minTlsVersion: '1.2'
      appCommandLine: 'gunicorn --bind=0.0.0.0 --timeout 600 run:app'
    }
  }
}

@description('Web app default hostname')
output defaultHostName string = webApp.properties.defaultHostName

@description('Web app name')
output webAppName string = webApp.name

@description('Web app managed identity principal ID')
output principalId string = webApp.identity.principalId

@description('Web app resource ID')
output webAppId string = webApp.id
