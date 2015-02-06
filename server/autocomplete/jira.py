def index(users, projs):
    bulk_data = []
    for user in users:
        bulk_data.append({
            "index": {
                "_index": "autocomplete", "_type": "user", "_id": user
        }})
        bulk_data.append({
            'user': user
        })

    for proj in projs:
        bulk_data.append({
            "index": {
                "_index": "autocomplete", "_type": "path", "_id": proj
        }})
        bulk_data.append({
            'path': proj
        })
    return bulk_data
