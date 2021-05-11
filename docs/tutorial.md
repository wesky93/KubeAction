# Tutorial


## Install Minikube
you must install minikube for using all feature.
because microk8s or Docker Descktop for mac doesn't support DinD.

### Install Minikube
[reference](https://minikube.sigs.k8s.io/docs/start/)

#### on mac
```bash
brew install hyperkit
brew install minikube
brew link minikube
minikube config set driver hyperkit
minikube start --driver=hyperkit
minikube start --kubernetes-version 1.14.9

# check minikube is runnig
kubectl get po -A
```

### set role
```bash
kubectl create clusterrolebinding cluster-system-anonymous --clusterrole=cluster-admin --user=system:anonymous
```

### install argo
```bash
kubectl create namespace argo
kubectl apply -n argo -f https://raw.githubusercontent.com/argoproj/argo/stable/manifests/install.yaml
kubectl create namespace argo-events
kubectl apply -f https://raw.githubusercontent.com/argoproj/argo-events/stable/manifests/install.yaml
```

### install kubeaction
```bash
kubectl create namespace kubeaction
kubectl apply -n kubeaction -f https://raw.githubusercontent.com/spaceone-dev/KubeAction/master/k8s/crd.yaml
kubectl apply -n kubeaction -f https://raw.githubusercontent.com/spaceone-dev/KubeAction/master/k8s/controller.yaml
```

### run sample flow!
kubectl apply -n kubeaction -f https://raw.githubusercontent.com/spaceone-dev/KubeAction/master/sample/simple-flow.yaml
kubectl apply -n kubeaction -f https://raw.githubusercontent.com/spaceone-dev/KubeAction/master/sample/simple-flow-2.yaml
kubectl apply -n kubeaction -f https://raw.githubusercontent.com/spaceone-dev/KubeAction/master/sample/simple-flow-3.yaml
kubectl apply -n kubeaction -f https://raw.githubusercontent.com/spaceone-dev/KubeAction/master/sample/simple-flow-not-valid.yaml
