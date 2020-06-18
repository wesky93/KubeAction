import json
import os
from dataclasses import dataclass
from typing import List

import kopf
import shortuuid
from dotenv import load_dotenv
from kopf.engines import logging

load_dotenv(verbose=True)


def get_uuid():
    return shortuuid.uuid().lower()[:5]


class Resource:
    def to_dict(self):
        raise NotImplementedError('you must overwrite to_dict')


@dataclass
class FlowInfo:
    name: str
    repo: str
    github_token: dict
    secrets: dict


class CustomObject(Resource):
    apiVersion = ""
    kind = ""

    def __init__(self, namespace=None, name=''):
        self.namespace = namespace
        self.name = name

    def get_obj_name(self) -> str:
        return self.name

    def get_spec(self) -> str:
        raise NotImplementedError('you must overwrite get_obj_name')

    def get_metadata(self) -> dict:
        meta = {
            "name": self.get_obj_name(),
        }
        if self.namespace:
            meta['namespace'] = self.namespace
        return meta

    def to_dict(self, adopt=True):
        resource = {
            "apiVersion": self.apiVersion,
            "kind": self.kind,
            "metadata": self.get_metadata(),
            "spec": self.get_spec()
        }
        if adopt:
            kopf.adopt(resource)
        return resource


class ArgoObject(CustomObject):
    apiVersion = "argoproj.io/v1alpha1"


class ArgoEventSource(ArgoObject):
    kind = 'EventSource'

    def __init__(self, namespace: str, name: str, _type: str, spec: dict = None):
        super(ArgoEventSource, self).__init__(namespace, name)
        self.type = _type
        self.spec = spec or {}

    def get_spec(self):
        return {
            "type": self.type,
            **self.spec,
        }


class ArgoWebHookEventSource(ArgoEventSource):
    def __init__(self, namespace: str, name: str, webhook: dict):
        super(ArgoWebHookEventSource, self).__init__(namespace, name, _type="webhook")
        self.spec = {
            "webhook": webhook
        }


class ArgoGateway(ArgoObject):
    kind = 'Gateway'

    def __init__(self,
                 namespace: str,
                 name: str,
                 _type: str,
                 event_source_name: str,
                 service: dict,
                 subscribers: dict,
                 replica: int = 1,
                 service_account: str = "argo-events-sa",
                 spec: dict = None):
        super(ArgoGateway, self).__init__(namespace, name)
        self.type = _type
        self.replica = replica
        self.event_source = {
            "name": event_source_name
        }
        self.template = {
            "serviceAccountName": service_account
        }
        self.service = service
        self.subscribers = subscribers
        self.spec = spec or {}

    def get_spec(self):
        return {
            "type": self.type,
            "replica": self.replica,
            "template": self.template,
            "eventSourceRef": self.event_source,
            "service": self.service,
            "subscribers": self.subscribers,
            **self.spec,
        }


class ArgoWebHookGateway(ArgoGateway):
    def __init__(self, namespace: str, name: str,
                 service_ports: List[str],
                 sensor_port: int,
                 replica: int = 1,
                 service_account: str = "argo-events-sa",
                 spec: dict = None):
        subscribers = {
            "http": [f"http://{name}-sensor.{namespace}.svc:{sensor_port}/"]
        }
        service = {
            "ports": [{"port": p, "targetPort": p} for p in service_ports]
        }
        super(ArgoWebHookGateway, self).__init__(
            namespace, name, "webhook", event_source_name=name, replica=replica,
            service=service, service_account=service_account, spec=spec, subscribers=subscribers
        )


class ArgoSensor(ArgoObject):
    kind = 'Sensor'

    def __init__(self,
                 namespace: str,
                 name: str,
                 triggers: list,
                 dependencies: List[dict],
                 subscription: dict,
                 service_account: str = "argo-events-sa",
                 spec: dict = None):
        super(ArgoSensor, self).__init__(namespace=namespace, name=name)
        self.triggers = triggers
        self.dependencies = dependencies
        self.subscription = subscription
        self.template = {
            "serviceAccountName": service_account
        }
        self.spec = spec or {}

    def get_spec(self):
        return {
            "subscription": self.subscription,
            "dependencies": self.dependencies,
            "triggers": self.triggers,
            "template": self.template,
            **self.spec,
        }


class ArgoWebHookSensor(ArgoSensor):
    def __init__(self, namespace: str, name: str,
                 event_names: List[str],
                 sensor_port: int,
                 triggers: list,
                 service_account: str = "argo-events-sa",
                 spec: dict = None):
        subscription = {
            "http": {"port": sensor_port}
        }
        dependencies = [{"name": name, "gatewayName": name, "eventName": n} for n in event_names]
        super(ArgoWebHookSensor, self).__init__(
            namespace=namespace, name=name, triggers=triggers, dependencies=dependencies, subscription=subscription,
            service_account=service_account, spec=spec
        )


class StepsWorkflowTemplates(Resource):
    def __init__(self, template_names: List[str], name="jobs"):
        self.name = name
        self.template_names = template_names

    def to_dict(self):
        steps = [[{"name": name, "template": name} for name in self.template_names]]
        return {
            "name": self.name,
            "steps": steps
        }


