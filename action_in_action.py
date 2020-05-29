from os import path

try:
    from .workflow import WorkFlow
except Exception:
    from workflow import WorkFlow

if __name__ == '__main__':
    BASE_DIR = path.dirname(path.abspath(__file__))
    file = path.join(BASE_DIR, 'simple.yaml')
    context = {
        'github': {
            'author': 'wesky93@gamil.com'
        }
    }
    wf = WorkFlow(file, context)
    wf.start()
