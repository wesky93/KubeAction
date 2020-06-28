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

# check minikube is runnig
kubectl get po -A
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
kubectl apply -n kubeaction -f https://raw.githubusercontent.com/spaceone-dev/KubeAction/master/k8s/conroller.yaml
```