from kubernetes import config, client


def run_list_resource():
    config.load_kube_config()
    api = client.CustomObjectsApi()
    return api.list_namespaced_custom_object()


if __name__ == '__main__':
    try:
        result = run_list_resource()
    except Exception as e:
        print(e)
