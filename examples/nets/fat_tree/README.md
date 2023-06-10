A Fat tree topology setup with classical BGP routing, 8 Kubernetes workers and 1 control plane node.

Note that this setup requires quite a bit of computing resources and might fail, for example Kind may refuse to create the cluster with 9 nodes, you can try to 'cut' this topology leaving just 1 node connected to each leaf, another potential solution is tweaking docker daemon settings (TODO).

<img src='topology.png'>

Topology taken from [this repo](https://github.com/KatharaFramework/Kathara-Labs/tree/master/Data%20Center%20Routing/kathara-labs_data_center/kathara-data_center-fat_tree_base).


This doesn't fully work yet (DNS problems with Kubernteres services for some reason + Kind can't run 8 nodes) TODO
