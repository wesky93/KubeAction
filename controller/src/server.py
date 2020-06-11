import os
import subprocess

import kopf
import kubernetes
from dotenv import load_dotenv
from pathlib import Path
home = str(Path.home())
load_dotenv(verbose=True)


def get_token(cluster_name):
    args = (f"{home}/aws-iam-authenticator", "token", "-i", cluster_name, "--token-only")
    popen = subprocess.Popen(args, stdout=subprocess.PIPE)
    popen.wait()
    return popen.stdout.read().rstrip()


def config():
    cluster_name = os.environ.get('CLUSTER_NAME')
    api_endpoint = os.environ.get('API_ENDPOINT')
    api_token = get_token(cluster_name)
    configuration = kubernetes.client.Configuration()
    configuration.host = api_endpoint
    configuration.verify_ssl = False
    configuration.debug = True
    configuration.api_key['authorization'] = "Bearer " + api_token
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
    kopf.adopt(resource)

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
    config()
    api = kubernetes.client.CustomObjectsApi()
    obj = api.create_namespaced_custom_object(make_workflow(name, namespace, jobs=jobs))
    logger.info(f"create workspace {obj.metadata.name}")
    kopf.info(body, reason='Start', message='Create Flow')
