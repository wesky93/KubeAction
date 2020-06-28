import logging
import os
import sys
from pathlib import Path
from pprint import pprint
from typing import List

import kopf
from dotenv import load_dotenv

sys.path.append(os.path.dirname(__file__))

try:
    from client_helper import ArgoCronWorkflowAPI, KubeActionEventAPI, ArgoEventSourceAPI, ArgoSensorsAPI, \
        ArgoGatewayAPI
    from schema import KubeActionEvent, ArgoCronWorkflow, FlowInfo, ArgoWebHookEventSource, ArgoWebHookGateway, \
        ArgoWebHookSensor
except Exception as e:
    from .client_helper import ArgoCronWorkflowAPI, KubeActionEventAPI, ArgoEventSourceAPI, ArgoSensorsAPI, \
        ArgoGatewayAPI
    from .schema import KubeActionEvent, ArgoCronWorkflow, FlowInfo, ArgoWebHookEventSource, ArgoWebHookGateway, \
        ArgoWebHookSensor

home = str(Path.home())
load_dotenv(verbose=True)
BASE_DIR = os.path.dirname(__file__)
print(os.environ.get('API_SERVICE'), os.environ.get('API_NAMESPACE'))
KUBEACTION_API = os.environ.get('KUBEACTION_API') \
                 or f"http://{os.environ.get('API_SERVICE')}.{os.environ.get('API_NAMESPACE')}.svc.cluster.local:{os.environ.get('API_PORT')}/events"

# https://github.com/zalando-incubator/kopf/issues/292#issuecomment-600672405
@kopf.on.login()
def login_fn(**kwargs):
    return kopf.login_via_client(**kwargs)


@kopf.on.startup()
def configure(logger, settings: kopf.OperatorSettings, **_):
    logger.info(os.environ.get('API_SERVICE'))
    logger.info(os.environ.get('API_NAMESPACE'))
    settings.posting.level = logging.DEBUG


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
        github_token=metadata.get('github_token'),
        secrets=metadata.get('secrets'),
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


def make_trigger_template(url, event_type_name, dependency_names: List[str]):
    payload = []
    for event in dependency_names:
        payload.append({
            "src": {
                "dependencyName": event,
                "contextTemplate": "{{ .Input }}"
            },
            "dest": "context"
        })
        payload.append({
            "src": {
                "dependencyName": event,
                "dataTemplate": "{{ .Input }}"
            },
            "dest": "data"
        })
        payload.append({
            "src": {
                "dependencyName": event,
                "value": event_type_name
            },
            "dest": "event_type_name"
        })
    return {
        "template": {
            "name": "kubeaction_event",
            "http": {
                "url": url,
                "payload": payload
            }
        }
    }


@kopf.on.create('kubeaction.spaceone.dev', 'v1alpha1', 'eventtypes')
def create_event_types(body, spec, name, namespace, logger, **kwargs):
    logger.info(f"{body}")
    logger.info(f"{spec}")
    event_type = spec.get('type')
    event_type_name = spec.get('event_type_name')

    if event_type == 'webhook':
        # webhook example
        # apiVersion: kubeaction.spaceone.dev/v1alpha1
        # kind: EventType
        # metadata:
        #     name: webhook-event-sourc
        #     spec:
        #         type: webhook
        #         event_type_name: ci-webhook
        #         gateway_replica: 1
        #         sensor_port: 9300
        #         events:
        #             intergraion:
        #                 port: 12000
        #                 endpoint: /intergraion
        #                 method: POST
        #             etc:
        #                 port: 12001
        #                 endpoint: /etc
        #                 method: POST
        raw_events = spec.get('events', {})
        events = {}
        sensor_port = spec.get('sensor_port')

        service_ports = []
        event_names = []
        for k, v in raw_events.items():
            port = v.get('port')
            service_ports.append(port)
            event_names.append(k)
            events[k] = v
            # event source port must string type
            events[k]['port'] = f"{port}"

        evs = ArgoWebHookEventSource(namespace, name, events)
        evs_obj = evs.to_dict()
        ArgoEventSourceAPI(namespace).create(body=evs_obj)
        logger.info(evs_obj)
        kopf.info(evs_obj, reason='Created', message='Gateway created')

        ga = ArgoWebHookGateway(namespace, name, service_ports, sensor_port,
                                replica=spec.get('gateway_replica'))
        ga_obj = ga.to_dict()
        pprint(ga_obj)
        ArgoGatewayAPI(namespace).create(body=ga_obj)
        logger.info(ga_obj)
        kopf.info(ga_obj, reason='Created', message='Gateway created')

        sensor = ArgoWebHookSensor(
            namespace, name, event_names=event_names, sensor_port=sensor_port,
            triggers=[make_trigger_template(KUBEACTION_API, event_type_name, event_names)]
        )
        sensor_obj = sensor.to_dict()
        logger.info(sensor_obj)
        ArgoSensorsAPI(namespace).create(body=sensor_obj)
        kopf.info(sensor_obj, reason='Created', message='Sensor created')
