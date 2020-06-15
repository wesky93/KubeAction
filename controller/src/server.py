import os
import sys
from pathlib import Path
from pprint import pprint

import kopf
from dotenv import load_dotenv

sys.path.append(os.path.dirname(__file__))

from client_helper import ArgoCronWorkflowAPI, KubeActionEventAPI
from schema import KubeActionEvent, ArgoCronWorkflow

home = str(Path.home())
load_dotenv(verbose=True)
BASE_DIR = os.path.dirname(__file__)


# def get_crd_create_api(group, version, namespace, plural):
#     kubernetes.config.load_kube_config()
#     api = kubernetes.client.CustomObjectsApi()
#     return partial(api.create_namespaced_custom_object, **{
#         "group": group,
#         "version": version,
#         "namespace": namespace,
#         "plural": plural
#     })
#
#
# def get_argo_create_api(namespace, plural, version="v1alpha1"):
#     return partial(get_crd_create_api, **{
#         "group": "argoproj.io",
#         "version": version,
#         "namespace": namespace,
#         "plural": plural
#     })
#
#
# def get_kubeaction_create_api(namespace, plural, version="v1alpha1"):
#     return partial(get_crd_create_api, **{
#         "group": "kubeaction.spaceone.dev",
#         "version": version,
#         "namespace": namespace,
#         "plural": plural
#     })
#
#
# def get_event_create_api(namespace):
#     return get_kubeaction_create_api(namespace=namespace, plural='events')
#
#
# def get_task_create_api(namespace):
#     return get_kubeaction_create_api(namespace=namespace, plural='tasks')


# def make_workflow(name: str, namespace: str, jobs: list, adopt=True):
#     resource = {
#         "apiVersion": "argoproj.io/v1alpha1",
#         "kind": "Workflow",
#         "metadata": {
#             "name": name,
#             "namespace": namespace,
#         },
#         "spec": {
#             "entrypoint": "dind-sidecar-test",
#             "templates": [
#                 {
#                     "name": "dind-sidecar-test",
#                     "container": {
#                         "image": "docker:17.10",
#                         "command": ["sh", "-c"],
#                         "args": [
#                             "until docker ps; do sleep 3; done; docker run --rm debian:latest cat /etc/os-release"],
#                         "env": [{
#                             "name": "DOCKER_HOST",
#                             "value": "127.0.0.1"
#                         }],
#                     },
#                     "sidecars": [
#                         {
#                             "name": "dind",
#                             "image": "docker:17.10-dind",
#                             "securityContext": {
#                                 "privileged": True,
#                             },
#                             "mirrorVolumeMounts": True
#                         }
#                     ]
#                 }
#             ]
#         }
#     }
#     print('origin')
#     pprint(resource)
#
#     if adopt:
#         kopf.adopt(resource)
#     print('\n\nafter adopt')
#     pprint(resource)
#     return resource


@kopf.on.create('kubeaction.spaceone.dev', 'v1alpha1', 'flows')
def create_flows(body, spec, name, namespace, logger, **kwargs):
    events = spec.get('events')
    jobs = spec.get('jobs')

    if not events:
        raise kopf.PermanentError("event(on) must be set")
    if not jobs or len(jobs) < 1:
        raise kopf.PermanentError("must set more than one job")

    api = KubeActionEventAPI(namespace)
    for k, v in events.items():
        body = KubeActionEvent(namespace, name, event_type=k, event_data=v, jobs=jobs).to_dict()
        pprint(body)
        obj = api.create(body=body)
        pprint(obj)
        logger.info('create event', obj)


@kopf.on.create('kubeaction.spaceone.dev', 'v1alpha1', 'events')
def create_events(body, spec, name, namespace, logger, **kwargs):
    pprint(body)
    event_type = spec.get('type')
    jobs = spec.get('jobs')

    if event_type == 'schedule':
        data = spec.get('data', [])
        for s in data:
            cron = s.get('cron')
            if cron:
                wf = ArgoCronWorkflow.from_flow(namespace, name, cron, jobs)
                ArgoCronWorkflowAPI(namespace).create(body=wf.to_dict())


@kopf.on.create('kubeaction.spaceone.dev', 'v1alpha1', 'tasks')
def create(body, spec, name, namespace, logger, **kwargs):
    pass
