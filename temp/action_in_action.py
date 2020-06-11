from os import path

try:
    from .workflow import LocalWorkFlow
except Exception:
    from workflow import LocalWorkFlow

if __name__ == '__main__':
    from dotenv import load_dotenv
    import os

    load_dotenv(verbose=True)
    BASE_DIR = path.dirname(path.abspath(__file__))
    file = path.join(BASE_DIR, 'simple.yaml')
    file = path.join(BASE_DIR, 'uses-action.yaml')
    context = {
        'github': {
            'author': 'wesky93@gamil.com'
        }
    }
    secrets = {
        "SLACK_WEBHOOK": os.environ.get('SLACK_WEBHOOK')
    }
    wf = LocalWorkFlow(file, context, secrets)
    wf.start()
