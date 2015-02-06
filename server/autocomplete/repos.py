def index(gh_repo_names, ghe_repo_names, force=False):
    repo_names = list(set(gh_repo_names).union(set(ghe_repo_names)))
    org_names = set()
    for repo_name in repo_names:
        org_name = repo_name.split('/')[0]
        org_names.add(org_name)

    paths = repo_names + list(org_names)
    bulk_data = []

    for path in paths:
        path_id = repo_name.replace('/', '%2F')
        bulk_data.append({
            "index": {
                "_index": "autocomplete", "_type": "path", "_id": path_id
        }})
        bulk_data.append({
            'path': path
        })
    return bulk_data
