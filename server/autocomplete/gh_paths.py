def get(gh_repo_names, ghe_repo_names):
    repo_names = set(gh_repo_names + ghe_repo_names)
    org_names = set()
    for repo_name in repo_names:
        org_name = repo_name.split('/')[0]
        org_names.add(org_name)

    paths = repo_names.union(org_names)
    return paths
