from flai.api import projects

flaiProjectApi = projects.FlaiProject()

for project in flaiProjectApi.get_projects():

    print(project)