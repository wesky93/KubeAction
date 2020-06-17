import os
from functools import partial

import kubernetes


class CustomObjectApi:
    group = ""
    version = ""
    plural = ""

    def __init__(self, namespace=None):
        if not os.environ.get('KUBECTL_CONFIG_MODE', True) == 'false':
            kubernetes.config.load_kube_config()
        self.api = kubernetes.client.CustomObjectsApi()
        self.namespace = namespace

    def get_client(self, method, postfix=""):
        kwargs = {
            "group": self.group,
            "version": self.version,
            "plural": self.plural
        }
        if self.namespace:
            scope = 'namespaced'
            kwargs['namespace'] = self.namespace
        else:
            scope = 'cluster'
        return partial(getattr(self.api, f'{method}_{scope}_custom_object{postfix}'), **kwargs)

    def create(self, **kwargs):
        return self.get_client('create')(**kwargs)

    def get(self, **kwargs):
        return self.get_client('get')(**kwargs)

    def delete(self, **kwargs):
        return self.get_client('delete')(**kwargs)

    def list(self, **kwargs):
        return self.get_client('list')(**kwargs)


class ArgoAPI(CustomObjectApi):
    group = 'argoproj.io'
    version = 'v1alpha1'


class ArgoWorkflowAPI(ArgoAPI):
    plural = 'workflows'


class ArgoCronWorkflowAPI(ArgoAPI):
    plural = 'cronworkflows'


class ArgoEventSourceAPI(ArgoAPI):
    plural = 'eventsources'


class ArgoGatewayAPI(ArgoAPI):
    plural = 'gateways'


class ArgoSensorsAPI(ArgoAPI):
    plural = 'sensors'


class KubeActionAPI(CustomObjectApi):
    group = 'kubeaction.spaceone.dev'
    version = 'v1alpha1'


class KubeActionFlowAPI(KubeActionAPI):
    plural = 'flows'


class KubeActionEventAPI(KubeActionAPI):
    plural = 'events'


class KubeActionTaskAPI(KubeActionAPI):
    plural = 'tasks'


if __name__ == '__main__':
    api = ArgoWorkflowAPI('argo')
    print(api.list())
