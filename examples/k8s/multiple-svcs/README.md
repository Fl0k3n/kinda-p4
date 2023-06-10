simple http node app which uses data from redis database in the cluster, http app pods can be replicated.

NodePort is exposed for access from the browser via <node_ip>:30007

run with:

`kubectl apply -f deploy.yaml`
