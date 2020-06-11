import os

import kopf
import kubernetes
import yaml


@kopf.on.create('kubeaction.sapceone.dev', 'v1', 'flow')
def create_fn(spec, name, namespace, logger, **kwargs):
    event = spec.get('on')
    jobs = spec.get('jobs')
    meta = spec.get('meta', {})
    repo = meta.get('repo')
    spaceone_meta = meta.get('spaceone')
    domain_id = spaceone_meta.get('domain_id')

    if not event:
        raise kopf.PermanentError("event(on) must be set")
    if not jobs or len(jobs) < 1:
        raise kopf.PermanentError("must set more than one job")

    path = os.path.join(os.path.dirname(__file__), 'pvc.yaml')
    tmpl = open(path, 'rt').read()
    text = tmpl.format(name=name, size=size)
    data = yaml.safe_load(text)

    api = kubernetes.client.CoreV1Api()
    obj = api.create_namespaced_persistent_volume_claim(
        namespace=namespace,
        body=data,
    )

    logger.info(f"PVC child is created: %s", obj)
