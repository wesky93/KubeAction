from pprint import pprint

import kopf
import kubernetes


def make_workflow(name: str, jobs: list):
    my_resource = {
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
    return my_resource


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

    wf = make_workflow(name, jobs=jobs)
    api = kubernetes.client.CoreV1Api()
    print('before')
    pprint(wf)

    kopf.adopt(wf)
    print('after')
    pprint(wf)

    obj = api.create_namespaced_custom_object(
        group="argoproj.io",
        version="v1",
        namespace=namespace,
        plural="workflows",
        body=wf,
    )
    logger.info(f"create workspace {obj.metadata.name}")
    kopf.info(body, reason='Start', message='Create Flow')
