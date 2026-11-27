#!/usr/bin/env bash
# create-env.sh: fill .env from your Microsoft IQ lab (Strandvik Drives).
#
# Used by both roles (business and builder). It signs you in once (device code) if
# needed, finds your lab resource group, reads the resource names and endpoints, and
# writes them to .env in this folder. It only reads; it changes nothing in Azure.
#
#   bash create-env.sh                 # find the lab resource group automatically
#   bash create-env.sh <resource-group> # or name it
#
# Windows without bash: use create-env.ps1 (same result).
set -euo pipefail

HACK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$HACK_DIR/.env"
RG="${1:-${AZURE_RESOURCE_GROUP:-}}"
LAB_TAG="15_Microsoft_IQ"

# Git Bash on Windows: keep /subscriptions/... arguments as they are.
export MSYS_NO_PATHCONV=1
export AZURE_CORE_ONLY_SHOW_ERRORS=1

# az on Windows prints CRLF; strip the CR.
azq() { az "$@" | tr -d '\r'; }

if ! command -v az >/dev/null 2>&1; then
  echo "ERROR: Azure CLI (az) is not installed. In the Codespace it is preinstalled." >&2
  exit 1
fi

echo "==> Checking your Azure sign-in"
if ! az account show >/dev/null 2>&1; then
  echo "    Not signed in. Sign in with your LAB user (one device code login)."
  az login --use-device-code --output none
fi
SUB_ID="$(azq account show --query id -o tsv)"
TENANT_ID="$(azq account show --query tenantId -o tsv)"
USER_NAME="$(azq account show --query user.name -o tsv)"
echo "    Signed in as $USER_NAME"

# Find the Foundry account of the lab: tagged microhack=15_Microsoft_IQ, with a project 'kolvo'.
find_account() {
  local query="[?tags.microhack=='$LAB_TAG'"
  if [ -n "$RG" ]; then query="$query && resourceGroup=='$RG'"; fi
  query="$query] | [0] | join(' ', [name, resourceGroup])"
  azq resource list --resource-type Microsoft.CognitiveServices/accounts --query "$query" -o tsv
}

echo "==> Looking for your lab"
FOUND="$(find_account || true)"
if [ -z "$FOUND" ]; then
  # Try the other subscriptions this user can see.
  for s in $(azq account list --query "[?state=='Enabled'].id" -o tsv); do
    [ "$s" = "$SUB_ID" ] && continue
    az account set --subscription "$s"
    FOUND="$(find_account || true)"
    if [ -n "$FOUND" ]; then SUB_ID="$s"; break; fi
  done
fi
if [ -z "$FOUND" ]; then
  # Fall back to the name pattern iq-<hash> (older labs without tags).
  query="[?starts_with(name, 'iq-')"
  if [ -n "$RG" ]; then query="$query && resourceGroup=='$RG'"; fi
  FOUND="$(azq resource list --resource-type Microsoft.CognitiveServices/accounts --query "$query] | [0] | join(' ', [name, resourceGroup])" -o tsv || true)"
fi
if [ -z "$FOUND" ]; then
  echo "ERROR: no Microsoft IQ lab found for $USER_NAME. Check that you signed in with your lab user," >&2
  echo "       or pass the resource group name: bash create-env.sh <resource-group>" >&2
  exit 1
fi
FOUNDRY_ACCOUNT="$(echo "$FOUND" | cut -d' ' -f1)"
RG="$(echo "$FOUND" | cut -d' ' -f2)"
echo "    Lab resource group: $RG (Foundry resource $FOUNDRY_ACCOUNT)"

first_of_type() {  # $1 = resource type, $2 = optional name prefix
  local q="[?resourceGroup=='$RG'"
  if [ -n "${2:-}" ]; then q="$q && starts_with(name, '$2')"; fi
  azq resource list -g "$RG" --resource-type "$1" --query "$q].name | [0]" -o tsv
}

FOUNDRY_HOST="https://$FOUNDRY_ACCOUNT.services.ai.azure.com"
PROJECT_ENDPOINT_STRANDVIK="$FOUNDRY_HOST/api/projects/strandvik"
PROJECT_ENDPOINT_KOLVO="$FOUNDRY_HOST/api/projects/kolvo"

SEARCH_NAME="$(first_of_type Microsoft.Search/searchServices)"
SEARCH_ENDPOINT="https://$SEARCH_NAME.search.windows.net"
STORAGE_ACCOUNT="$(first_of_type Microsoft.Storage/storageAccounts iqst)"
DOCUMENTS_CONTAINER="documents"
APPINSIGHTS_NAME="$(first_of_type Microsoft.Insights/components)"
FABRIC_CAPACITY="$(first_of_type Microsoft.Fabric/capacities || true)"

