from os import path

try:
    from .workflow import LocalWorkFlow
except Exception:
    from workflow import LocalWorkFlow

if __name__ == '__main__':
    BASE_DIR = path.dirname(path.abspath(__file__))
    file = path.join(BASE_DIR, 'simple.yaml')
    file = path.join(BASE_DIR, 'uses-action.yaml')
    context = {
        'github': {
            'author': 'wesky93@gamil.com'
        }
    }
    wf = LocalWorkFlow(file, context)
    wf.start()
