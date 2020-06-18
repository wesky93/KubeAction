import json
import subprocess
import tempfile
from dataclasses import dataclass
from os import path, walk, environ
from time import sleep
from typing import ItemsView
from urllib.parse import urlparse

import docker
import git
import yaml
from jinja2 import Template

from utils import files_list


def get_yaml_file(filename):
    with open(filename) as f:
        data = yaml.load(f, Loader=yaml.FullLoader)
    return data


def template_render(_template: str, ctx: dict, secrets=None):
    raw = _template.replace('${{', '{{')
    temp = Template(raw)
    context = ctx
    if secrets:
        pass
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
    def __init__(self, job, working_dir: str, data: dict, secrets={}, ctx={}):
        self._data = data
        self.job = job
        self.working_dir = working_dir
        self.secrets = secrets
        self.ctx = ctx
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

    def render_value(self, value):
        if type(value) == str and "{{" in value:
            return template_render(value, ctx=self.ctx, secrets=self.secrets)
        elif type(value) == bool:
            return 'true' if value else 'false'
        else:
            return value

    @property
    def env(self):
        if not self._env:
            self._env = {
                k: self.render_value(v)
                for k, v in self._data.get('env', {}).items()
            }
        return self._env


class RunStep(BaseStep):

    @property
    def run(self):
        return self._data.get('run', '')

    def get_script(self):
        return template_render(self.run, self.ctx, secrets=self.secrets)

    def exec(self):
        print(self.run)
        sh = tempfile.NamedTemporaryFile()

        with open(sh.name, 'w') as f:
            f.write(self.get_script())

        try:
            out = subprocess.check_output(f'/bin/bash -e {sh.name}',
                                          shell=True,
                                          encoding='utf-8',
                                          stderr=subprocess.STDOUT,
                                          cwd=self.working_dir)
        except subprocess.CalledProcessError as exc:
            print(exc.output)
            raise exc
        print(out)
        sh.close()

    def setup(self):
        pass

    def clean(self):
        pass

    def load(self):
        pass


def download_docker_image(img: str):
    tag = None
    client = docker.from_env(version='auto')
    url = urlparse(img)
    info = url.path.split(":")
    img_name = url.netloc + info[0]
    if len(info) == 2:
        tag = info[1]

    print(f'start download {img_name} with tag {tag}')
    img = client.images.pull(img_name, tag=tag)
    print(f'finish download {img}')
    return img


def show_files(p):
    f = []
    for (dirpath, dirnames, filenames) in walk(p):
        f.extend(filenames)
        f.extend(dirnames)
        break
    return f


class UsesStep(BaseStep):
    def __init__(self, job, working_dir: str, data: dict, secrets={}, ctx={}):
        super().__init__(job, working_dir, data, secrets=secrets, ctx=ctx)
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
        return {f"INPUT_{k.upper().replace('-', '_')}": self.render_value(v) for k, v in env.items()}

    def exec(self):
        print(show_files(self.working_dir))

        if self.runtime == 'docker':
            print('run', f"{self.meta}")
            client = docker.from_env(version='auto')
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
            entrypoint = path.join(self.path, self.main)
            try:
                out = subprocess.check_output(f'{exports}node {entrypoint}',
                                              shell=True,
                                              encoding='utf-8',
                                              stderr=subprocess.STDOUT,
                                              cwd=self.working_dir)
            except subprocess.CalledProcessError as exc:
                print(exc.output)
                raise exc
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
        self.path = path.join(self.working_dir, meta['name'])
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


def get_steps(job, wdr, steps: list, secrets={}, ctx={}):
    result = []
    for step in steps:
        klass = RunStep
        if step.get('uses'):
            klass = UsesStep
        result.append(klass(job, wdr, step, secrets, ctx))

    print(result)
    return result


class Job():
    def __init__(self,
                 name: str,
                 data: dict,
                 workspace: tempfile.TemporaryDirectory = None,
                 secrets={},
                 ctx: dict = {}
                 ):
        self._data = data
        self.name = name
        self.workspace = workspace or tempfile.TemporaryDirectory()
        self.steps = get_steps(self, self.workspace.name, self._data.get('steps', []), secrets, ctx)

    def load(self):
        for step in self.steps:
            step.load()

    def start(self):
        for step in self.steps:
            step.start()
        self.workspace.cleanup()


@dataclass
class KubeActionENV:
    @property
    def flow_name(self):
        return environ.get('KUBEACTION_FLOW')

    @property
    def job_name(self):
        return environ.get('KUBEACTION_NAME')

    @property
    def job(self):
        return json.loads(environ.get('KUBEACTION_JOB', ''))

    @property
    def repository(self):
        return environ.get('KUBEACTION_REPOSITORY')

    @property
    def github_token(self):
        return environ.get('KUBEACTION_GITHUB_TOKEN', '')

    @property
    def dind_mode(self):
        return environ.get('DIND_MODE', 'false') == 'true'


def set_github_env(ctx: dict):
    data = {
        "GITHUB_REPOSITORY": ctx['repository'],
        "GITHUB_WORKSPACE": ctx['workspace'],
        "GITHUB_TOKEN": ctx['token']

    }
    for k, v in data.items():
        environ[k] = v


def get_github_context(env: KubeActionENV, workspace: str):
    ctx = {
        "workspace": workspace,
        "job": env.job_name,
        "repository": '',
        "repository_owner": '',
        "token": env.github_token,
    }
    if env.repository:
        repo = urlparse(env.repository).path
        if repo[0] == '/':
            repo = repo[1:]
        ctx['repository'] = repo
        ctx['repository_owner'] = repo.split('/')[0]
    set_github_env(ctx)
    return ctx


def load_secrets(mount_path='/secret/kubeaction'):
    _secrets = {}
    for f in files_list(mount_path):
        with open(path.join(mount_path, f), 'r') as raw:
            _secrets[f] = raw.read()

    print('secrets', _secrets)
    return _secrets


if __name__ == '__main__':
    # get secrets
    secrets = load_secrets()
    workspace = tempfile.TemporaryDirectory()
    kube_env = KubeActionENV()
    context = {
        "github": get_github_context(kube_env, workspace.name)
    }

    if kube_env.dind_mode:
        print('this is DinD Mode')
        load = False
        max_try = 10
        while not load:
            try:
                client = docker.from_env(version='auto')
                print('images', client.images.list())
                print('docker load success')
                load = True
            except Exception as e:
                max_try -= 1
                print(f'fail to run docker {max_try} retry left')
                if max_try == 0:
                    raise e
                sleep(2)

    job = Job(kube_env.job_name, kube_env.job, workspace, ctx=context, secrets=secrets)
    job.load()
    job.start()

    # run job
    # export output
