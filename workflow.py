import os
import tempfile
from os import path

import git
import yaml
from jinja2 import Template

template = Template('Hello {{ name }}!')
template.render(name='John Doe')


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


class Step:
    def __init__(self, working_dir: str, data: dict):
        self._data = data
        self.working_dir = working_dir
        self.dir = None
        self.git_version = None
        self.git = None

    def id(self):
        return self._data.get('id')

    @property
    def uses(self):
        return self._data.get('uses')

    @property
    def run(self):
        return self._data.get('run')

    def exec(self):

        if self.run:
            cmds = self.run.split('|')
            for cmd in cmds:
                cmd = cmd.replace('\n', '')
                os.system(cmd)

    def load(self):
        if self.uses:
            self.dir = self.uses.split('/')[-1]
            prefix = self.uses.split('/')[:-1]
            meta = get_repo_name_version(self.dir)
            url = '/'.join(prefix + [meta['name']])

            self.git = git.Git(path.join(self.working_dir, self.dir))
            if 'git://' in url or 'http://' in url:
                self.git.clone(url)
            else:
                self.git.clone('git://github.com/' + url)


def get_steps(wdr, job: dict):
    return [Step(wdr, step) for step in job.get('steps', {})]


class Job:
    def __init__(self, name: str, data: dict):
        self._data = data
        self.name = name
        self.workspace = tempfile.TemporaryDirectory()
        self.steps = get_steps(self.workspace, self._data)

    def load(self):
        for step in self.steps:
            step.load()

    def start(self):
        for step in self.steps:
            step.exec()


def get_jobs(jobs: dict):
    return [Job(name=name, data=data) for name, data in jobs.get('jobs', {}).items()]


class WorkFlow:
    def __init__(self, filename: str, context: dict = None):
        self.context = context or {}
        with open(filename) as f:
            self._wf = yaml.load(f, Loader=yaml.FullLoader)
        print(f'{self._wf=}')
        self.jobs = get_jobs(self._wf)

    def start(self):
        for job in self.jobs:
            job.load()
            job.start()

    @property
    def name(self):
        return self._wf.get('name')
