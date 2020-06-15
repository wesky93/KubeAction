import json
from typing import List

import kopf
import shortuuid


def get_uuid():
    return shortuuid.uuid().lower()


class Resource:
    def to_dict(self):
        raise NotImplementedError('you must overwrite to_dict')


class CustomObject(Resource):
    apiVersion = ""
    kind = ""

    def __init__(self, namespace=None, name=''):
        self.namespace = namespace
        self.name = name

    def get_obj_name(self) -> str:
        raise self.name

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
    def __init__(self, name: str, job: str, cmd: list = None, image: str = 'spaceone/kubeaction-job:0.0.11'):
        self.name = name
        self.job = job
        self.image = image
        self.cmd = cmd or ["python3 /src/job.py"]

    def to_dict(self):
        return {
            "name": self.name,
            "container": {
                "image": self.image,
                # "command": self.cmd,
                "env": [
                    {"name": "KUBEACTION_NAME", "value": self.name},
                    {"name": "KUBEACTION_JOB", "value": json.dumps(self.job)},
                    {"name": "DOCKER_HOST", "value": "127.0.0.1"}
                ],
            },
            # "sidecars": [
            #     {
            #         "name": "dind",
            #         "image": "docker:17.10-dind",
            #         "securityContext": {
            #             "privileged": True,
            #         },
            #         "mirrorVolumeMounts": True
            #     }
            # ]
        }

    @classmethod
    def from_flow_jobs(cls, jobs: dict) -> dict:
        has_needs = any([j.get('needs') for j in jobs.values()])
        templates = []
        entrypoint: str = None
        if has_needs:
            # make DAG templates
            pass
        else:
            for name, job in jobs.items():
                templates.append(cls(name, job))
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
            "templates": [t.to_dict() for t in self.templates]
        }

    @classmethod
    def from_flow(cls, namespace: str, name: str, jobs: dict, **kwargs):
        return cls(namespace, name, **JobWorkflowTemplate.from_flow_jobs(jobs=jobs), **kwargs)


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
        return f"{self.name}-cwf-{get_uuid()}"

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
    def from_flow(cls, namespace: str, name: str, schedule: str, jobs: dict, **kwargs):
        return cls(namespace, name, schedule, **JobWorkflowTemplate.from_flow_jobs(jobs=jobs), **kwargs)


class KubeActionObject(CustomObject):
    apiVersion = "kubeaction.spaceone.dev/v1alpha1"


class KubeActionEvent(KubeActionObject):
    kind = 'Event'

    def __init__(self, namespace: str, name, event_type='', event_data=None, jobs: list = None):
        super(KubeActionEvent, self).__init__(namespace)
        self.name = name
        self.event_type = event_type
        self.event_data = event_data
        self.jobs = jobs or []

    def get_obj_name(self):
        return f"{self.name}-event-{self.event_type}"

    def get_spec(self):
        return {
            "type": self.event_type,
            "data": self.event_data,
            "jobs": self.jobs
        }
