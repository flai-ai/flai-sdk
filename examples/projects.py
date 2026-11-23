from flai_sdk.api import projects

flaiProjectApi = projects.FlaiProject()

for project in flaiProjectApi.get_projects()['items']:

    print(project)