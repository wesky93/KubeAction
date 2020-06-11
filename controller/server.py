import kopf


@kopf.on.create('kubeaction.sapceone.dev', 'v1', 'flow')
def create_fn(body, spec, name, namespace, logger, **kwargs):
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

    kopf.info(body, reason='Start', message='Create Flow')
