# KubeAction

Github Action on K*S!!


## support syntax

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
        - [ ] k8s
        - [ ] aws secretManager
        - [ ] vault
- [ ] matrix
- [ ] needs
