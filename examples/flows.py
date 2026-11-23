from flai_sdk.api import flows

flaiFlowsApi = flows.FlaiFlows()

# flows come in pages of at most 50
page = 1
while True:
    result = flaiFlowsApi.get_flows(page=page)

    for flow in result['items']:
        print(flow['id'], flow['title'])

    if page >= result['pagination']['total_pages']:
        break
    page += 1