echo "==> Reading model deployments"
DEPLOYMENTS="$(azq cognitiveservices account deployment list -g "$RG" -n "$FOUNDRY_ACCOUNT" --query "[].name" -o tsv)"
pick_model() {
  if ! echo "$DEPLOYMENTS" | grep -qx "$1"; then echo "    WARN: model deployment '$1' not found in $FOUNDRY_ACCOUNT." >&2; fi
  echo "$1"
}
MODEL_DEPLOYMENT_NAME="$(pick_model gpt-5.4-mini)"
JUDGE_MODEL_DEPLOYMENT_NAME="$(pick_model gpt-5.6-luna)"
EMBEDDING_DEPLOYMENT_NAME="$(pick_model text-embedding-3-large)"

echo "==> Reading the Work IQ emulator"
FUNC_NAME="$(first_of_type Microsoft.Web/sites iq-wiq-)"
WORKIQ_MCP_URL=""; WORKIQ_VIEWER_URL=""; WORKIQ_BOARD_URL=""; WORKIQ_KEY=""; WORKIQ_KEY_SAM=""
if [ -n "$FUNC_NAME" ]; then
  FUNC_HOST="$(azq resource show -g "$RG" -n "$FUNC_NAME" --resource-type Microsoft.Web/sites --query properties.defaultHostName -o tsv)"
  WORKIQ_MCP_URL="https://$FUNC_HOST/mcp"
  WORKIQ_VIEWER_URL="https://$FUNC_HOST/viewer"
  WORKIQ_BOARD_URL="https://$FUNC_HOST/board"
  # The participant key is Alex's persona key. The admin key is never written to .env.
  WORKIQ_KEY="$(azq functionapp config appsettings list -g "$RG" -n "$FUNC_NAME" --query "[?name=='WORKIQ_KEY_ALEX'].value | [0]" -o tsv || true)"
  WORKIQ_KEY_SAM="$(azq functionapp config appsettings list -g "$RG" -n "$FUNC_NAME" --query "[?name=='WORKIQ_KEY_SAM'].value | [0]" -o tsv || true)"
else
  echo "    WARN: no Work IQ emulator found in $RG."
fi

echo "==> Looking for your Fabric workspace"
FABRIC_WORKSPACE_ID="$(azq rest --method get --url "https://api.fabric.microsoft.com/v1/workspaces" \
  --resource "https://api.fabric.microsoft.com" \
  --query "value[?starts_with(displayName, 'strandvik')].id | [0]" -o tsv 2>/dev/null || true)"
if [ -z "$FABRIC_WORKSPACE_ID" ]; then
  echo "    No 'strandvik-...' Fabric workspace yet. Create one in the Fabric portal on capacity '${FABRIC_CAPACITY:-<your capacity>}',"
  echo "    then run this script again (or paste its id into FABRIC_WORKSPACE_ID)."
fi

# Foundry portal deep links need the subscription id as base64url bytes.
sub_token() {
  local hex="${SUB_ID//-/}"
  if command -v python3 >/dev/null 2>&1 && python3 -c "" >/dev/null 2>&1; then
    python3 -c "import base64,sys;print(base64.urlsafe_b64encode(bytes.fromhex('$hex')).decode().rstrip('='))"
  elif command -v xxd >/dev/null 2>&1; then
    echo -n "$hex" | xxd -r -p | base64 | tr '+/' '-_' | tr -d '='
  fi
}
SUB_TOKEN="$(sub_token || true)"
project_url() {
  if [ -n "$SUB_TOKEN" ]; then
    echo "https://ai.azure.com/nextgen/r/$SUB_TOKEN,$RG,,$FOUNDRY_ACCOUNT,$1/home?tid=$TENANT_ID"
  else
    echo "https://ai.azure.com/?tid=$TENANT_ID (open project '$1' of $FOUNDRY_ACCOUNT)"
  fi
}

