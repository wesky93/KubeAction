import os
import sys
from pathlib import Path
from pprint import pprint

import kopf
from dotenv import load_dotenv

sys.path.append(os.path.dirname(__file__))

from client_helper import ArgoCronWorkflowAPI, KubeActionEventAPI
from schema import KubeActionEvent, ArgoCronWorkflow, FlowInfo

home = str(Path.home())
load_dotenv(verbose=True)
BASE_DIR = os.path.dirname(__file__)


@kopf.on.create('kubeaction.spaceone.dev', 'v1alpha1', 'flows')
def create_flows(body, spec, name, namespace, logger, **kwargs):
    events = spec.get('events')
    jobs = spec.get('jobs')
    metadata = spec.get('metadata', {})

    if not events:
        raise kopf.PermanentError("event(on) must be set")
    if not jobs or len(jobs) < 1:
        raise kopf.PermanentError("must set more than one job")

    api = KubeActionEventAPI(namespace)
    for k, v in events.items():
        body = KubeActionEvent(namespace, name, event_type=k, event_data=v, jobs=jobs, metadata=metadata).to_dict()
        pprint(body)
        obj = api.create(body=body)
        pprint(obj)
        logger.info('create event', obj)


@kopf.on.create('kubeaction.spaceone.dev', 'v1alpha1', 'events')
def create_events(body, spec, name, namespace, logger, **kwargs):
    pprint(body)
    event_type = spec.get('type')
    jobs = spec.get('jobs')

    metadata = spec.get('metadata', {})
    print(f"{metadata=}")
    flow_info = FlowInfo(
        name=name,
        repo=metadata.get('repository', ''),
        github_token=metadata.get('github_token')
    )
    print(f"{flow_info.repo=}")
    if event_type == 'schedule':
        data = spec.get('data', [])
        for s in data:
            cron = s.get('cron')
            if cron:
                wf = ArgoCronWorkflow.from_flow(namespace, name, cron, jobs, flow_info=flow_info)
                ArgoCronWorkflowAPI(namespace).create(body=wf.to_dict())


@kopf.on.create('kubeaction.spaceone.dev', 'v1alpha1', 'tasks')
def create(body, spec, name, namespace, logger, **kwargs):
    pass
