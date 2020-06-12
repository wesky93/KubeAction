import os
import subprocess
from pathlib import Path
from pprint import pprint

import kopf
import kubernetes
from dotenv import load_dotenv

home = str(Path.home())
load_dotenv(verbose=True)


def get_token(cluster_name):
    args = (f"{home}/aws-iam-authenticator", "token", "-i", cluster_name, "--token-only")
    popen = subprocess.Popen(args, stdout=subprocess.PIPE)
    popen.wait()
    return popen.stdout.read().rstrip().decode('utf-8')


def config_client():
    cluster_name = os.environ.get('CLUSTER_NAME')
    api_endpoint = os.environ.get('API_ENDPOINT')
    api_token = get_token(cluster_name)
    configuration = kubernetes.client.Configuration()
    configuration.host = api_endpoint
    configuration.verify_ssl = False
    configuration.debug = True
    configuration.api_key['authorization'] = f"Bearer {api_token}"
    configuration.assert_hostname = True
    configuration.verify_ssl = False
    kubernetes.client.Configuration.set_default(configuration)


def make_workflow(name: str, namespace: str, jobs: list):
    resource = {
        "apiVersion": "argoproj.io/v1alpha1",
        "kind": "Workflow",
        "metadata": {"generateName": f"{name}-"},
        "spec": {
            "entrypoint": "whalesay",
            "arguments": {
                "parameters": [
                    {
                        "name": "message",
                        "value": "hello world"
                    }
                ]
            },
            "templates": [
                {
                    "name": "whalesay",
                    "inputs": {
                        "parameters": [{"name": "message", }]
                    },
                    "container": {
                        "image": "docker/whalesay",
                        "command": "[cowsay]",
                        "args": '["{{inputs.parameters.message}}"]'
                    }
                }
            ]
        }
    }
    print('origin')
    pprint(resource)
    kopf.adopt(resource)
    print('\n\nafter adopt')
    pprint(resource)

    data = {
        'group': "argoproj.io",
        'version': "v1",
        'namespace': namespace,
        'plural': "workflows",
        'body': resource,
    }

    return data


@kopf.on.create('kubeaction.spaceone.dev', 'v1', 'flows')
def create(body, spec, name, namespace, logger, **kwargs):
    print('body')
    print(body)
    print('spec')
    print(spec)
    print('name')
    print(name)
    print('namepace')
    print(namespace)

    event = spec.get('event')
    jobs = spec.get('jobs')
    meta = spec.get('meta', {})
    if meta:
        repo = meta.get('repo')
        spaceone_meta = meta.get('spaceone', {})
        domain_id = spaceone_meta.get('domain_id')

    if not event:
        raise kopf.PermanentError("event(on) must be set")
    if not jobs or len(jobs) < 1:
        raise kopf.PermanentError("must set more than one job")
    kubernetes.config.load_kube_config()
    configuration = kubernetes.client.Configuration()
    api_instance = kubernetes.client.ApiClient(configuration)

    vApi = kubernetes.client.VersionApi(api_instance)
    result = vApi.get_code()
    kopf.info(body, reason='log', message=f'version {result}')
    pprint(result)
    api = kubernetes.client.CustomObjectsApi(api_instance)
    obj = api.create_namespaced_custom_object(**make_workflow(name, namespace, jobs=jobs))

    kopf.info(body, reason='Create', message=f'Create Workflow {obj.metadata.name}')
