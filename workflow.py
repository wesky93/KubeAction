import os
import tempfile
from urllib.parse import urlparse

import docker
import git
import yaml
from jinja2 import Template


def get_yaml_file(filename):
    with open(filename) as f:
        data = yaml.load(f, Loader=yaml.FullLoader)
    return data


def template_render(_template: str, context: dict):
    raw = _template.replace('${{', '{{')
    temp = Template(raw)
    return temp.render(**context)


def get_repo_name_version(p: str):
    raw = p.split('@')
    data = {
        'name': raw[0],
        'version': None
    }
    if len(raw) > 1:
        data['version'] = raw[1]
    return data


class BaseStep:
    def __init__(self, working_dir: str, data: dict):
        self._data = data
        self.working_dir = working_dir

    def id(self):
        return self._data.get('id')

    def exec(self):
        pass

    def load(self):
        pass


class RunStep(BaseStep):

    @property
    def run(self):
        return self._data.get('run', '')

    def exec(self):
        cmds = self.run.split('|')
        for cmd in cmds:
            cmd = cmd.replace('\n', '')
            os.system(cmd)

    def load(self):
        pass


def download_docker_image(img: str):
    tag = None
    client = docker.from_env()
    url = urlparse(img)
    info = url.path.split(":")
    img_name = url.netloc + info[0]
    if len(info) == 2:
        tag = info[1]

    print(f'start download {img_name} with tag {tag}')
    client.images.pull(img_name, tag=tag)
    print(f'finish download {img}')


class UsesStep(BaseStep):
    def __init__(self, working_dir: str, data: dict):
        super().__init__(working_dir, data)
        self.dir = None
        self.repo = None
        self.meta = None

    def id(self):
        return self._data.get('id')

    @property
    def uses(self):
        return self._data.get('uses')

    def exec(self):
        pass

    def load(self):
        self.dir = self.uses.split('/')[-1]
        prefix = self.uses.split('/')[:-1]
        meta = get_repo_name_version(self.dir)
        url = '/'.join(prefix + [meta['name']])
        url = f'https://github.com/{url}'
        branch = meta['version'] or 'master'
        print('start download git')
        self.path = os.path.join(self.working_dir, meta['name'])
        self.repo = git.Repo.clone_from(url, self.path, branch=branch)
        print(f'finish {meta["name"]} git download')
        self.meta = self.find_action_meta()
        print(f"{self.meta=}")

        self._ready()

    def _ready(self):
        runs = self.meta.get('runs')
        print(f"{runs=}")
        if runs.get('using') == 'docker':
            img = runs.get('image')
            if img:
                download_docker_image(img)

    def find_action_meta(self):
        tree = self.repo.tree()
        for blob in tree.blobs:
            if blob.name == 'action.yml':
                return get_yaml_file(blob.abspath)


def get_steps(wdr, job: dict):
    result = []
    for step in job.get('steps', {}):
        if step.get('uses'):
            result.append(UsesStep(wdr, step))
        else:
            result.append(RunStep(wdr, step))
    print(result)
    return result


class Job:
    def __init__(self, name: str, data: dict):
        self._data = data
        self.name = name
        self.workspace = tempfile.TemporaryDirectory()
        self.steps = get_steps(self.workspace.name, self._data)

    def load(self):
        for step in self.steps:
            step.load()

    def start(self):
        for step in self.steps:
            step.exec()
        self.workspace.cleanup()


def get_jobs(jobs: dict):
    return [Job(name=name, data=data) for name, data in jobs.get('jobs', {}).items()]


class BaseWorkFlow:
    def __init__(self, filename: str, context: dict = None):
        self.context = context or {}
        self._wf = get_yaml_file(filename)
        self.jobs = get_jobs(self._wf)

    def start(self):
        pass

    @property
    def name(self):
        return self._wf.get('name')


class LocalWorkFlow(BaseWorkFlow):

    def start(self):
        for job in self.jobs:
            job.load()
            job.start()
