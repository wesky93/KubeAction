from marshmallow import Schema, fields


class StepContext(Schema):
    outputs = fields.Dict(keys=fields.Str(), values=fields.Str(), default={})
    outcome = fields.Str()
    conclusion = fields.Str()


class NeedContext(Schema):
    result = fields.Str()
    outputs = fields.Dict(keys=fields.Str(), values=fields.Str())


class RunnerContext(Schema):
    os = fields.Str()
    temp = fields.Str()
    tool_cache = fields.Str()


class GithubContext(Schema):
    event = fields.Dict()
    event_path = fields.Str()
    workflow = fields.Str()
    job = fields.Str()
    run_id = fields.Str()
    run_number = fields.Str()
    actor = fields.Str()
    repository = fields.Str()
    event_name = fields.Str()
    sha = fields.Str()
    ref = fields.Str()
    head_ref = fields.Str()
    base_ref = fields.Str()
    token = fields.Str()
    workspace = fields.Str()
    action = fields.Str()


class ContextSchema(Schema):
    github = fields.Nested(GithubContext)
    # job = {}
    # env = {}
    needs = fields.Dict(keys=fields.Str(), values=fields.Nested(NeedContext))
    steps = fields.Dict(keys=fields.Str(), values=fields.Nested(StepContext))
    runner = fields.Nested(RunnerContext)

    def get_context(self):
        return self.dump(self)