# ---------------------------------------------------------------------------
# Write .env: the keys below are managed by this script; any other lines you
# added yourself are kept.
# ---------------------------------------------------------------------------
MANAGED_KEYS="AZURE_SUBSCRIPTION_ID AZURE_TENANT_ID AZURE_RESOURCE_GROUP FOUNDRY_ACCOUNT PROJECT_ENDPOINT_STRANDVIK PROJECT_ENDPOINT_KOLVO MODEL_DEPLOYMENT_NAME JUDGE_MODEL_DEPLOYMENT_NAME EMBEDDING_DEPLOYMENT_NAME SEARCH_ENDPOINT STORAGE_ACCOUNT DOCUMENTS_CONTAINER APPINSIGHTS_NAME FABRIC_CAPACITY_NAME FABRIC_WORKSPACE_ID WORKIQ_MCP_URL WORKIQ_VIEWER_URL WORKIQ_BOARD_URL WORKIQ_KEY WORKIQ_KEY_SAM"
KEEP=""
if [ -f "$ENV_FILE" ]; then
  pattern="^($(echo "$MANAGED_KEYS" | tr ' ' '|'))="
  KEEP="$(grep -Ev "$pattern" "$ENV_FILE" | grep -Ev '^# (Written by create-env|Lab:)' || true)"
fi
{
  echo "# Written by create-env.sh on $(date -u +%Y-%m-%dT%H:%MZ). Do not commit: it holds your Work IQ keys."
  echo "# Lab: $RG"
  echo "AZURE_SUBSCRIPTION_ID=$SUB_ID"
  echo "AZURE_TENANT_ID=$TENANT_ID"
  echo "AZURE_RESOURCE_GROUP=$RG"
  echo "FOUNDRY_ACCOUNT=$FOUNDRY_ACCOUNT"
  echo "PROJECT_ENDPOINT_STRANDVIK=$PROJECT_ENDPOINT_STRANDVIK"
  echo "PROJECT_ENDPOINT_KOLVO=$PROJECT_ENDPOINT_KOLVO"
  echo "MODEL_DEPLOYMENT_NAME=$MODEL_DEPLOYMENT_NAME"
  echo "JUDGE_MODEL_DEPLOYMENT_NAME=$JUDGE_MODEL_DEPLOYMENT_NAME"
  echo "EMBEDDING_DEPLOYMENT_NAME=$EMBEDDING_DEPLOYMENT_NAME"
  echo "SEARCH_ENDPOINT=$SEARCH_ENDPOINT"
  echo "STORAGE_ACCOUNT=$STORAGE_ACCOUNT"
  echo "DOCUMENTS_CONTAINER=$DOCUMENTS_CONTAINER"
  echo "APPINSIGHTS_NAME=$APPINSIGHTS_NAME"
  echo "FABRIC_CAPACITY_NAME=$FABRIC_CAPACITY"
  echo "FABRIC_WORKSPACE_ID=$FABRIC_WORKSPACE_ID"
  echo "WORKIQ_MCP_URL=$WORKIQ_MCP_URL"
  echo "WORKIQ_VIEWER_URL=$WORKIQ_VIEWER_URL"
  echo "WORKIQ_BOARD_URL=$WORKIQ_BOARD_URL"
  echo "WORKIQ_KEY=$WORKIQ_KEY"
  echo "WORKIQ_KEY_SAM=$WORKIQ_KEY_SAM"
  if [ -n "$KEEP" ]; then echo "$KEEP"; fi
} > "$ENV_FILE.tmp"
mv "$ENV_FILE.tmp" "$ENV_FILE"
chmod 600 "$ENV_FILE" 2>/dev/null || true

MISSING=""
for k in $MANAGED_KEYS; do
  v="$(grep -E "^$k=" "$ENV_FILE" | head -n1 | cut -d= -f2-)"
  if [ -z "$v" ]; then MISSING="$MISSING $k"; fi
done

cat <<EOF

============================================================
 Your lab is ready. Wrote $ENV_FILE

 Foundry (ai.azure.com)
   Strandvik project (build here): $(project_url strandvik)
   Kolvo project (pre-built):       $(project_url kolvo)
 Azure portal, your resource group:
   https://portal.azure.com/#@$TENANT_ID/resource/subscriptions/$SUB_ID/resourceGroups/$RG/overview
 Fabric workspace:
   $( [ -n "$FABRIC_WORKSPACE_ID" ] && echo "https://app.fabric.microsoft.com/groups/$FABRIC_WORKSPACE_ID/list?tid=$TENANT_ID" || echo "https://app.fabric.microsoft.com/home?tid=$TENANT_ID (create your workspace)" )
 Work IQ viewer (play Sam here): ${WORKIQ_VIEWER_URL:-<not found>}
 Kolvo procurement board:        ${WORKIQ_BOARD_URL:-<not found>}
   Sign in to both with your WORKIQ_KEY (in .env).
============================================================
EOF
if [ -n "$MISSING" ]; then
  echo " Still empty:$MISSING"
  echo " (FABRIC_WORKSPACE_ID stays empty until you create your Fabric workspace.)"
fi
