import json
import os
from pathlib import Path
from typing import Any, Dict

from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.resource.subscriptions import SubscriptionClient
from azure.mgmt.resource.resources.models import DeploymentMode
from dotenv import load_dotenv
from azure.mgmt.compute import ComputeManagementClient


def load_json(file_path: Path) -> Dict[str, Any]:
    with file_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_env(name: str, default: str | None = None, required: bool = False) -> str:
    value = os.getenv(name, default)
    if required and not value:
        raise ValueError(f"Environment variable {name} is required")
    return value or ""


def main() -> None:
    load_dotenv()

    subscription_id = get_env("AZURE_SUBSCRIPTION_ID", required=True)
    template_path = Path("infra/arm/subscription.json")
    parameters_path = Path("infra/parameters/dev.json")

    if not template_path.exists():
        raise FileNotFoundError(f"Template not found at {template_path}")
    if not parameters_path.exists():
        raise FileNotFoundError(f"Parameters not found at {parameters_path}")

    template = load_json(template_path)
    parameters_raw = load_json(parameters_path)

    # Convert parameters file into ARM expected shape { name: { value } }
    parameters = {
        k: ({"value": v["value"]} if isinstance(v, dict) and "value" in v else {"value": v})
        for k, v in parameters_raw.items()
    }

    credential = DefaultAzureCredential(exclude_interactive_browser_credential=False)
    client = ResourceManagementClient(credential, subscription_id)

    deployment_name = get_env("DEPLOYMENT_NAME")

    deployment_properties = {
        "location": parameters["rgLocation"]["value"],
        "properties": {
            "mode": DeploymentMode.incremental,
            "template": template,
            "parameters": parameters,
        },
    }

    deployment = client.deployments.begin_create_or_update_at_subscription_scope(
        deployment_name=deployment_name,
        parameters=deployment_properties,
    ).result()

    outputs = deployment.properties.outputs or {}
    print(json.dumps(outputs or {}, indent=2))

    # Stress test is now on-demand via Run Command; see README.


if __name__ == "__main__":
    main()