class JobWorkflowTemplate(Resource):
    def __init__(self, name: str, job: str, flow_info: FlowInfo, cmd: list = None,
                 image: str = None,
                 ):
        self.name = name
        self.job = job
        self.image = image or os.environ.get('KUBEACTION_JOB_IMAGE', "spaceone/kubeaction-job:latest")
        self.cmd = cmd or ["python3 /src/job.py"]
        self.flow_info = flow_info

    def get_github_token(self):
        if self.flow_info.github_token:
            if self.flow_info.github_token['secrets_provider'] == 'kubernetes':
                return {
                    "name": "KUBEACTION_GITHUB_TOKEN",
                    "valueFrom": {
                        "secretKeyRef": {
                            "name": self.flow_info.github_token.get('name'),
                            "key": self.flow_info.github_token.get('key'),
                        }
                    }
                }
        return None

    def to_dict(self):
        DIND_MODE = os.environ.get('DIND_MODE', 'false')
        env = [
            {"name": "KUBEACTION_NAME", "value": self.name},
            {"name": "KUBEACTION_JOB", "value": json.dumps(self.job)},
            {"name": "KUBEACTION_FLOW", "value": self.flow_info.name},
            {"name": "KUBEACTION_REPOSITORY", "value": self.flow_info.repo},
            {"name": "DOCKER_HOST", "value": "127.0.0.1:2375"},
            {"name": "DIND_MODE", "value": DIND_MODE}

        ]
        volume_mounts = []
        if self.flow_info.secrets:
            if self.flow_info.secrets.get('provider') == 'kubernetes':
                volume_mounts.append({
                    "name": "secrets",
                    "mountPath": "/secret/kubeaction",
                    "readOnly": True,
                })
        github_token = self.get_github_token()
        if github_token:
            env.append(github_token)
        data = {
            "name": self.name,
            "container": {
                "image": self.image,
                "imagePullPolicy": "Always",
                "volumeMounts": volume_mounts,
                # "command": self.cmd,
                "env": env
            },
        }
        if DIND_MODE == 'true':
            data['sidecars'] = [
                {
                    "name": "dind",
                    "image": "docker:17.10-dind",
                    "securityContext": {
                        "privileged": True,
                    },
                    "mirrorVolumeMounts": True
                }
            ]

        return data

    @classmethod
    def from_flow_jobs(cls, jobs: dict, flow_info: FlowInfo) -> dict:
        has_needs = any([j.get('needs') for j in jobs.values()])
        templates = []
        entrypoint: str = None
        if has_needs:
            # make DAG templates
            pass
        else:
            for name, job in jobs.items():
                templates.append(cls(name, job, flow_info=flow_info))
            templates.append(StepsWorkflowTemplates(jobs.keys()))
            entrypoint = "jobs"

        return {
            'entrypoint': entrypoint,
            "templates": templates
        }


class ArgoWorkflow(ArgoObject):
    kind = 'Workflow'

    def __init__(self, namespace: str, name: str, entrypoint: str, templates: List[Resource], spec: dict = None):
        super(ArgoWorkflow, self).__init__(namespace=namespace, name=name)
        self.entrypoint = entrypoint
        self.templates = templates
        self.spec = spec or {}

    def get_spec(self):
        return {
            "entrypoint": self.entrypoint,
            "templates": [t.to_dict() for t in self.templates],
            **self.spec,
        }

    @classmethod
    def from_flow(cls, namespace: str, name: str, jobs: dict, flow_info: FlowInfo, spec: dict = {}, **kwargs):
        logging.info(f"flow_info_secrets {flow_info.secrets}")
        if flow_info.secrets:
            if flow_info.secrets.get('provider') == 'kubernetes':
                spec['volumes'] = [
                    {"name": "secrets", "secret": {"secretName": flow_info.secrets.get('name')}}
                ]
        logging.info(f"{spec}")
        return cls(namespace, name, **JobWorkflowTemplate.from_flow_jobs(jobs=jobs, flow_info=flow_info), spec=spec,
                   **kwargs)


class ArgoCronWorkflow(ArgoObject):
    kind = 'CronWorkflow'

    def __init__(self, namespace: str, name, schedule: str, entrypoint: str, templates: List[Resource],
                 spec: dict = None, workflow_spec: dict = None):
        super(ArgoCronWorkflow, self).__init__(namespace=namespace, name=name)
        self.name = name
        self.schedule = schedule
        self.entrypoint = entrypoint
        self.templates = templates
        self.spec = spec or {}
        self.workflow_spec = workflow_spec or {}

    def get_obj_name(self):
        return f"{self.name}-cwf"

    def get_spec(self):
        return {
            "schedule": self.schedule,
            "workflowSpec": {
                "entrypoint": self.entrypoint,
                "templates": [t.to_dict() for t in self.templates],
                **self.workflow_spec
            },
            **self.spec
        }

    @classmethod
    def from_flow(cls, namespace: str, name: str, schedule: str, jobs: dict, flow_info: FlowInfo,
                  workflow_spec: dict = {},
                  **kwargs):
        print("flow_info_secrets", flow_info.secrets)
        if flow_info.secrets:
            if flow_info.secrets.get('provider') == 'kubernetes':
                workflow_spec['volumes'] = [
                    {"name": "secrets", "secret": {"secretName": flow_info.secrets.get('name')}}
                ]
        print(workflow_spec)
        return cls(namespace, name, schedule, **JobWorkflowTemplate.from_flow_jobs(jobs=jobs, flow_info=flow_info),
                   workflow_spec=workflow_spec,
                   **kwargs)


class KubeActionObject(CustomObject):
    apiVersion = "kubeaction.spaceone.dev/v1alpha1"


class KubeActionEvent(KubeActionObject):
    kind = 'Event'

    def __init__(self, namespace: str, name, event_type='', event_data=None, jobs: list = None, metadata: dict = {}):
        super(KubeActionEvent, self).__init__(namespace)
        self.name = name
        self.event_type = event_type
        self.event_data = event_data
        self.metadata = metadata
        self.jobs = jobs or []

    def get_obj_name(self):
        return f"{self.name}-{self.event_type}"

    def get_spec(self):
        return {
            "type": self.event_type,
            "data": self.event_data,
            "jobs": self.jobs,
            "metadata": self.metadata,
        }
