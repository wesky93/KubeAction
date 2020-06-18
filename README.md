# KubeAction

Github Action on K8S!!

this project is part of OpenAction Project.
we will support you can use this in local, all any system. 

## support workflow syntax

- [x] name -> metadata.name
- [x] on -> spec.events
    - [ ] on.<event_name>.types
    - [ ] on.<push|pull_request>.<branches|tags>
    - [ ] on.<push|pull_request>.paths
    - [x] on.schedule
        - [x] on.schedule.cron
- [ ] env
- [ ] defaults
- [ ] defaults.run
- [x] jobs
    - [x] <job_id>
        - [x] name
        - [ ] needs
        - [x] runs-on(only ubuntu)
        - [ ] outputs
        - [ ] env
        - [ ] defaults
            - [ ] run
        - [ ] if
        - [ ] timeout-minutes
        - [ ] strategy
            - [ ] fail-fast
            - [ ] matrix(with context matrix)
            - [ ] max-parallel
        - [ ] continue-on-error
        - [ ] container
        - [ ] services
        - [x] steps
            - [x] run
            - [ ] shell
                - [ ] (bash)
                - [ ] (pwsh)
                - [ ] (python)
                - [ ] (sh)
                - [ ] (cmd)
                - [ ] (powershell)
            - [ ] with
                - [ ] (inputs)
                - [ ] args
                - [ ] entrypoint
            - [ ] env
            - [ ] continue-on-error
            - [ ] timeout-minutes

## support context
- [ ] secrets
    - provider
        - [ ] spaceone secrets
        - [x] k8s
        - [ ] aws secretManager
        - [ ] vault
- [ ] matrix
- [ ] needs

## support action syntax

- [x] name
- [x] author
- [x] description
- [ ] inputs
    - [ ] input_id
    - [ ] description
    - [ ] required
    - [ ] default
- [ ] outputs
- [ ] runs for JavaScript actions
    - [x] using(node12)
    - [ ] pre
    - [ ] pre-if
    - [x] main
    - [ ] post
    - [ ] post-if
- [ ] runs for Docker actions
    - [x] using(docker)
    - [ ] image
        - [ ] Dockerfile
        - [x] DockerHub url
    - [ ] pre-entrypoint
    - [x] entrypoint 
    - [ ] env
    - [ ] args(only for Dockerfile)
- [ ] branding
    - [ ] color
    - [ ] icon
    
## Secrets
support kubernetes secrets for workflow secrets.

we will support other provider(aws secrets,vault) using [external-secrets](https://github.com/godaddy/kubernetes-external-secrets)
```yaml
apiVersion: kubeaction.spaceone.dev/v1alpha1
kind: Flow
metadata:
  name: test-secrets
  namespace: kubeaction
spec:
  metadata:
    repository: https://github.com/wesky93/test_action
    secrets:
      provider: kubernetes
      name: action-test-secrets
```