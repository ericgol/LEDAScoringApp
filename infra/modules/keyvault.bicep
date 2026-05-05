// Azure Key Vault for secrets management

@description('Location for Key Vault')
param location string

@description('Base name for the resource')
param baseName string

@description('Environment suffix')
param environment string = 'dev'

@description('Principal ID of the web app managed identity')
param webAppPrincipalId string = ''

var keyVaultName = 'kv-${baseName}-${environment}'

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: length(keyVaultName) > 24 ? substring(keyVaultName, 0, 24) : keyVaultName
  location: location
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 90
    // Do NOT disable purge protection per Azure best practices
    enablePurgeProtection: true
  }
}

// Key Vault Secrets User role for the web app
var keyVaultSecretsUserRole = '4633458b-17de-408a-b874-0445c86b69e6'

resource kvRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(webAppPrincipalId)) {
  name: guid(keyVault.id, webAppPrincipalId, keyVaultSecretsUserRole)
  scope: keyVault
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', keyVaultSecretsUserRole)
    principalId: webAppPrincipalId
    principalType: 'ServicePrincipal'
  }
}

@description('Key Vault name')
output keyVaultName string = keyVault.name

@description('Key Vault URI')
output keyVaultUri string = keyVault.properties.vaultUri
