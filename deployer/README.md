# Deploy workflow
When `cloudctl` being invoked with `deploy` command, we follow this workflow:
1) Fetch all files from config and code repos, get hashes of latest commits, create
test project with `project_id`, that contains these hashes.
2) Pull state of this test deployment.
3) Pull state of real deployment for specified `project_id`.
4) Compare states of test and real deployment. If they are not equal, which is expected
since we want to deploy some new changes, we continue. If they are equal, we throw an error.
5) Deploy changes for real project.
6) Pull new state of real deployment.
7) Compare states of test and real deployment. The should be equal, since we synchronized
test deployment and real deployment.
8) Delete test deployment.
9) Pull state of test deployment and make sure that it doesn't contain any resources.