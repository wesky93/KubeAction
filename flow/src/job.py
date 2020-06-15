import json
import os
import subprocess
import tempfile
from typing import ItemsView
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
    def __init__(self, job, working_dir: str, data: dict, secrets):
        self._data = data
        self.job = job
        self.working_dir = working_dir
        self.secrets = secrets
        self._env = None

    def id(self):
        return self._data.get('id')

    def exec(self):
        pass

    def start(self):
        self.setup()
        self.exec()
        self.clean()

    def load(self):
        pass

    def setup(self):
        pass

    def clean(self):
        pass

    @property
    def env(self):
        if not self._env:
            self._env = {
                k: template_render(v, {"secrets": self.secrets})
                for k, v in self._data.get('env', {}).items()
            }
        return self._env


class RunStep(BaseStep):

    @property
    def run(self):
        return self._data.get('run', '')

    def exec(self):
        cmds = self.run.split('|')
        for cmd in cmds:
            cmd = cmd.replace('\n', '')
            os.system(cmd)

    def setup(self):
        pass

    def clean(self):
        pass

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
    img = client.images.pull(img_name, tag=tag)
    print(f'finish download {img}')
    return img


from os import walk


def show_files(p):
    f = []
    for (dirpath, dirnames, filenames) in walk(p):
        f.extend(filenames)
        f.extend(dirnames)
        break
    return f


class UsesStep(BaseStep):
    def __init__(self, job, working_dir: str, data: dict, secrets):
        super().__init__(job, working_dir, data, secrets)
        self.dir = None
        self.repo = None
        self.meta = None
        self.docker_img = None

    @property
    def id(self):
        return self._data.get('id')

    @property
    def uses(self):
        return self._data.get('uses')

    @property
    def with_by_items(self) -> ItemsView:
        return self._data.get('with', {}).items()

    @property
    def runs(self):
        return self.meta.get('runs', {})

    @property
    def runtime(self):
        return self.runs.get('using')

    @property
    def main(self):
        return self.runs.get('main')

    @property
    def pre(self):
        return self.runs.get('pre')

    @property
    def inputs_by_items(self) -> ItemsView:
        return self.meta.get('inputs', {}).items()

    def get_inputs_env(self) -> dict:
        env = {key: data['default'] for key, data in self.inputs_by_items if data.get('default')}
        for k, v in self.with_by_items:
            env[k] = v
        return {f"INPUT_{k.upper()}": v for k, v in env.items()}

    def exec(self):
        print(show_files(self.working_dir))

        if self.runtime == 'docker':
            print('run', f"{self.meta}")
            client = docker.from_env()
            result = client.containers.run(
                self.docker_img.id,
                ['./entrypoint.sh'],
                detach=True,
                auto_remove=True,
                working_dir='/github/workflow',
                environment=self.env,
                volumes={
                    "/var/run/docker.sock": {"bind": "/var/run/docker.sock", "mode": "rw"},
                    f"/{self.working_dir}": {"bind": "/github/workflow", "mode": "rw"}
                }
            )
            try:
                print(result.logs())
            except Exception as e:
                print(e)
            result.remove(force=True)
        elif self.runtime == 'node12':
            print(show_files(self.path))
            inputs = self.get_inputs_env().items()
            exports = "; ".join([f"export {k}={v}" for k, v in inputs]) + "; " if inputs else ""
            entrypoint = os.path.join(self.path, self.main)
            out = subprocess.check_output(f'{exports}node {entrypoint}', shell=True, encoding='utf-8', cwd=self.working_dir)
            print(out)
        else:
            print(f'dose not support {self.runtime}')

    def load(self):
        self.dir = self.uses.split('/')[-1]
        prefix = self.uses.split('/')[:-1]
        meta = get_repo_name_version(self.dir)
        url = '/'.join(prefix + [meta['name']])
        url = f'https://github.com/{url}'
        branch = meta['version'] or 'master'
        print('start download git')
        self.path = os.path.join(self.working_dir, meta['name'])
        print(self.path, 'git pull path')
        self.repo = git.Repo.clone_from(url, self.path, branch=branch)
        print(f'finish {meta["name"]} git download')
        self.meta = self.find_action_meta()
        print(f"{self.meta}")

        # download docker image
        self._ready()

    def _ready(self):
        runs = self.meta.get('runs')
        print(f"{runs}")
        if runs.get('using') == 'docker':
            img = runs.get('image')
            if img:
                self.docker_img = download_docker_image(img)

    def find_action_meta(self):
        tree = self.repo.tree()
        for blob in tree.blobs:
            if blob.name == 'action.yml':
                return get_yaml_file(blob.abspath)


def get_steps(job, wdr, steps: list, secrets={}):
    result = []
    for step in steps:
        klass = RunStep
        if step.get('uses'):
            klass = UsesStep
        result.append(klass(job, wdr, step, secrets))

    print(result)
    return result


class Job():
    def __init__(self, name: str, data: dict, ctx: dict = {}):
        self._data = data
        self.name = name
        self.workspace = tempfile.TemporaryDirectory()
        self.steps = get_steps(self, self.workspace.name, self._data.get('steps', []))

    def load(self):
        for step in self.steps:
            step.load()

    def start(self):
        for step in self.steps:
            step.start()
        self.workspace.cleanup()


if __name__ == '__main__':
    # get secrets

    # get job
    job_name = os.environ.get('KUBEACTION_NAME')
    raw = json.loads(os.environ.get('KUBEACTION_JOB', ''))
    job = Job(job_name, raw)
    job.load()
    job.start()

    # set job
    # load resource
    # run job
    # export output
